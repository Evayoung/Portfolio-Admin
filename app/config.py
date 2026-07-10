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
    secret_key: str = os.getenv("NEO_ADMIN_SECRET_KEY", "")
    admin_login_email: str = os.getenv("NEO_ADMIN_LOGIN_EMAIL") or "admin@example.com"
    admin_login_password: str = os.getenv("NEO_ADMIN_LOGIN_PASSWORD") or "change-me-before-deploy"
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
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    groq_enabled: bool = bool(os.getenv("GROQ_API_KEY", ""))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")


settings = Settings()


def _validate_production_settings() -> None:
    import warnings

    # Always warn about insecure defaults (not just on Vercel)
    if not settings.secret_key:
        warnings.warn(
            "NEO_ADMIN_SECRET_KEY is not set. Sessions are insecure. "
            "Set it in your .env file.",
            stacklevel=2,
        )
    if settings.admin_login_password in ("change-me-before-deploy", ""):
        warnings.warn(
            "NEO_ADMIN_LOGIN_PASSWORD is using the insecure default. "
            "Change it before deploying.",
            stacklevel=2,
        )

    if not os.getenv("VERCEL"):
        return

    # Production: raise errors instead of warnings
    raw_secret = os.getenv("NEO_ADMIN_SECRET_KEY")
    if not raw_secret or raw_secret in {"neo-admin-local-dev-secret", "replace-with-a-secure-secret", ""}:
        raise RuntimeError("NEO_ADMIN_SECRET_KEY must be set to a secure value in production.")
    raw_pwd = os.getenv("NEO_ADMIN_LOGIN_PASSWORD")
    if raw_pwd is not None and raw_pwd in {"Password123!", "replace-with-a-strong-password", "change-me-before-deploy"}:
        raise RuntimeError("NEO_ADMIN_LOGIN_PASSWORD must be changed before deploying Neo Admin.")
    raw_supabase_url = os.getenv("SUPABASE_URL")
    raw_service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if (
        raw_supabase_url is not None and raw_supabase_url in {"https://your-project-id.supabase.co"}
        or raw_service_role is not None and raw_service_role in {"your-service-role-key"}
    ):
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in production.")


_validate_production_settings()
