# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/api/routes/remix.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
内容灵感分析 API - 基于 LangChain 1.0 Agent 的 SSE 流式响应

端点:
- POST /api/v1/remix/analyze - 发起内容分析 (Agent 驱动)
- POST /api/v1/remix/chat - 对话追问 (带会话记忆)
- GET /api/v1/remix/modes - 获取支持的学习模式

事件类型:
- thinking_start/chunk/end - LLM 思考过程
- content_chunk - LLM 最终回复（流式）
- tool_call_start/end - 工具调用
- tool_progress - 工具执行进度
- done - 完成（包含结构化数据）
- error - 错误
"""

import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent.intent_classifier import classify_intent
from agent.memory import get_session_manager, memory_manager
from agent.remix_agent import (
    create_remix_agent,
    get_agent_state,
    get_session_config,
)
from agent.state import RemixContext
from agent.stream import StreamEventProcessor
from api.dependencies import get_current_user, get_current_user_optional
from api.routes.sse_helpers import SegmentCollector, SSEEventBuilder
from config import settings
from i18n import t
from llm_provider import is_llm_configured
from services.auth_service import User
from services.title_generator import generate_title
from utils.error_handlers import (
    build_agent_error_context,
    log_agent_error,
    build_sse_error_data,
)
from services.media_ai_store import MediaAIStore
from services.usage_service import usage_service, LLMUsageEvent
from utils.logger import logger


router = APIRouter()


# ========== 标题生成 ==========

async def _update_session_title(session_id: str, user_message: str, content_info: dict, user_id: Optional[str] = None):
    """后台任务：生成并更新会话标题"""
    if not settings.ENABLE_TITLE_GENERATION:
        return
    try:
        result = await generate_title(user_message, content_info, settings.TITLE_MAX_LENGTH)
        await get_session_manager().aupdate_session(session_id, title=result.title, user_id=user_id)
        logger.info(f"Session {session_id} title: '{result.title}'")
    except Exception as e:
        logger.warning(f"Title generation failed for {session_id}: {e}")



# ========== 请求模型 ==========

class AnalyzeRequest(BaseModel):
    """分析请求"""
    url: str
    instruction: Optional[str] = None  # 自然语言指令，如 "只分析不生成灵感"
    mode: Optional[str] = None   # 学习模式（可选）
    session_id: Optional[str] = None   # 会话 ID（用于会话持久化）
    original_message: Optional[str] = None  # 用户原始输入（用于持久化展示）
    preferred_voice_id: Optional[str] = None
    preferred_voice_title: Optional[str] = None
    preferred_avatar_id: Optional[str] = None
    preferred_avatar_title: Optional[str] = None
    preferred_avatar_url: Optional[str] = None
    model_name: Optional[str] = None


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None  # 会话 ID（新对话可为空，会自动生成）
    preferred_voice_id: Optional[str] = None
    preferred_voice_title: Optional[str] = None
    preferred_avatar_id: Optional[str] = None
    preferred_avatar_title: Optional[str] = None
    preferred_avatar_url: Optional[str] = None
    model_name: Optional[str] = None


def resolve_model_name(model_name: Optional[str]) -> Optional[str]:
    """
    解析并校验用户选择的模型名称（仅允许配置白名单）
    """
    if not model_name:
        return None
    allowed = getattr(settings, "LLM_ALLOWED_MODELS", None) or []
    if not allowed:
        return model_name
    if model_name in allowed:
        return model_name
    logger.warning(f"Model '{model_name}' not in allowlist, ignoring")
    return None


# ========== 端点实现 ==========

@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    发起内容分析（SSE 流式响应）

    基于 LangChain 1.0 Agent 实现，支持:
    - 自然语言指令 (instruction)
    - 会话记忆 (session_id)
    - 多种学习模式 (mode)
    - 自动意图识别 (当 mode 未指定时)
    - 用户关联 (可选，登录用户自动关联)

    事件类型:
    - progress: 进度更新 (来自 runtime.stream_writer)
    - agent: Agent 响应消息
    - error: 错误信息
    - done: 完成
    """
    # 前置校验
    if not request.url:
        raise HTTPException(status_code=400, detail=t("errors.urlEmpty"))

    # 获取用户 ID（可选）
    user_id = current_user.user_id if current_user else None

    if not request.url.startswith(("http://", "https://")):
        request.url = "https://" + request.url

    # 生成或使用提供的 session_id
    session_id = request.session_id or str(uuid.uuid4())

    # 记录会话元数据
    session_mgr = get_session_manager()
    if request.original_message:
        first_message = request.original_message
    else:
        first_message = request.url
        if request.instruction:
            first_message = f"{request.url} - {request.instruction}"
    await session_mgr.acreate_session(session_id, first_message=first_message, user_id=user_id)

    if request.original_message:
        user_display_message = request.original_message
    else:
        user_display_message = request.url
        if request.instruction:
            user_display_message = f"{request.url}\n{request.instruction}"
    await session_mgr.aadd_message(session_id, "user", user_display_message)

    logger.info(f"Received analyze request: {request.url}, session_id={session_id}")

    # 模式名称映射 (优先数据库，其次 i18n)
    def normalize_mode_key(mode_key: str) -> str:
        mode_map = {
            "imitate": "template",
            "rewrite": "style_explore",
        }
        return mode_map.get(mode_key, mode_key)

    async def get_mode_name(mode_key: str) -> str:
        """获取模式的本地化名称"""
        actual_key = normalize_mode_key(mode_key)
        try:
            from services.insight_mode_service import insight_mode_service
            from i18n import get_language
            mode = await insight_mode_service.get_mode(actual_key)
            if mode:
                is_zh = get_language() == "zh"
                return mode.label_zh if is_zh else mode.label_en
        except Exception as e:
            logger.debug(f"Failed to resolve mode name from database: {e}")
        return t(f"modes.{actual_key}.label")

    async def get_active_mode(mode_key: str):
        """校验模式是否存在且启用"""
        from services.insight_mode_service import insight_mode_service
        mode = await insight_mode_service.get_mode(mode_key)
        if not mode or not mode.is_active:
            return None
        return mode

    requested_mode = None
    if request.mode:
        requested_mode = normalize_mode_key(request.mode.strip())
        if not requested_mode:
            raise HTTPException(status_code=400, detail="mode cannot be empty")
        if not await get_active_mode(requested_mode):
            raise HTTPException(status_code=400, detail=f"Mode '{requested_mode}' not found or disabled")

    async def event_generator():
        request_started = time.monotonic()
        builder = SSEEventBuilder(retry_ms=5000)

        # ========== LLM 配置检查 ==========
        if not is_llm_configured():
            yield builder.build_with_retry("error", {
                "code": "LLM_NOT_CONFIGURED",
                "message": "尚未配置大模型，请联系管理员配置内置 LLM。",
            })
            yield builder.build("done", {"session_id": session_id, "error": True})
            yield builder.build_done()
            return

        # 每次请求创建新的 Agent 实例 (线程安全)
        selected_model = resolve_model_name(request.model_name)
        agent = create_remix_agent(model_name=selected_model)
        # 记录本次请求开始时的累计 token（用于计算 delta）
        start_state = await get_agent_state(agent, session_id)
        start_in = int((start_state or {}).get("total_input_tokens") or 0)
        start_out = int((start_state or {}).get("total_output_tokens") or 0)
        processor = StreamEventProcessor()
        collector = SegmentCollector()
        first_event_sent = False
        background_tasks = []  # 追踪后台任务，用于清理

        # ========== 意图识别阶段 ==========
        # 1. 优先使用用户明确指定的 mode
        # 2. 否则使用 LLM 意图识别（作为 SSE 流的一部分）
        if requested_mode:
            mode = requested_mode
            logger.info(f"Using user-specified mode: {mode}")
        else:
            # 发送意图识别开始事件（首个事件，包含 retry）
            yield builder.build_with_retry("intent_start", {"message": t("intent.analyzing")})
            first_event_sent = True

            # 使用意图识别
            user_input = request.url
            if request.instruction:
                user_input = f"{request.url} {request.instruction}"
            intent_result = await classify_intent(user_input)
            mode = normalize_mode_key(intent_result.mode)
            if not await get_active_mode(mode):
                logger.warning(f"Intent mode '{mode}' not found or disabled, falling back to analyze")
                mode = "analyze"
            logger.info(
                f"Intent classified: mode={mode}, "
                f"confidence={intent_result.confidence:.2f}, "
                f"reasoning={intent_result.reasoning[:50]}..."
            )

            # 发送意图识别完成事件
            yield builder.build("intent_end", {
                "mode": mode,
                "mode_name": await get_mode_name(mode),
                "confidence": intent_result.confidence,
                "reasoning": intent_result.reasoning,
            })

        # ========== 读取用户默认语音/形象 ==========
        if user_id and not request.preferred_voice_id:
            store = MediaAIStore()
            latest_voice = await store.get_latest_voice(user_id)
            if latest_voice:
                request.preferred_voice_id = latest_voice.get("voiceId")
                request.preferred_voice_title = latest_voice.get("title")
        if user_id and not request.preferred_avatar_url:
            store = MediaAIStore()
            latest_avatar = await store.get_latest_avatar(user_id)
            if latest_avatar:
                request.preferred_avatar_id = latest_avatar.get("avatarId")
                request.preferred_avatar_title = latest_avatar.get("title")
                request.preferred_avatar_url = (
                    latest_avatar.get("clipVideoUrl")
                    or latest_avatar.get("fullVideoUrl")
                    or ""
                )

        # ========== 构建用户消息和上下文 ==========
        if request.instruction:
            user_message = f"请处理这个链接: {request.url}\n\n要求: {request.instruction}"
        else:
            mode_name = await get_mode_name(mode)
            user_message = f"请分析 {request.url} 并用【{mode_name}】模式生成创意灵感"

        # 创建上下文（使用识别后的 mode）
        context = RemixContext(
            session_id=session_id,
            mode=mode,
            instruction=request.instruction,
            use_mock=settings.USE_MOCK,
            user_id=user_id,
            preferred_voice_id=request.preferred_voice_id,
            preferred_voice_title=request.preferred_voice_title,
            preferred_avatar_id=request.preferred_avatar_id,
            preferred_avatar_title=request.preferred_avatar_title,
            preferred_avatar_url=request.preferred_avatar_url,
            model_name=selected_model,
        )

        # 构建消息和配置
        messages = [HumanMessage(content=user_message)]
        config = get_session_config(session_id)

        # 确保 callbacks 在 config 中（错误时会输出详细日志）
        from utils.llm_callbacks import get_debug_callback_handler
        if "callbacks" not in config:
            config["callbacks"] = []
        config["callbacks"].append(get_debug_callback_handler())

        try:
            # 使用 astream_events 获取流式事件
            async for event in agent.astream_events(
                {"messages": messages},
                config=config,
                context=context,
                version="v2",
            ):
                # 使用 StreamEventProcessor 处理事件并转换为统一格式
                for output in processor.process_event(event):
                    event_type = output["type"]
                    event_data = output["data"]
                    timestamp = output.get("timestamp", 0)

                    # 收集 segments
                    collector.process_event(event_type, event_data, timestamp)

                    # 当收到 content_info 事件时，启动标题生成任务
                    if event_type == "content_info":
                        content_info = event_data.get("content_info")
                        if content_info:
                            task = asyncio.create_task(_update_session_title(session_id, first_message, content_info, user_id=user_id))
                            background_tasks.append(task)

                    # 首个事件包含 retry 字段
                    if not first_event_sent:
                        yield builder.build_with_retry(event_type, event_data)
                        first_event_sent = True
                    else:
                        yield builder.build(event_type, event_data)

            # 刷新缓冲区
            for output in processor.flush():
                event_type = output["type"]
                event_data = output["data"]
                collector.process_event(event_type, event_data)
                yield builder.build(event_type, event_data)

            # 完成收集
            segments = collector.finalize_segments()
            assistant_message = collector.get_assistant_message()

            # 获取最终状态（在保存消息前，用于添加 content_info 和 transcript 到 segments）
            final_state = await get_agent_state(agent, session_id)
            end_in = int((final_state or {}).get("total_input_tokens") or 0)
            end_out = int((final_state or {}).get("total_output_tokens") or 0)
            delta_in = max(0, end_in - start_in)
            delta_out = max(0, end_out - start_out)
            model_for_usage = (
                selected_model
                or getattr(settings, "OPENAI_MODEL_NAME", None)
                or getattr(settings, "OLLAMA_MODEL_NAME", None)
                or getattr(settings, "DEEPSEEK_MODEL_NAME", None)
                or "unknown"
            )
            await usage_service.record_llm_usage(
                LLMUsageEvent(
                    user_id=user_id,
                    session_id=session_id,
                    endpoint="/api/v1/remix/analyze",
                    model=model_for_usage,
                    input_tokens=delta_in,
                    output_tokens=delta_out,
                    latency_ms=int((time.monotonic() - request_started) * 1000),
                    success=True,
                )
            )

            # 诊断日志：检查 transcript 是否在 final_state 中
            logger.info(f"Final state transcript: {bool(final_state.get('transcript') if final_state else None)}")
            if final_state and final_state.get('transcript'):
                t = final_state['transcript']
                logger.info(f"Transcript: text={len(t.get('text', ''))} chars, segments={len(t.get('segments', []))} items")

            # 将 content_info 和 transcript 添加到 segments，以便刷新页面后能恢复
            done_cloned_voice = None
            done_tts_result = None
            done_lipsync_result = None
            if final_state:
                if final_state.get("content_info"):
                    segments.append({
                        "type": "content_info",
                        "data": final_state["content_info"],
                    })
                if final_state.get("transcript"):
                    segments.append({
                        "type": "transcript",
                        "data": final_state["transcript"],
                    })
                tool_names = {
                    seg.get("tool")
                    for seg in segments
                    if isinstance(seg, dict) and seg.get("type") == "tool_call"
                }
                has_cloned_voice = any(
                    isinstance(seg, dict) and seg.get("type") == "cloned_voice"
                    for seg in segments
                )
                has_tts_result = any(
                    isinstance(seg, dict) and seg.get("type") == "tts_result"
                    for seg in segments
                )
                has_lipsync_result = any(
                    isinstance(seg, dict) and seg.get("type") == "lipsync_result"
                    for seg in segments
                )
                if final_state.get("cloned_voice"):
                    done_cloned_voice = final_state["cloned_voice"]
                    if not has_cloned_voice:
                        segments.append({
                            "type": "cloned_voice",
                            "data": done_cloned_voice,
                        })
                if final_state.get("tts_result"):
                    done_tts_result = final_state["tts_result"]
                    if not has_tts_result:
                        segments.append({
                            "type": "tts_result",
                            "data": done_tts_result,
                        })
                if final_state.get("lipsync_result"):
                    done_lipsync_result = final_state["lipsync_result"]
                    if not has_lipsync_result:
                        segments.append({
                            "type": "lipsync_result",
                            "data": done_lipsync_result,
                        })

            # 持久化消息（包含完整的 segments）
            if assistant_message:
                await session_mgr.aadd_message(session_id, "assistant", assistant_message, segments=segments)

            # 发送 done 事件
            yield builder.build("done", {
                "session_id": session_id,
                "content_info": final_state.get("content_info") if final_state else None,
                "transcript": final_state.get("transcript") if final_state else None,
                "cloned_voice": done_cloned_voice,
                "tts_result": done_tts_result,
                "lipsync_result": done_lipsync_result,
            })

            # 发送 SSE 标准终止信号
            yield builder.build_done()

        except asyncio.CancelledError:
            # 客户端断开连接 - 记录日志并清理
            logger.info(f"Client disconnected for session {session_id}, cleaning up...")
            raise  # 重新抛出以确保生成器正确退出

        except Exception as e:
            # 失败也记录一条 usage（用于定位异常消耗/失败率）
            model_for_usage = (
                selected_model
                or getattr(settings, "OPENAI_MODEL_NAME", None)
                or getattr(settings, "OLLAMA_MODEL_NAME", None)
                or getattr(settings, "DEEPSEEK_MODEL_NAME", None)
                or "unknown"
            )
            await usage_service.record_llm_usage(
                LLMUsageEvent(
                    user_id=user_id,
                    session_id=session_id,
                    endpoint="/api/v1/remix/analyze",
                    model=model_for_usage,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=int((time.monotonic() - request_started) * 1000),
                    success=False,
                    error=str(e),
                )
            )
            # 使用统一错误处理
            error_context = build_agent_error_context(
                error=e,
                session_id=session_id,
                url=request.url,
                mode=mode if 'mode' in locals() else None,
                has_instruction=bool(request.instruction),
            )
            log_agent_error(e, error_context, "analyze")

            # 构建 SSE 错误事件
            error_data = build_sse_error_data(e, error_context, "AGENT_ERROR")
            yield builder.build("error", error_data)

            # 发送 done 事件确保前端能正确清理 loading 状态
            yield builder.build("done", {
                "session_id": session_id,
                "error": True,
            })
            # 发送 SSE 标准终止信号
            yield builder.build_done()

        finally:
            # 确保清理工作被执行
            # 1. 取消所有后台任务
            for task in background_tasks:
                if not task.done():
                    task.cancel()
            # 2. 重置处理器状态
            processor.reset()
            logger.debug(f"Event generator cleanup completed for session {session_id}")

    return EventSourceResponse(event_generator())


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    对话追问（SSE 流式响应）

    继续使用相同的 session_id 进行对话，Agent 会记住之前的分析结果。
    可以用于:
    - 调整标题、钩子、灵感内容
    - 切换学习模式重新生成
    - 询问创作技巧相关问题
    - 用户关联 (可选，登录用户自动关联)
    """
    if not request.message:
        raise HTTPException(status_code=400, detail=t("errors.messageEmpty"))

    # 获取用户 ID（可选）
    user_id = current_user.user_id if current_user else None

    # 如果没有提供 session_id，生成一个新的
    session_id = request.session_id or str(uuid.uuid4())

    # 记录会话元数据
    session_mgr = get_session_manager()
    await session_mgr.acreate_session(session_id, first_message=request.message, user_id=user_id)
    await session_mgr.aadd_message(session_id, "user", request.message)

    logger.info(f"Received chat request: {request.message[:50]}..., session_id={session_id}")

    if user_id and not request.preferred_voice_id:
        store = MediaAIStore()
        latest_voice = await store.get_latest_voice(user_id)
        if latest_voice:
            request.preferred_voice_id = latest_voice.get("voiceId")
            request.preferred_voice_title = latest_voice.get("title")
    if user_id and not request.preferred_avatar_url:
        store = MediaAIStore()
        latest_avatar = await store.get_latest_avatar(user_id)
        if latest_avatar:
            request.preferred_avatar_id = latest_avatar.get("avatarId")
            request.preferred_avatar_title = latest_avatar.get("title")
            request.preferred_avatar_url = (
                latest_avatar.get("clipVideoUrl")
                or latest_avatar.get("fullVideoUrl")
                or ""
            )

    selected_model = resolve_model_name(request.model_name)

    # 创建上下文
    context = RemixContext(
        session_id=session_id,
        use_mock=settings.USE_MOCK,
        user_id=user_id,
        preferred_voice_id=request.preferred_voice_id,
        preferred_voice_title=request.preferred_voice_title,
        preferred_avatar_id=request.preferred_avatar_id,
        preferred_avatar_title=request.preferred_avatar_title,
        preferred_avatar_url=request.preferred_avatar_url,
        model_name=selected_model,
    )

    async def event_generator():
        request_started = time.monotonic()
        builder = SSEEventBuilder(retry_ms=5000)

        # ========== LLM 配置检查 ==========
        if not is_llm_configured():
            yield builder.build_with_retry("error", {
                "code": "LLM_NOT_CONFIGURED",
                "message": "尚未配置大模型，请联系管理员配置内置 LLM。",
            })
            yield builder.build("done", {"session_id": session_id, "error": True})
            yield builder.build_done()
            return

        # 每次请求创建新的 Agent 实例 (线程安全)
        agent = create_remix_agent(model_name=selected_model)
        start_state = await get_agent_state(agent, session_id)
        start_in = int((start_state or {}).get("total_input_tokens") or 0)
        start_out = int((start_state or {}).get("total_output_tokens") or 0)
        processor = StreamEventProcessor()
        collector = SegmentCollector()
        first_event_sent = False

        # 构建消息和配置
        messages = [HumanMessage(content=request.message)]
        config = get_session_config(session_id)

        # 确保 callbacks 在 config 中（错误时会输出详细日志）
        from utils.llm_callbacks import get_debug_callback_handler
        if "callbacks" not in config:
            config["callbacks"] = []
        config["callbacks"].append(get_debug_callback_handler())

        try:
            # 使用 astream_events 获取流式事件
            async for event in agent.astream_events(
                {"messages": messages},
                config=config,
                context=context,
                version="v2",
            ):
                # 使用 StreamEventProcessor 处理事件
                for output in processor.process_event(event):
                    event_type = output["type"]
                    event_data = output["data"]
                    timestamp = output.get("timestamp", 0)

                    # 收集 segments
                    collector.process_event(event_type, event_data, timestamp)

                    # 首个事件包含 retry 字段
                    if not first_event_sent:
                        yield builder.build_with_retry(event_type, event_data)
                        first_event_sent = True
                    else:
                        yield builder.build(event_type, event_data)

            # 刷新缓冲区
            for output in processor.flush():
                event_type = output["type"]
                event_data = output["data"]
                collector.process_event(event_type, event_data)
                yield builder.build(event_type, event_data)

            # 完成收集
            segments = collector.finalize_segments()
            assistant_message = collector.get_assistant_message()

            # 获取最终状态并追加本轮媒体结果，支持前端聊天侧直接播放
            final_state = await get_agent_state(agent, session_id)
            end_in = int((final_state or {}).get("total_input_tokens") or 0)
            end_out = int((final_state or {}).get("total_output_tokens") or 0)
            delta_in = max(0, end_in - start_in)
            delta_out = max(0, end_out - start_out)
            model_for_usage = (
                selected_model
                or getattr(settings, "OPENAI_MODEL_NAME", None)
                or getattr(settings, "OLLAMA_MODEL_NAME", None)
                or getattr(settings, "DEEPSEEK_MODEL_NAME", None)
                or "unknown"
            )
            await usage_service.record_llm_usage(
                LLMUsageEvent(
                    user_id=user_id,
                    session_id=session_id,
                    endpoint="/api/v1/remix/chat",
                    model=model_for_usage,
                    input_tokens=delta_in,
                    output_tokens=delta_out,
                    latency_ms=int((time.monotonic() - request_started) * 1000),
                    success=True,
                )
            )
            done_cloned_voice = None
            done_tts_result = None
            done_lipsync_result = None
            if final_state:
                tool_names = {
                    seg.get("tool")
                    for seg in segments
                    if isinstance(seg, dict) and seg.get("type") == "tool_call"
                }
                has_cloned_voice = any(
                    isinstance(seg, dict) and seg.get("type") == "cloned_voice"
                    for seg in segments
                )
                has_tts_result = any(
                    isinstance(seg, dict) and seg.get("type") == "tts_result"
                    for seg in segments
                )
                has_lipsync_result = any(
                    isinstance(seg, dict) and seg.get("type") == "lipsync_result"
                    for seg in segments
                )
                if final_state.get("cloned_voice"):
                    done_cloned_voice = final_state["cloned_voice"]
                    if not has_cloned_voice:
                        segments.append({
                            "type": "cloned_voice",
                            "data": done_cloned_voice,
                        })
                if final_state.get("tts_result"):
                    done_tts_result = final_state["tts_result"]
                    if not has_tts_result:
                        segments.append({
                            "type": "tts_result",
                            "data": done_tts_result,
                        })
                if final_state.get("lipsync_result"):
                    done_lipsync_result = final_state["lipsync_result"]
                    if not has_lipsync_result:
                        segments.append({
                            "type": "lipsync_result",
                            "data": done_lipsync_result,
                        })

            # 持久化消息
            # 注意：追问时不添加 content_info 和 transcript 到 segments
            # 因为这些数据来自首次分析，追问不会产生新的视频处理结果
            if assistant_message:
                await session_mgr.aadd_message(session_id, "assistant", assistant_message, segments=segments)

            # 发送 done 事件
            # 追问时不发送旧的 content_info 和 transcript，避免前端重复显示
            yield builder.build("done", {
                "session_id": session_id,
                "cloned_voice": done_cloned_voice,
                "tts_result": done_tts_result,
                "lipsync_result": done_lipsync_result,
            })

            # 发送 SSE 标准终止信号
            yield builder.build_done()

        except asyncio.CancelledError:
            # 客户端断开连接 - 记录日志并清理
            logger.info(f"Client disconnected for session {session_id}, cleaning up...")
            raise  # 重新抛出以确保生成器正确退出

        except Exception as e:
            model_for_usage = (
                selected_model
                or getattr(settings, "OPENAI_MODEL_NAME", None)
                or getattr(settings, "OLLAMA_MODEL_NAME", None)
                or getattr(settings, "DEEPSEEK_MODEL_NAME", None)
                or "unknown"
            )
            await usage_service.record_llm_usage(
                LLMUsageEvent(
                    user_id=user_id,
                    session_id=session_id,
                    endpoint="/api/v1/remix/chat",
                    model=model_for_usage,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=int((time.monotonic() - request_started) * 1000),
                    success=False,
                    error=str(e),
                )
            )
            # 使用统一错误处理
            error_context = build_agent_error_context(
                error=e,
                session_id=session_id,
                message_preview=request.message[:100] if len(request.message) > 100 else request.message,
            )
            log_agent_error(e, error_context, "chat")

            # 构建 SSE 错误事件
            error_data = build_sse_error_data(e, error_context, "CHAT_ERROR")
            yield builder.build("error", error_data)

            # 发送 done 事件确保前端能正确清理 loading 状态
            yield builder.build("done", {
                "session_id": session_id,
                "error": True,
            })
            # 发送 SSE 标准终止信号
            yield builder.build_done()

        finally:
            # 确保清理工作被执行
            processor.reset()
            logger.debug(f"Event generator cleanup completed for session {session_id}")

    return EventSourceResponse(event_generator())


@router.get("/modes")
async def get_modes():
    """
    获取支持的学习模式（从数据库动态读取）

    返回启用的模式列表，包含本地化的标签和描述。
    """
    from services.insight_mode_service import insight_mode_service
    from i18n import get_language

    try:
        modes = await insight_mode_service.list_all(active_only=True)
        lang = get_language()
        is_zh = lang == "zh"

        return {
            "modes": [
                {
                    "value": mode.mode_key,
                    "label": mode.label_zh if is_zh else mode.label_en,
                    "description": mode.description_zh if is_zh else mode.description_en,
                    "prefill": mode.prefill_zh if is_zh else mode.prefill_en,
                    "icon": mode.icon,
                    "color": mode.color,
                }
                for mode in modes
            ]
        }
    except Exception as e:
        # 回退到硬编码列表
        logger.warning(f"Failed to fetch modes from database: {e}, using fallback")
        mode_keys = ["summarize", "analyze", "template", "style_explore"]
        return {
            "modes": [
                {
                    "value": mode_key,
                    "label": t(f"modes.{mode_key}.label"),
                    "description": t(f"modes.{mode_key}.description"),
                }
                for mode_key in mode_keys
            ]
        }


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    获取会话状态

    返回指定会话的当前状态，包括已分析的内容和生成的文案。
    """
    agent = create_remix_agent()
    state = await get_agent_state(agent, session_id)

    if not state:
        raise HTTPException(status_code=404, detail=t("errors.sessionNotFound"))

    # 注：analysis 和 copywriting 现在由 Agent 直接输出，不再保存到状态
    return {
        "session_id": session_id,
        "content_info": state.get("content_info"),
        "transcript": state.get("transcript"),
    }


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """获取会话消息列表"""
    user_id = current_user.user_id if current_user else None
    session_mgr = get_session_manager()
    session = await session_mgr.aget_session(session_id, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail=t("errors.sessionNotFound"))

    messages = await session_mgr.alist_messages(session_id, limit=limit, offset=offset)
    total = await session_mgr.acount_messages(session_id)

    return {
        "session_id": session_id,
        "messages": [m.to_dict() for m in messages],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ========== 会话管理端点 ==========

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    获取会话列表

    返回按更新时间倒序排列的会话列表，按用户隔离。
    """
    user_id = current_user.user_id if current_user else None
    session_mgr = get_session_manager()
    sessions = await session_mgr.alist_sessions(limit=limit, offset=offset, user_id=user_id)
    total = await session_mgr.acount_sessions(user_id=user_id)

    return {
        "sessions": [s.to_dict() for s in sessions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    删除会话（需要登录）

    删除指定会话的元数据和 checkpointer 中的数据。
    """
    user_id = current_user.user_id
    session_mgr = get_session_manager()

    # 删除会话元数据（带 user_id 校验）
    deleted = await session_mgr.adelete_session(session_id, user_id=user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=t("errors.sessionNotFound"))

    # 尝试从 checkpointer 删除（如果支持）
    try:
        checkpointer = memory_manager.checkpointer
        if hasattr(checkpointer, "adelete_thread"):
            await checkpointer.adelete_thread(session_id)
        elif hasattr(checkpointer, "delete_thread"):
            checkpointer.delete_thread(session_id)
    except Exception as e:
        logger.warning(f"Failed to delete checkpointer data: {e}")

    return {"success": True, "session_id": session_id}


class UpdateSessionRequest(BaseModel):
    """更新会话请求"""
    title: Optional[str] = None


@router.patch("/session/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    更新会话元数据（需要登录）

    目前支持更新会话标题。
    """
    user_id = current_user.user_id
    session_mgr = get_session_manager()
    session = await session_mgr.aupdate_session(session_id, title=request.title, user_id=user_id)

    if not session:
        raise HTTPException(status_code=404, detail=t("errors.sessionNotFound"))

    return session.to_dict()
