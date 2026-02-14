# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/services/asr_service.py
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
ASR 服务 - 语音转文字

使用 FunASR (paraformer-zh + fsmn-vad + ct-punc) 作为主后端，
实现带句子级时间戳的语音转文字服务。

架构设计:
- AudioPreprocessor: 音频预处理（转换为 16kHz mono wav）
- FunASRBackend: FunASR 转录后端（懒加载单例）
- SegmentBuilder: 句子切分器（标点/长度/时长/间隙）
- ASRService: 统一入口（单例模式）

参考文章： https://wangjunjian.com/funasr/asr/2025/12/06/FunASR.html
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from config import settings
from schemas import Segment, TranscriptResult
from utils.logger import logger


class ASRError(Exception):
    """ASR 统一错误类型"""

    pass


# =============================================================================
# 内部数据结构
# =============================================================================


@dataclass
class Token:
    """词级时间戳单元"""

    text: str
    start_ms: int  # 毫秒
    end_ms: int  # 毫秒


@dataclass
class RawTranscriptResult:
    """FunASR 原始转录结果"""

    text: str
    tokens: List[Token] = field(default_factory=list)
    vad_segments: List[Tuple[int, int]] = field(default_factory=list)  # [(start_ms, end_ms), ...]


# =============================================================================
# 音频预处理器
# =============================================================================


class AudioPreprocessor:
    """
    音频预处理器 - 转换为 16kHz mono WAV

    使用 ffmpeg 将各种音频格式转换为 FunASR 所需的格式
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or settings.ASR_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def preprocess(self, audio_path: str) -> str:
        """
        预处理音频文件

        Args:
            audio_path: 输入音频路径（支持 mp4/wav/mp3/m4a 等）

        Returns:
            str: 转换后的 16kHz mono wav 文件路径

        Raises:
            ASRError: 文件不存在或转换失败
        """
        input_path = Path(audio_path)

        if not input_path.exists():
            raise ASRError(f"音频文件不存在: {audio_path}")

        # 如果已是 wav 且符合要求，检查采样率
        if input_path.suffix.lower() == ".wav":
            if self._check_wav_format(str(input_path)):
                logger.debug(f"音频已是正确格式，跳过转换: {audio_path}")
                return str(input_path)

        # 生成输出路径
        output_path = self.cache_dir / f"{input_path.stem}_{os.getpid()}.wav"

        # ffmpeg 转换
        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-ar",
            "16000",  # 采样率 16kHz
            "-ac",
            "1",  # 单声道
            "-f",
            "wav",  # 输出格式
            "-y",  # 覆盖已存在文件
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error(f"ffmpeg 转换失败: {result.stderr}")
                raise ASRError(f"音频预处理失败: {result.stderr[:200]}")

            logger.debug(f"音频预处理完成: {audio_path} -> {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            raise ASRError("音频预处理超时")
        except FileNotFoundError:
            raise ASRError("ffmpeg 未安装，请安装 ffmpeg")

    def _check_wav_format(self, wav_path: str) -> bool:
        """检查 wav 文件是否符合 16kHz mono 格式"""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "csv=p=0",
            wav_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                output = result.stdout.strip()
                parts = output.split(",")
                if len(parts) == 2:
                    sample_rate = int(parts[0])
                    channels = int(parts[1])
                    return sample_rate == 16000 and channels == 1
        except Exception:
            pass
        return False

    def cleanup(self, wav_path: str) -> None:
        """清理临时文件"""
        try:
            path = Path(wav_path)
            if path.exists() and path.parent == self.cache_dir:
                path.unlink()
                logger.debug(f"清理临时文件: {wav_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")


# =============================================================================
# FunASR 后端
# =============================================================================


class FunASRBackend:
    """
    FunASR 转录后端

    使用 paraformer-zh + fsmn-vad + ct-punc 实现高质量中文 ASR
    模型懒加载，首次调用时初始化
    """

    _instance: Optional["FunASRBackend"] = None
    _model = None
    _available: Optional[bool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> None:
        """懒加载模型"""
        if self._model is not None:
            return

        try:
            from funasr import AutoModel

            logger.info(
                f"正在加载 FunASR 模型: {settings.ASR_MODEL} "
                f"(VAD: {settings.ASR_VAD_MODEL}, PUNC: {settings.ASR_PUNC_MODEL})"
            )

            self._model = AutoModel(
                model=settings.ASR_MODEL,
                vad_model=settings.ASR_VAD_MODEL,
                punc_model=settings.ASR_PUNC_MODEL,
                device=settings.ASR_DEVICE,
            )

            logger.info("FunASR 模型加载完成")
            self._available = True

        except ImportError:
            logger.error("FunASR 未安装，请运行: pip install funasr")
            self._available = False
            raise ASRError("FunASR 未安装")
        except Exception as e:
            logger.error(f"FunASR 模型加载失败: {e}")
            self._available = False
            raise ASRError(f"模型加载失败: {e}")

    def is_available(self) -> bool:
        """检查 FunASR 是否可用"""
        if self._available is not None:
            return self._available

        try:
            import funasr  # noqa: F401

            self._available = True
        except ImportError:
            self._available = False

        return self._available

    def transcribe(self, wav_path: str) -> RawTranscriptResult:
        """
        转录音频文件

        Args:
            wav_path: 16kHz mono WAV 文件路径

        Returns:
            RawTranscriptResult: 包含文本和词级时间戳

        Raises:
            ASRError: 转录失败
        """
        self._load_model()

        try:
            # FunASR generate 调用
            # timestamp=True 启用词级时间戳
            result = self._model.generate(
                input=wav_path,
                batch_size_s=300,  # 批处理秒数
                hotword="",  # 热词（可选）
            )

            if not result:
                raise ASRError("转录结果为空")

            # 解析结果
            # FunASR 返回格式: [{"text": "...", "timestamp": [[start_ms, end_ms], ...]}]
            # timestamp 是字符级时间戳，与 text 中的字符一一对应
            item = result[0] if isinstance(result, list) else result

            text = item.get("text", "")
            timestamp_data = item.get("timestamp", [])

            # 解析字符级时间戳
            # timestamp 格式: [[start_ms, end_ms], [start_ms, end_ms], ...]
            tokens = []
            for i, ts in enumerate(timestamp_data):
                if len(ts) >= 2 and i < len(text):
                    start_ms = int(ts[0])
                    end_ms = int(ts[1])
                    char = text[i]
                    tokens.append(Token(text=char, start_ms=start_ms, end_ms=end_ms))

            logger.debug(f"转录完成: {len(text)} 字符, {len(tokens)} 时间戳")

            return RawTranscriptResult(text=text, tokens=tokens)

        except ASRError:
            raise
        except Exception as e:
            logger.error(f"FunASR 转录失败: {e}")
            raise ASRError(f"语音识别失败: {e}")


# =============================================================================
# Bcut ASR 后端 (B站必剪云端API)
# =============================================================================


class BcutASRBackend:
    """
    B站必剪 ASR 云端后端

    使用 B站必剪 APP 的逆向 API 实现云端 ASR
    流程: 上传音频 -> 创建任务 -> 轮询结果
    """

    API_BASE_URL = "https://member.bilibili.com/x/bcut/rubick-interface"
    API_REQ_UPLOAD = API_BASE_URL + "/resource/create"
    API_COMMIT_UPLOAD = API_BASE_URL + "/resource/create/complete"
    API_CREATE_TASK = API_BASE_URL + "/task"
    API_QUERY_RESULT = API_BASE_URL + "/task/result"

    HEADERS = {
        "User-Agent": "Bilibili/1.0.0 (https://www.bilibili.com)",
        "Content-Type": "application/json",
    }

    _instance: Optional["BcutASRBackend"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._session = None

    def _get_session(self):
        """获取 requests session"""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def is_available(self) -> bool:
        """检查 Bcut API 是否可用（始终可用，只需网络）"""
        try:
            import requests  # noqa: F401
            return True
        except ImportError:
            return False

    def transcribe(self, audio_path: str) -> RawTranscriptResult:
        """
        转录音频文件

        Args:
            audio_path: 音频文件路径

        Returns:
            RawTranscriptResult: 包含文本和词级时间戳

        Raises:
            ASRError: 转录失败
        """
        import json
        import time
        import requests

        try:
            # 1. 读取音频文件
            audio_path = Path(audio_path)
            if not audio_path.exists():
                raise ASRError(f"音频文件不存在: {audio_path}")

            with open(audio_path, "rb") as f:
                file_binary = f.read()

            file_size = len(file_binary)
            logger.info(f"Bcut ASR: 上传音频 {file_size / 1024:.1f} KB")

            # 2. 请求上传授权
            payload = json.dumps({
                "type": 2,
                "name": "audio.mp3",
                "size": file_size,
                "ResourceFileType": "mp3",
                "model_id": "8",
            })

            resp = requests.post(
                self.API_REQ_UPLOAD,
                data=payload,
                headers=self.HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("code") != 0:
                raise ASRError(f"上传授权失败: {resp_data.get('message')}")

            upload_data = resp_data["data"]
            in_boss_key = upload_data["in_boss_key"]
            resource_id = upload_data["resource_id"]
            upload_id = upload_data["upload_id"]
            upload_urls = upload_data["upload_urls"]
            per_size = upload_data["per_size"]

            # 3. 分片上传
            etags = []
            for i, url in enumerate(upload_urls):
                start = i * per_size
                end = (i + 1) * per_size
                chunk = file_binary[start:end]

                resp = requests.put(url, data=chunk, headers=self.HEADERS, timeout=60)
                resp.raise_for_status()
                etag = resp.headers.get("Etag")
                if etag:
                    etags.append(etag)

            logger.debug(f"Bcut ASR: 上传完成, {len(etags)} 片")

            # 4. 提交上传
            commit_data = json.dumps({
                "InBossKey": in_boss_key,
                "ResourceId": resource_id,
                "Etags": ",".join(etags) if etags else "",
                "UploadId": upload_id,
                "model_id": "8",
            })

            resp = requests.post(
                self.API_COMMIT_UPLOAD,
                data=commit_data,
                headers=self.HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("code") != 0:
                raise ASRError(f"提交上传失败: {resp_data.get('message')}")

            download_url = resp_data["data"]["download_url"]

            # 5. 创建 ASR 任务
            resp = requests.post(
                self.API_CREATE_TASK,
                json={"resource": download_url, "model_id": "8"},
                headers=self.HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("code") != 0:
                raise ASRError(f"创建任务失败: {resp_data.get('message')}")

            task_id = resp_data["data"]["task_id"]
            logger.info(f"Bcut ASR: 任务创建成功, task_id={task_id}")

            # 6. 轮询任务结果
            poll_interval = settings.BCUT_POLL_INTERVAL
            max_retries = settings.BCUT_MAX_RETRIES
            task_result = None

            for i in range(max_retries):
                resp = requests.get(
                    self.API_QUERY_RESULT,
                    params={"model_id": 7, "task_id": task_id},
                    headers=self.HEADERS,
                    timeout=30,
                )
                resp.raise_for_status()
                resp_data = resp.json()

                if resp_data.get("code") != 0:
                    raise ASRError(f"查询结果失败: {resp_data.get('message')}")

                task_data = resp_data["data"]
                state = task_data.get("state", 0)

                if state == 4:  # 完成
                    task_result = json.loads(task_data["result"])
                    break
                elif state == -1:  # 失败
                    raise ASRError("ASR 任务失败")

                if i % 10 == 0:
                    logger.debug(f"Bcut ASR: 等待结果... ({i}/{max_retries})")

                time.sleep(poll_interval)

            if task_result is None:
                raise ASRError("ASR 任务超时")

            # 7. 解析结果
            return self._parse_result(task_result)

        except ASRError:
            raise
        except Exception as e:
            logger.error(f"Bcut ASR 失败: {e}")
            raise ASRError(f"Bcut ASR 失败: {e}")

    def _parse_result(self, result: dict) -> RawTranscriptResult:
        """解析 Bcut API 返回结果"""
        utterances = result.get("utterances", [])

        # 合并所有 utterance 的文本
        full_text = ""
        tokens = []

        for utterance in utterances:
            transcript = utterance.get("transcript", "")
            start_time = utterance.get("start_time", 0)
            end_time = utterance.get("end_time", 0)
            words = utterance.get("words", [])

            if words:
                # 如果有词级时间戳，使用词级
                for word in words:
                    word_text = word.get("label", "").strip()
                    word_start = word.get("start_time", 0)
                    word_end = word.get("end_time", 0)
                    if word_text:
                        tokens.append(Token(
                            text=word_text,
                            start_ms=word_start,
                            end_ms=word_end,
                        ))
                        full_text += word_text
            else:
                # 否则使用句子级，按字符比例分配时间戳
                if transcript:
                    char_duration = (end_time - start_time) / max(len(transcript), 1)
                    for i, char in enumerate(transcript):
                        char_start = int(start_time + i * char_duration)
                        char_end = int(start_time + (i + 1) * char_duration)
                        tokens.append(Token(
                            text=char,
                            start_ms=char_start,
                            end_ms=char_end,
                        ))
                    full_text += transcript

        logger.debug(f"Bcut ASR 解析完成: {len(full_text)} 字符, {len(tokens)} 词")

        return RawTranscriptResult(text=full_text, tokens=tokens)


# =============================================================================
# 句子切分器
# =============================================================================


class SegmentBuilder:
    """
    句子切分器

    将词级时间戳聚合为句子级分段，支持多种切分策略:
    - 按标点切分 (。！？；…)
    - 按长度切分 (max 20 字符)
    - 按时长切分 (max 6 秒)
    - 按间隙切分 (gap > 0.6s)
    """

    # 句子结束标点
    SENTENCE_ENDINGS = {"。", "！", "？", "；", "…", "!", "?", ";"}
    # 次要切分标点（逗号等）
    MINOR_BREAKS = {"，", ",", "、"}

    def __init__(
        self,
        max_chars: int = 20,
        max_seconds: float = 6.0,
        min_seconds: float = 0.5,
        gap_split: float = 0.6,
    ):
        self.max_chars = max_chars
        self.max_seconds = max_seconds
        self.min_seconds = min_seconds
        self.gap_split_ms = int(gap_split * 1000)

    def build_segments(self, raw_result: RawTranscriptResult) -> List[Segment]:
        """
        构建句子级分段

        Args:
            raw_result: FunASR 原始转录结果

        Returns:
            List[Segment]: 句子级分段列表
        """
        if not raw_result.text:
            return []

        # 如果有词级时间戳，使用精确切分
        if raw_result.tokens:
            return self._build_from_tokens(raw_result.tokens)

        # 否则使用标点切分 + 比例分配时间戳
        return self._build_from_text_only(raw_result.text, raw_result.vad_segments)

    def _build_from_tokens(self, tokens: List[Token]) -> List[Segment]:
        """从词级时间戳构建分段"""
        if not tokens:
            return []

        segments = []
        current_tokens: List[Token] = []
        current_text = ""

        for i, token in enumerate(tokens):
            current_tokens.append(token)
            current_text += token.text

            # 检查是否需要切分
            should_split = False
            reason = ""

            # 1. 标点切分
            if token.text in self.SENTENCE_ENDINGS:
                should_split = True
                reason = "punctuation"

            # 2. 长度切分
            elif len(current_text) >= self.max_chars:
                # 尝试在次要标点处切分
                if token.text in self.MINOR_BREAKS:
                    should_split = True
                    reason = "length_at_break"
                elif len(current_text) > self.max_chars:
                    should_split = True
                    reason = "length_exceeded"

            # 3. 时长切分
            elif current_tokens:
                duration_ms = token.end_ms - current_tokens[0].start_ms
                if duration_ms >= self.max_seconds * 1000:
                    should_split = True
                    reason = "duration"

            # 4. 间隙切分
            if not should_split and i + 1 < len(tokens):
                gap = tokens[i + 1].start_ms - token.end_ms
                if gap >= self.gap_split_ms:
                    should_split = True
                    reason = "gap"

            if should_split and current_tokens:
                segment = self._create_segment_from_tokens(current_tokens)
                if segment:
                    segments.append(segment)
                    logger.debug(f"切分 ({reason}): [{segment.start:.2f}-{segment.end:.2f}] {segment.text}")
                current_tokens = []
                current_text = ""

        # 处理剩余的 tokens
        if current_tokens:
            segment = self._create_segment_from_tokens(current_tokens)
            if segment:
                segments.append(segment)

        return segments

    def _create_segment_from_tokens(self, tokens: List[Token]) -> Optional[Segment]:
        """从 token 列表创建 Segment"""
        if not tokens:
            return None

        text = "".join(t.text for t in tokens).strip()
        if not text:
            return None

        start = tokens[0].start_ms / 1000.0
        end = tokens[-1].end_ms / 1000.0

        # 确保最小时长
        if end - start < self.min_seconds:
            end = start + self.min_seconds

        return Segment(start=start, end=end, text=text)

    def _build_from_text_only(
        self, text: str, vad_segments: List[Tuple[int, int]]
    ) -> List[Segment]:
        """
        仅从文本构建分段（无词级时间戳时的回退方案）

        使用标点切分文本，然后按字符比例分配时间戳
        """
        # 按标点切分
        sentences = self._split_by_punctuation(text)
        if not sentences:
            return []

        # 计算总时长
        if vad_segments:
            total_start = vad_segments[0][0]
            total_end = vad_segments[-1][1]
        else:
            # 假设每秒 4 个字符的语速
            total_start = 0
            total_end = int(len(text) / 4 * 1000)

        # 按字符比例分配时间戳
        return self._assign_timestamps_proportional(
            sentences, total_start, total_end
        )

    def _split_by_punctuation(self, text: str) -> List[str]:
        """按标点切分文本"""
        # 匹配句子结束标点
        pattern = r"([。！？；…!?;])"
        parts = re.split(pattern, text)

        sentences = []
        current = ""

        for part in parts:
            if part in self.SENTENCE_ENDINGS:
                current += part
                if current.strip():
                    sentences.append(current.strip())
                current = ""
            else:
                current += part

        if current.strip():
            sentences.append(current.strip())

        # 进一步按长度切分
        result = []
        for sentence in sentences:
            if len(sentence) <= self.max_chars:
                result.append(sentence)
            else:
                # 按逗号切分长句
                sub_parts = re.split(r"([，,、])", sentence)
                sub_current = ""
                for sub_part in sub_parts:
                    if len(sub_current) + len(sub_part) <= self.max_chars:
                        sub_current += sub_part
                    else:
                        if sub_current.strip():
                            result.append(sub_current.strip())
                        sub_current = sub_part
                if sub_current.strip():
                    result.append(sub_current.strip())

        return result

    def _assign_timestamps_proportional(
        self, sentences: List[str], total_start_ms: int, total_end_ms: int
    ) -> List[Segment]:
        """按字符比例分配时间戳"""
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            return []

        total_duration = total_end_ms - total_start_ms
        segments = []
        current_start = total_start_ms

        for sentence in sentences:
            duration = int(total_duration * len(sentence) / total_chars)
            end = current_start + duration

            segment = Segment(
                start=current_start / 1000.0,
                end=end / 1000.0,
                text=sentence,
            )
            segments.append(segment)
            current_start = end

        return segments


# =============================================================================
# Mock ASR 服务（测试用）
# =============================================================================


class MockASRService:
    """Mock ASR 服务 - 用于测试和开发"""

    def transcribe(self, audio_path: str) -> TranscriptResult:  # noqa: ARG002
        """返回模拟的转录结果"""
        _ = audio_path  # 未使用，仅保持接口一致
        mock_segments = [
            Segment(start=0.0, end=2.5, text="这是一段模拟的语音转录结果。"),
            Segment(start=2.5, end=5.0, text="用于测试 ASR 服务的功能。"),
            Segment(start=5.0, end=8.0, text="真实环境请使用 FunASR 后端。"),
        ]

        full_text = "".join(s.text for s in mock_segments)

        return TranscriptResult(text=full_text, segments=mock_segments)

    def is_available(self) -> bool:
        """Mock 服务始终可用"""
        return True

    def preload(self) -> None:
        """Mock 预加载（无操作）"""
        pass


# =============================================================================
# ASR 服务（统一入口）
# =============================================================================


class ASRService:
    """
    语音转文字服务 - 统一入口

    单例模式，根据配置自动选择后端:
    - funasr: FunASR 本地模型（默认）
    - bcut: B站必剪云端 API
    """

    _instance: Optional["ASRService"] = None
    _preprocessor: Optional[AudioPreprocessor] = None
    _backend = None  # FunASRBackend 或 BcutASRBackend
    _segment_builder: Optional[SegmentBuilder] = None
    _backend_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """初始化组件"""
        self._preprocessor = AudioPreprocessor()
        self._segment_builder = SegmentBuilder(
            max_chars=settings.SEG_MAX_CHARS,
            max_seconds=settings.SEG_MAX_SECONDS,
            min_seconds=settings.SEG_MIN_SECONDS,
            gap_split=settings.SEG_GAP_SPLIT,
        )

        # 根据配置选择后端
        backend_name = settings.ASR_BACKEND.lower()
        self._backend_name = backend_name

        if backend_name == "bcut":
            logger.info("ASR 后端: Bcut (B站必剪云端API)")
            self._backend = BcutASRBackend()
        else:
            logger.info("ASR 后端: FunASR (本地模型)")
            self._backend = FunASRBackend()

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """
        转录音频

        Args:
            audio_path: 音频文件路径（支持 mp4/wav/mp3/m4a 等）

        Returns:
            TranscriptResult: 包含完整文本和句子级时间戳分段

        Raises:
            ASRError: 转录失败
        """
        wav_path = None
        temp_file = False

        try:
            # 1. 音频预处理
            logger.info(f"开始转录: {audio_path}")
            wav_path = self._preprocessor.preprocess(audio_path)
            temp_file = wav_path != audio_path

            # 2. FunASR 转录
            raw_result = self._backend.transcribe(wav_path)

            # 3. 句子切分
            segments = self._segment_builder.build_segments(raw_result)

            logger.info(f"转录完成: {len(raw_result.text)} 字符, {len(segments)} 段")

            return TranscriptResult(text=raw_result.text, segments=segments)

        except ASRError:
            raise
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise ASRError(f"转录失败: {e}")
        finally:
            # 清理临时文件
            if temp_file and wav_path:
                self._preprocessor.cleanup(wav_path)

    def is_available(self) -> bool:
        """检查 ASR 服务是否可用"""
        return self._backend.is_available()

    def preload(self) -> None:
        """
        预加载模型

        在应用启动时调用，避免首次转录时的延迟
        仅对 FunASR 本地模型有效，Bcut API 无需预加载
        """
        # Bcut 后端无需预加载
        if self._backend_name == "bcut":
            logger.info("Bcut 后端无需预加载")
            return

        if not self.is_available():
            logger.warning("FunASR 不可用，跳过预加载")
            return

        try:
            logger.info("预加载 FunASR 模型...")
            self._backend._load_model()
            logger.info("FunASR 模型预加载完成")
        except Exception as e:
            logger.error(f"模型预加载失败: {e}")

    @property
    def backend_name(self) -> str:
        """获取当前后端名称"""
        return self._backend_name


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "ASRError",
    "ASRService",
    "MockASRService",
    "AudioPreprocessor",
    "FunASRBackend",
    "BcutASRBackend",
    "SegmentBuilder",
    "Token",
    "RawTranscriptResult",
]
