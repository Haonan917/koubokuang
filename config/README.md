# Config Directory

This directory centralizes runtime configuration for `start_all.sh` and `start.sh`.

Load order:
1. `config/common.env`
2. `config/<service>.env`

Supported service files:
- `config/backend.env`
- `config/download.env`
- `config/signsrv.env`
- `config/frontend.env`

Notes:
- Environment variables from later files override earlier ones.
- Existing legacy files like `backend/.env` are still supported as fallback.
- Do not commit secrets into Git. Put real values in local `.env` files only.

- Single source of truth:
  - `CRAWLER_DB_*` is defined in `config/common.env` and is shared by backend + DownloadServer.
- Platform cookies can be set in `config/backend.env` via:
  - `PLATFORM_COOKIES_XHS`
  - `PLATFORM_COOKIES_DY`
  - `PLATFORM_COOKIES_BILI`
  - `PLATFORM_COOKIES_KS`
  If set, backend uses them first; otherwise it falls back to DB `platform_cookies`.

- Admin / management:
  - After running migrations, use `backend/scripts/set_admin.py` to grant admin:
    - `uv run python scripts/set_admin.py you@example.com`
  - Admin APIs are under `/api/v1/admin/*` and require `users.is_admin=1` (or `ADMIN_TOKEN` via `X-Admin-Token`).

- Usage & cost estimation:
  - Enable via `USAGE_LOGGING_ENABLED=true` and `API_REQUEST_LOGGING_ENABLED=true` in `config/backend.env`.
  - Optional pricing mapping (JSON): `MODEL_PRICING_USD_PER_1M`.
