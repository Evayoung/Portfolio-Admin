"""FastHTML app shell for Neo Admin."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fasthtml.common import Beforeware, FastHTML, Link, Redirect, Script, serve
from faststrap import add_bootstrap, add_pwa, mount_assets

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
        skip=[
            r"/login",
            r"/logout",
            r"/assets/.*",
            r"/favicon.ico",
            r"/manifest\.json",
            r"/sw\.js",
            r"/offline",
            r"/documents/.*",
        ],
    )
)

add_bootstrap(app, theme=NEO_ADMIN_THEME, mode="dark", use_cdn=settings.use_cdn)
add_pwa(
    app,
    name="Neo Admin",
    short_name="NeoAdmin",
    description="Installable publishing dashboard for portfolio content, inbox management, and settings control.",
    theme_color="#091321",
    background_color="#091321",
    icon_path="/assets/icon-512.png",
    cache_name="neo-admin-shell",
    cache_version="v3",
    pre_cache_urls=[
        "/assets/admin.css?v=20260427f",
        "/assets/admin.js?v=20260427c",
        "/assets/icon-192.png",
        "/assets/icon-512.png",
    ],
    route_cache_policies={
        "/assets/": "stale-while-revalidate",
    },
)
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
    Link(rel="stylesheet", href="/assets/admin.css?v=20260427f"),
    Script(src="/assets/admin.js?v=20260427c", defer=True),
]

setup_routes(app)

if __name__ == "__main__":
    serve(port=settings.port)
