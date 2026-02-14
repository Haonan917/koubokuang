# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/llm_provider.py
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
LLM 提供商抽象层 - 统一的 LLM 接口。

支持:
- Anthropic Claude (Extended Thinking)
- OpenAI 兼容 API (GPT-5, MiniMax M2.x, Kimi K2, GLM-4.7)
- DeepSeek (原生 reasoning_content)
- Ollama (本地模型)

Thinking/Reasoning 支持:
- Claude: thinking={"type": "enabled", "budget_tokens": N}
- GPT-5: reasoning={"effort": "high", "summary": "auto"}
- DeepSeek: 使用 deepseek-reasoner 模型，自动处理 reasoning_content
- GLM-4.7: extra_body={"thinking": {"type": "enabled", "clear_thinking": False}}
- Kimi K2: extra_body={"reasoning": True}
- MiniMax: 默认输出 <think> 标签，由 ThinkTagFSM 解析

配置优先级:
1. 数据库激活配置 (用户通过 UI 选择的 is_active=1 配置)
2. .env 环境变量配置 (回退/默认)
"""
from typing import Optional, Dict, Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from config import settings
from langchain_openai import ChatOpenAI
from utils.chat_openai_with_reasoning import ChatOpenAIWithReasoning
from utils.logger import logger


# ============================================================================
# 数据库配置读取 (同步版本)
# ============================================================================

def _get_active_db_config() -> Optional[Dict[str, Any]]:
    """
    从数据库获取当前激活的 LLM 配置 (同步版本)

    Returns:
        激活的配置字典，如果没有则返回 None
    """
    try:
        import pymysql

        # 使用 Agent 数据库配置
        conn = pymysql.connect(
            host=settings.AGENT_DB_HOST or "localhost",
            port=settings.AGENT_DB_PORT or 3306,
            user=settings.AGENT_DB_USER or "root",
            password=settings.AGENT_DB_PASSWORD or "",
            database=settings.AGENT_DB_NAME,
            charset="utf8mb4",
            connect_timeout=5,
        )

        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("""
                    SELECT provider, api_key, base_url, model_name,
                           enable_thinking, thinking_budget_tokens, reasoning_effort,
                           support_multimodal
                    FROM llm_configs
                    WHERE is_active = 1
                    LIMIT 1
                """)
                result = cursor.fetchone()

                if result:
                    logger.info(f"[LLM Config] 使用数据库配置: {result['provider']} / {result['model_name']}")
                    return result
                else:
                    logger.debug("[LLM Config] 数据库无激活配置，回退到 .env")
                    return None
        finally:
            conn.close()

    except ImportError:
        logger.warning("[LLM Config] pymysql 未安装，无法读取数据库配置")
        return None
    except Exception as e:
        logger.debug(f"[LLM Config] 数据库配置读取失败: {e}，回退到 .env")
        return None


# ============================================================================
# DeepSeek Reasoner 兼容层
# ============================================================================

class ChatDeepSeekWithReasoning:
    """
    DeepSeek Chat 模型包装器，支持 reasoning_content 在 tool calling 中传递。

    修复：langchain_deepseek 库未将 reasoning_content 传回 API 的问题，
    导致 DeepSeek Reasoner 模型在 tool calling 时返回 400 错误。

    参考：https://api-docs.deepseek.com/zh-cn/guides/thinking_mode#工具调用
    """

    def __new__(cls, **kwargs):
        from langchain_deepseek import ChatDeepSeek
        from langchain_core.messages import AIMessage

        class _ChatDeepSeekWithReasoning(ChatDeepSeek):
            """内部实现类：重写 _get_request_payload 以传递 reasoning_content"""

            def _get_request_payload(self, input_, *, stop=None, **kwargs):
                payload = super()._get_request_payload(input_, stop=stop, **kwargs)

                # 从输入中提取原始消息
                if isinstance(input_, list):
                    messages = input_
                elif hasattr(input_, "messages"):
                    messages = input_.messages
                else:
                    messages = []

                # 为 assistant 消息添加 reasoning_content
                ai_msg_idx = 0
                ai_messages = [m for m in messages if isinstance(m, AIMessage)]

                for msg_dict in payload.get("messages", []):
                    if msg_dict.get("role") == "assistant" and ai_msg_idx < len(ai_messages):
                        reasoning = ai_messages[ai_msg_idx].additional_kwargs.get("reasoning_content")
                        if reasoning:
                            msg_dict["reasoning_content"] = reasoning
                        ai_msg_idx += 1

                return payload

        return _ChatDeepSeekWithReasoning(**kwargs)


def get_llm(
    temperature: float = 0.1,
    model_name: Optional[str] = None,
    enable_thinking: Optional[bool] = None,
    enable_debug: Optional[bool] = None,
) -> BaseChatModel:
    """
    根据配置返回对应的 LLM 实例

    配置优先级:
    1. 数据库激活配置 (用户通过 UI 选择的 is_active=1 配置)
    2. .env 环境变量配置 (回退/默认)

    Args:
        temperature: 采样温度
        model_name: 可选的模型名称覆盖 (会覆盖数据库配置)
        enable_thinking: 是否启用 thinking/reasoning 输出
        enable_debug: 是否启用调试日志（默认读取 LLM_DEBUG_LOGGING 配置）

    Returns:
        BaseChatModel: LangChain Chat 模型实例
    """
    # 尝试从数据库获取激活配置
    db_config = _get_active_db_config()

    if db_config:
        # 使用数据库配置
        provider = db_config['provider'].lower()
        _model_name = model_name or db_config['model_name']
        _api_key = db_config['api_key']
        _base_url = db_config['base_url']
        _enable_thinking = enable_thinking if enable_thinking is not None else bool(db_config['enable_thinking'])
        _thinking_budget = db_config['thinking_budget_tokens'] or 4096
        _reasoning_effort = db_config['reasoning_effort'] or 'high'

        logger.debug(f"[LLM] 使用数据库配置: provider={provider}, model={_model_name}, thinking={_enable_thinking}")
    else:
        # 回退到 .env 配置
        provider = settings.LLM_PROVIDER.lower()
        _model_name = model_name  # 后面会从 settings 获取
        _api_key = None  # 后面会从 settings 获取
        _base_url = None  # 后面会从 settings 获取
        _enable_thinking = enable_thinking if enable_thinking is not None else getattr(settings, 'ENABLE_THINKING', False)
        _thinking_budget = getattr(settings, 'THINKING_BUDGET_TOKENS', 4096)
        _reasoning_effort = getattr(settings, 'REASONING_EFFORT', 'high')

        logger.debug(f"[LLM] 使用 .env 配置: provider={provider}")

    # ========== 准备 Callbacks ==========
    callbacks = []

    # 注入调试 callback
    # 默认总是启用，因为 callback 内部会根据 log level 决定输出详细程度
    # 可以通过 enable_debug=False 明确禁用
    should_debug = enable_debug if enable_debug is not None else True

    if should_debug:
        from utils.llm_callbacks import get_debug_callback_handler
        callbacks.append(get_debug_callback_handler())
        # callback 已启用，正常请求不输出日志，只在错误时输出

    # ========== Anthropic Claude ==========
    if provider == "anthropic":
        model = _model_name or settings.ANTHROPIC_MODEL_NAME
        api_key = _api_key or settings.ANTHROPIC_API_KEY
        base_url = _base_url or settings.ANTHROPIC_BASE_URL

        logger.debug(f"Initializing Anthropic: {model}, thinking={_enable_thinking}")

        kwargs = {
            "api_key": api_key,
            # 开启 thinking 时: max_tokens = thinking_budget + 输出预算(16K)
            # 未开启时: 16K 足够覆盖长文创作场景
            "max_tokens": _thinking_budget + 16384 if _enable_thinking else 16384,
            "callbacks": callbacks,
        }
        if base_url:
            kwargs["base_url"] = base_url

        if _enable_thinking:
            kwargs["temperature"] = 1  # Extended Thinking 要求
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": _thinking_budget
            }
            # 使用 output_version="v1" 确保 content_blocks 使用 LangChain 标准格式
            # 这样 ReasoningExtractor 可以统一处理 type="thinking" 的 blocks
            kwargs["output_version"] = "v1"
        else:
            kwargs["temperature"] = temperature

        return init_chat_model(f"anthropic:{model}", **kwargs)

    # ========== DeepSeek (专用包，支持 reasoning_content) ==========
    elif provider == "deepseek":
        model = _model_name or settings.DEEPSEEK_MODEL_NAME or "deepseek-chat"
        api_key = _api_key or settings.DEEPSEEK_API_KEY
        base_url = _base_url or settings.DEEPSEEK_BASE_URL

        logger.debug(f"Initializing DeepSeek: {model}")

        return ChatDeepSeekWithReasoning(
            model=model,
            api_key=api_key,
            api_base=base_url,
            temperature=temperature if "reasoner" not in model else 0,
            callbacks=callbacks,
        )

    # ========== OpenAI 兼容 API (GPT-5, MiniMax, Kimi) ==========
    elif provider == "openai":
        model = _model_name or settings.OPENAI_MODEL_NAME
        api_key = _api_key or settings.OPENAI_API_KEY
        base_url = _base_url or settings.OPENAI_BASE_URL
        model_lower = model.lower() if model else ""

        logger.debug(f"Initializing OpenAI-compatible: {model}, thinking={_enable_thinking}")

        kwargs = {
            "api_key": api_key,
            "base_url": base_url,
            "temperature": temperature,
            "callbacks": callbacks,
        }

        # MiniMax 在长输出场景下建议显式设置 max_tokens，避免 completion 预算过小导致提前收束
        # 该参数仅对 MiniMax 生效，避免影响其他 OpenAI-compatible 提供商
        if "minimax" in model_lower or "m2" in model_lower:
            kwargs["max_tokens"] = getattr(settings, "MINIMAX_MAX_TOKENS", 8192)

        # 检查是否强制禁用 reasoning
        force_disable_reasoning = getattr(settings, 'LLM_FORCE_DISABLE_REASONING', False)

        if _enable_thinking and model and not force_disable_reasoning:
            # OpenAI GPT-5.x 系列
            # 修复：根据 LangChain 文档，reasoning 应作为直接参数而非 extra_body
            # 参考：https://python.langchain.com/docs/integrations/chat/openai/
            if "gpt-5" in model_lower or "gpt5" in model_lower:
                # 正确方式：直接传递 reasoning 参数
                kwargs["reasoning"] = {
                    "effort": _reasoning_effort,  # 'low', 'medium', 'high', 'xhigh'
                    "summary": "auto",            # 'detailed', 'auto', or None
                }
                # 使用 output_version="v1" 确保 content_blocks 使用 LangChain 标准格式
                # GPT-5 会输出 type="reasoning" 的 blocks
                kwargs["output_version"] = "v1"
                logger.debug(f"✓ GPT-5 reasoning enabled: effort={_reasoning_effort}")

            # MiniMax M2.x - 不使用 reasoning_split（LangChain 会丢失 reasoning_details）
            # MiniMax M2.1 默认会输出 <think> 标签，由 ThinkingParser 解析
            elif "minimax" in model_lower or "m2" in model_lower:
                # 使用稍高的 temperature 让模型更自然地输出思考
                kwargs["temperature"] = max(temperature, 0.5)
                logger.debug("MiniMax M2.x: using <think> tags (parsed by ThinkingParser)")

            # Kimi K2 - 使用 extra_body（Kimi API 的实现方式）
            # 注意：Kimi 返回 delta.reasoning_content，需要使用 ChatOpenAIWithReasoning
            elif "kimi" in model_lower:
                kwargs["extra_body"] = {"reasoning": True}
                kwargs["temperature"] = 1.0
                logger.debug("✓ Kimi reasoning enabled (using ChatOpenAIWithReasoning)")
                return ChatOpenAIWithReasoning(model=model, **kwargs)

            # GLM-4.7 系列 - 使用 extra_body 启用 thinking
            # 参考: https://docs.bigmodel.cn/thinking
            # 注意：GLM 返回 delta.reasoning_content，需要使用 ChatOpenAIWithReasoning
            elif "glm" in model_lower:
                kwargs["extra_body"] = {
                    "thinking": {
                        "type": "enabled",
                        "clear_thinking": False  # False=保留式思考，推荐用于 Agent 场景
                    }
                }
                # GLM 思考模式建议使用 temperature=1.0
                kwargs["temperature"] = 1.0
                logger.debug("✓ GLM-4.7 thinking enabled (using ChatOpenAIWithReasoning)")
                return ChatOpenAIWithReasoning(model=model, **kwargs)

        elif force_disable_reasoning and _enable_thinking:
            logger.info(
                f"⚠ Reasoning disabled by LLM_FORCE_DISABLE_REASONING setting (model: {model})"
            )
        return ChatOpenAI(
            model=model,
            **kwargs
        )

    # ========== Ollama (保留兼容) ==========
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        model = _model_name or settings.OLLAMA_MODEL_NAME
        base_url = _base_url or settings.OLLAMA_BASE_URL

        logger.debug(f"Initializing Ollama: {model}")

        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_ctx=4096,
            callbacks=callbacks,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def is_multimodal_enabled() -> bool:
    """
    检查当前激活配置是否支持多模态

    配置优先级:
    1. 数据库激活配置的 support_multimodal 字段
    2. .env 的 MULTIMODAL_ENABLED 配置

    Returns:
        bool: 是否启用多模态
    """
    db_config = _get_active_db_config()
    if db_config:
        return bool(db_config.get('support_multimodal'))
    return settings.MULTIMODAL_ENABLED


def get_multimodal_llm(
    temperature: float = 0.1,
    model_name: Optional[str] = None
) -> BaseChatModel:
    """
    返回支持多模态的 LLM 实例（用于图片理解）

    配置优先级:
    1. 数据库激活配置 (如果 support_multimodal=1)
    2. .env 的 MULTIMODAL_* 配置 (回退)

    Args:
        temperature: 采样温度
        model_name: 可选的模型名称覆盖

    Returns:
        BaseChatModel: 支持视觉的 LLM 实例

    Raises:
        RuntimeError: 多模态未启用时抛出
        ValueError: 不支持的多模态提供商
    """
    # 尝试从数据库获取支持多模态的配置
    db_config = _get_active_db_config()

    if db_config and db_config.get('support_multimodal'):
        # 使用数据库配置
        provider = db_config['provider'].lower()
        model = model_name or db_config['model_name']
        api_key = db_config['api_key']
        base_url = db_config['base_url']

        logger.info(f"[Multimodal] 使用数据库配置: {provider} / {model}")

        if provider == "openai":
            return init_chat_model(
                f"openai:{model}",
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
            )
        elif provider == "anthropic":
            kwargs = {
                "api_key": api_key,
                "temperature": temperature,
                "max_tokens": 8192,
            }
            if base_url:
                kwargs["base_url"] = base_url
            return init_chat_model(f"anthropic:{model}", **kwargs)
        elif provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model,
                base_url=base_url,
                temperature=temperature,
                num_ctx=4096,
            )
        else:
            raise ValueError(f"Unsupported multimodal provider: {provider}")

    # 回退到 .env 配置
    if not settings.MULTIMODAL_ENABLED:
        raise RuntimeError("Multimodal is not enabled. Set MULTIMODAL_ENABLED=true in .env or enable support_multimodal in DB config")

    provider = settings.MULTIMODAL_PROVIDER.lower()
    model = model_name or settings.MULTIMODAL_MODEL_NAME

    logger.info(f"[Multimodal] 使用 .env 配置: {provider} / {model}")

    if provider == "openai":
        logger.debug(f"Initializing OpenAI multimodal provider: {model}")
        return init_chat_model(
            f"openai:{model}",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=temperature,
        )
    elif provider == "anthropic":
        logger.debug(f"Initializing Anthropic multimodal provider: {model}")
        kwargs = {
            "api_key": settings.ANTHROPIC_API_KEY,
            "temperature": temperature,
            "max_tokens": 8192,
        }
        if settings.ANTHROPIC_BASE_URL:
            kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
        return init_chat_model(f"anthropic:{model}", **kwargs)
    else:
        raise ValueError(f"Unsupported multimodal provider: {provider}")
