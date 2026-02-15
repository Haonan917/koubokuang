# -*- coding: utf-8 -*-
"""
Usage / Billing 统计服务

目标：
- 记录 LLM token 用量（估算费用）
- 记录 API 请求（计数/审计/基础统计）
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from sqlalchemy import text

from config import settings
from db.base import get_async_session
from utils.logger import logger


def _guess_provider() -> Optional[str]:
    provider = (getattr(settings, "LLM_PROVIDER", None) or "").strip().lower()
    if provider and provider != "openai":
        return provider

    base_url = (getattr(settings, "OPENAI_BASE_URL", None) or "").strip().lower()
    if "openrouter.ai" in base_url:
        return "openrouter"
    if base_url:
        return "openai-compatible"
    return provider or None


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    pricing = getattr(settings, "MODEL_PRICING_USD_PER_1M", {}) or {}
    item = pricing.get(model)
    if not isinstance(item, dict):
        return None
    try:
        in_rate = float(item.get("input_per_1m") or 0.0)
        out_rate = float(item.get("output_per_1m") or 0.0)
        if in_rate <= 0 and out_rate <= 0:
            return None
        return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate
    except Exception:
        return None


@dataclass
class LLMUsageEvent:
    user_id: Optional[str]
    session_id: Optional[str]
    endpoint: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: Optional[int] = None
    success: bool = True
    error: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class APIRequestLog:
    user_id: Optional[str]
    method: str
    path: str
    status_code: int
    latency_ms: int
    request_bytes: Optional[int] = None
    response_bytes: Optional[int] = None


class UsageService:
    async def record_llm_usage(self, event: LLMUsageEvent) -> None:
        if not getattr(settings, "USAGE_LOGGING_ENABLED", True):
            return
        try:
            provider = event.provider or _guess_provider()
            total = int(event.input_tokens or 0) + int(event.output_tokens or 0)
            model = (event.model or "").strip() or "unknown"
            cost = estimate_cost_usd(model, int(event.input_tokens or 0), int(event.output_tokens or 0))
            error = (event.error or None)
            if error and len(error) > 255:
                error = error[:255]

            async with get_async_session() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO llm_usage_events
                          (user_id, session_id, endpoint, provider, model,
                           input_tokens, output_tokens, total_tokens,
                           estimated_cost_usd, latency_ms, success, error)
                        VALUES
                          (:user_id, :session_id, :endpoint, :provider, :model,
                           :input_tokens, :output_tokens, :total_tokens,
                           :estimated_cost_usd, :latency_ms, :success, :error)
                        """
                    ),
                    {
                        "user_id": event.user_id,
                        "session_id": event.session_id,
                        "endpoint": event.endpoint,
                        "provider": provider,
                        "model": model,
                        "input_tokens": int(event.input_tokens or 0),
                        "output_tokens": int(event.output_tokens or 0),
                        "total_tokens": total,
                        "estimated_cost_usd": cost,
                        "latency_ms": event.latency_ms,
                        "success": 1 if event.success else 0,
                        "error": error,
                    },
                )
        except Exception as e:
            logger.debug(f"[UsageService] record_llm_usage failed: {e}")

    async def record_api_request(self, log: APIRequestLog) -> None:
        if not getattr(settings, "API_REQUEST_LOGGING_ENABLED", True):
            return
        try:
            async with get_async_session() as session:
                await session.execute(
                    text(
                        """
                        INSERT INTO api_request_logs
                          (user_id, method, path, status_code, latency_ms, request_bytes, response_bytes)
                        VALUES
                          (:user_id, :method, :path, :status_code, :latency_ms, :request_bytes, :response_bytes)
                        """
                    ),
                    {
                        "user_id": log.user_id,
                        "method": (log.method or "")[:10],
                        "path": (log.path or "")[:255],
                        "status_code": int(log.status_code),
                        "latency_ms": int(log.latency_ms),
                        "request_bytes": log.request_bytes,
                        "response_bytes": log.response_bytes,
                    },
                )
        except Exception as e:
            logger.debug(f"[UsageService] record_api_request failed: {e}")

    async def get_llm_usage_summary(
        self,
        days: int = 7,
        model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        where = "created_at >= (NOW() - INTERVAL :days DAY)"
        params: Dict[str, Any] = {"days": int(days)}
        if model:
            where += " AND model = :model"
            params["model"] = model

        async with get_async_session() as session:
            result = await session.execute(
                text(
                    f"""
                    SELECT
                      DATE(created_at) AS day,
                      model,
                      SUM(input_tokens) AS input_tokens,
                      SUM(output_tokens) AS output_tokens,
                      SUM(total_tokens) AS total_tokens,
                      SUM(COALESCE(estimated_cost_usd, 0)) AS estimated_cost_usd,
                      COUNT(*) AS calls
                    FROM llm_usage_events
                    WHERE {where}
                    GROUP BY DATE(created_at), model
                    ORDER BY day DESC, estimated_cost_usd DESC
                    """
                ),
                params,
            )
            return [dict(row) for row in result.mappings().all()]


usage_service = UsageService()

