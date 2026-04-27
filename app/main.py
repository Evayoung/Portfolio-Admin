"""FastHTML app shell for Neo Admin."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fasthtml.common import Beforeware, FastHTML, Link, Meta, Redirect, Script, serve
from faststrap import add_bootstrap, mount_assets

try:
    from .config import settings
    from .routes import setup_routes
    from .theme import NEO_ADMIN_THEME, setup_theme_defaults
except ImportError:
    from config import settings
    from routes import setup_routes
    from theme import NEO_ADMIN_THEME, setup_theme_defaults

BASE_DIR = Path(__file__).resolve().parent.parent


def _require_admin_login(req, session):
    if session.get("admin_authenticated"):
        return None
    next_path = req.url.path
    if req.url.query:
        next_path = f"{next_path}?{req.url.query}"
    return Redirect(f"/login?next_path={quote(next_path, safe='/?=&')}")


app = FastHTML(secret_key=settings.secret_key, session_cookie=settings.session_cookie)
app.before.append(
    Beforeware(
        _require_admin_login,
        skip=[r"/login", r"/logout", r"/assets/.*", r"/favicon.ico"],
    )
)

add_bootstrap(app, theme=NEO_ADMIN_THEME, mode="dark", use_cdn=settings.use_cdn)
setup_theme_defaults()

if not settings.use_cdn:
    mount_assets(app, str(BASE_DIR / "assets"), url_path="/assets")

app.hdrs = app.hdrs + [
    Link(rel="preconnect", href="https://fonts.googleapis.com"),
    Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin="anonymous"),
    Link(
        rel="stylesheet",
        href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap",
    ),
    Meta(name="theme-color", content="#091321"),
    Meta(name="mobile-web-app-capable", content="yes"),
    Meta(name="apple-mobile-web-app-capable", content="yes"),
    Meta(name="apple-mobile-web-app-status-bar-style", content="black-translucent"),
    Meta(name="apple-mobile-web-app-title", content="Neo Admin"),
    Link(rel="manifest", href="/assets/manifest.webmanifest"),
    Link(rel="apple-touch-icon", href="/assets/icon-192.png"),
    Link(rel="stylesheet", href="/assets/admin.css?v=20260427d"),
    Script(src="/assets/admin.js?v=20260426a", defer=True),
]

setup_routes(app)

if __name__ == "__main__":
    serve(port=settings.port)
