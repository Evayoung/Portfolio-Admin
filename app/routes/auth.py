"""Authentication routes — login, logout."""

from __future__ import annotations

from typing import Any
from fasthtml.common import Redirect

try:
    from ..config import settings
    from ..infrastructure.auth_repository import authenticate_admin, save_admin_access
    from ..presentation.pages.auth import login_page
    from .helpers import _safe_next_path
except ImportError:
    from config import settings
    from infrastructure.auth_repository import authenticate_admin, save_admin_access
    from presentation.pages.auth import login_page
    from routes.helpers import _safe_next_path


def setup_auth_routes(app: Any) -> None:
    @app.get("/login")
    def login(session, next_path: str = "/") -> Any:
        if session.get("admin_authenticated"):
            return Redirect(_safe_next_path(next_path))
        return login_page(next_path=_safe_next_path(next_path))

    @app.post("/login")
    def login_submit(session, login_email: str = "", password: str = "", next_path: str = "/") -> Any:
        result = authenticate_admin(login_email, password)
        if not result.success:
            return login_page(
                next_path=_safe_next_path(next_path),
                message=result.message,
                tone=result.tone,
                login_email=login_email,
            )
        session["admin_authenticated"] = True
        session["admin_login_email"] = result.login_email
        return Redirect(_safe_next_path(next_path))

    @app.get("/logout")
    def logout(session) -> Any:
        session.clear()
        return Redirect("/login")
