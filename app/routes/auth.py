"""Authentication routes — login, logout."""

from __future__ import annotations

from typing import Any
from fasthtml.common import Request, Redirect

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
    def login_submit(req: Request, session, login_email: str = "", password: str = "", next_path: str = "/", _trap: str = "") -> Any:
        # Check session expiry (8-hour rolling window)
        import time as _time
        expires_at = session.get("expires_at", 0)
        if expires_at and _time.time() > expires_at:
            session.clear()
        # Honeypot: real browsers never fill the hidden _trap field
        if _trap:
            return login_page(next_path=_safe_next_path(next_path))
        # Extract client IP for rate limiting
        client_ip = req.headers.get("x-forwarded-for", req.headers.get("x-real-ip", "")).split(",")[0].strip()
        result = authenticate_admin(login_email, password, ip=client_ip)
        if not result.success:
            return login_page(
                next_path=_safe_next_path(next_path),
                message=result.message,
                tone=result.tone,
                login_email=login_email,
            )
        session["admin_authenticated"] = True
        session["admin_login_email"] = result.login_email
        session["expires_at"] = _time.time() + (8 * 3600)  # 8-hour session
        return Redirect(_safe_next_path(next_path))

    @app.get("/logout")
    def logout(session) -> Any:
        session.clear()
        return Redirect("/login")
