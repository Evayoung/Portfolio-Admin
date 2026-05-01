"""Environment and project configuration for Neo Admin."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in app environments
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


BASE_DIR = Path(__file__).resolve().parents[1]
if not os.getenv("VERCEL"):
    load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Neo Admin"
    owner_name: str = "Olorundare Micheal"
    session_cookie: str = "neo_admin_session"
    secret_key: str = os.getenv("NEO_ADMIN_SECRET_KEY", "neo-admin-local-dev-secret")
    admin_login_email: str = os.getenv("NEO_ADMIN_LOGIN_EMAIL") or "meshelleva@gmail.com"
    admin_login_password: str = os.getenv("NEO_ADMIN_LOGIN_PASSWORD") or "Password123!"
    base_url: str = os.getenv("NEO_ADMIN_BASE_URL", "http://127.0.0.1:5063")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    github_username: str = os.getenv("GITHUB_USERNAME", "Evayoung")
    github_access_token: str = os.getenv("GITHUB_ACCESS_TOKEN", "")
    supabase_schema_path: str = "app/infrastructure/sql/001_initial_schema.sql"
    use_cdn: bool = bool(os.getenv("VERCEL"))
    port: int = int(os.getenv("PORT", "5063"))
    # Email notifications (Resend API — optional)
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    admin_notify_email: str = os.getenv("ADMIN_NOTIFY_EMAIL", "") or os.getenv("NEO_ADMIN_LOGIN_EMAIL", "")
    email_from: str = os.getenv("EMAIL_FROM", "noreply@neoportfolio.dev")
    email_enabled: bool = bool(os.getenv("RESEND_API_KEY", ""))


settings = Settings()


def _validate_production_settings() -> None:
    if not os.getenv("VERCEL"):
        return
    if settings.secret_key in {"", "neo-admin-local-dev-secret", "replace-with-a-secure-secret"}:
        raise RuntimeError("NEO_ADMIN_SECRET_KEY must be set to a secure value in production.")
    if settings.admin_login_password in {"", "Password123!", "replace-with-a-strong-password"}:
        raise RuntimeError("NEO_ADMIN_LOGIN_PASSWORD must be changed before deploying Neo Admin.")
    if (
        settings.supabase_url in {"", "https://your-project-id.supabase.co"}
        or settings.supabase_service_role_key in {"", "your-service-role-key"}
    ):
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in production.")


_validate_production_settings()
