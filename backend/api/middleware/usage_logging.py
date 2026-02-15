# -*- coding: utf-8 -*-
"""
API 请求日志中间件

记录每次请求的：
- user_id（可选）
- path/method/status/latency/bytes
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import Request
from starlette.responses import Response

from config import settings
from services.auth_service import auth_service
from services.usage_service import usage_service, APIRequestLog


def _should_skip(path: str) -> bool:
    prefixes = getattr(settings, "API_LOG_EXCLUDE_PATH_PREFIXES", None) or []
    for p in prefixes:
        if path.startswith(p):
            return True
    return False


def _get_user_id_from_request(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    return auth_service.verify_access_token(token)


async def api_usage_middleware(request: Request, call_next) -> Response:
    if not getattr(settings, "API_REQUEST_LOGGING_ENABLED", True):
        return await call_next(request)

    path = request.url.path
    if _should_skip(path):
        return await call_next(request)

    start = time.monotonic()
    status_code = 500
    response: Optional[Response] = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        req_bytes = None
        resp_bytes = None
        try:
            if request.headers.get("content-length"):
                req_bytes = int(request.headers.get("content-length") or 0)
        except Exception:
            req_bytes = None
        try:
            if response is not None and response.headers.get("content-length"):
                resp_bytes = int(response.headers.get("content-length") or 0)
        except Exception:
            resp_bytes = None

        await usage_service.record_api_request(
            APIRequestLog(
                user_id=_get_user_id_from_request(request),
                method=request.method,
                path=path,
                status_code=status_code,
                latency_ms=latency_ms,
                request_bytes=req_bytes,
                response_bytes=resp_bytes,
            )
        )
