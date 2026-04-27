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
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Neo Admin"
    owner_name: str = "Olorundare Micheal"
    session_cookie: str = "neo_admin_session"
    secret_key: str = os.getenv("NEO_ADMIN_SECRET_KEY", "neo-admin-local-dev-secret")
    admin_login_email: str = os.getenv("NEO_ADMIN_LOGIN_EMAIL", "admin@neoportfolio.dev")
    admin_login_password: str = os.getenv("NEO_ADMIN_LOGIN_PASSWORD", "ChangeMe123!")
    base_url: str = os.getenv("NEO_ADMIN_BASE_URL", "http://127.0.0.1:5063")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase_schema_path: str = "app/infrastructure/sql/001_initial_schema.sql"
    use_cdn: bool = bool(os.getenv("VERCEL"))
    port: int = int(os.getenv("PORT", "5063"))


settings = Settings()
