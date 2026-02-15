# -*- coding: utf-8 -*-
"""
httpx compatibility helpers.

This repo historically pinned httpx==0.24.0. In that version, proxy is configured
via `proxies=...`. Newer httpx versions support `proxy=...`.

We keep a small shim so business code can pass a single proxy URL string and work
across httpx versions.
"""

from __future__ import annotations

from typing import Optional, Any, Dict

import httpx


def new_async_client(*, proxy: Optional[str] = None, **kwargs: Any) -> httpx.AsyncClient:
    if proxy:
        try:
            return httpx.AsyncClient(proxy=proxy, **kwargs)
        except TypeError:
            # httpx<0.27 uses `proxies`
            return httpx.AsyncClient(proxies=proxy, **kwargs)
    return httpx.AsyncClient(**kwargs)

