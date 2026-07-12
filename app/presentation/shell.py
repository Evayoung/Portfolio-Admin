"""Shared layout helpers for the Neo Admin UI."""

from __future__ import annotations

import secrets as _secrets
import time as _time

from fasthtml.common import A, Aside, Button, Div, Footer, H1, Main, Meta, P, Small, Span
from faststrap import BottomNav, BottomNavItem, Container, Drawer, Icon, SidebarNavbar, SidebarNavItem
from faststrap.components.feedback.modern_toast import ModernToastStack

from app.config import settings
from app.infrastructure.settings_repository import get_site_profile

_page_csrf_tokens: list[str] = []


def _get_csrf_token() -> str:
    """Generate a per-render CSRF token for HTMX header injection.

    The actual session-based validation happens in route handlers.
    This token is embedded in a <meta> tag so admin.js can send it
    as an HTMX header on every request.
    """
    token = _secrets.token_hex(32)
    _page_csrf_tokens.append(token)
    if len(_page_csrf_tokens) > 100:
        _page_csrf_tokens.pop(0)
    return token


NAV_ITEMS = (
    ("Overview", "/", "grid"),
    ("Projects", "/projects", "kanban"),
    ("Blog", "/blog", "journal-richtext"),
    ("CV", "/cv", "file-earmark-person"),
    ("Submissions", "/submissions", "inbox"),
    ("Deals", "/deals", "briefcase"),
    ("AI Assistant", "/ai-assistant", "robot"),
    ("Media", "/media", "images"),
    ("Settings", "/settings", "sliders"),
)

BOTTOM_NAV_ITEMS = (
    ("Overview", "/", "grid"),
    ("Projects", "/projects", "kanban"),
    ("Submissions", "/submissions", "inbox"),
    ("Deals", "/deals", "briefcase"),
    ("Settings", "/settings", "sliders"),
)


# TTL-based cache for profile (replaces stale lru_cache)
_profile_cache: tuple = (None, 0.0)  # (profile, timestamp)
_PROFILE_TTL = 300  # 5 minutes


def brand_profile():
    """Return the site profile, cached for 5 minutes to avoid stale data."""
    global _profile_cache
    profile, ts = _profile_cache
    if profile is None or _time.time() - ts > _PROFILE_TTL:
        profile = get_site_profile()
        _profile_cache = (profile, _time.time())
    return profile


def brand_name(profile) -> str:
    site_name = (getattr(profile, "site_name", "") or "").strip()
    if site_name.endswith(" Portfolio"):
        site_name = site_name[:-10].strip()
    return site_name or settings.owner_name


def profile_name(profile) -> str:
    full_name = (getattr(profile, "full_name", "") or "").strip()
    return full_name or settings.owner_name


def sidebar_brand_title(profile) -> str:
    full_name = profile_name(profile)
    parts = [part for part in full_name.split() if part]
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else brand_name(profile)


def public_site_url(profile) -> str:
    site_url = (getattr(profile, "site_url", "") or "").strip()
    return site_url or "https://olorundaremicheal.vercel.app"


def _brand_initials(profile) -> tuple[str, str]:
    words = [part for part in brand_name(profile).replace("-", " ").split() if part]
    if not words:
        return ("N", "A")
    if len(words) == 1:
        token = words[0][:2].upper()
        return (token[:1], token[1:2] or token[:1])
    return (words[0][:1].upper(), words[1][:1].upper())


def admin_logo(profile=None) -> Span:
    profile = profile or brand_profile()
    first_letter, second_letter = _brand_initials(profile)
    return Span(
        Span(first_letter, cls="admin-logo-letter"),
        Span(second_letter, cls="admin-logo-letter admin-logo-letter-alt"),
        cls="admin-logo",
    )


def _nav_link(label: str, href: str, icon: str, current: str, *, compact: bool = False) -> A:
    base_cls = "admin-nav-link"
    if compact:
        base_cls = "admin-bottom-link"
    if href == current:
        base_cls += " active"
    return A(
        Icon(icon, cls="admin-nav-icon"),
        Span(label, cls="admin-nav-label"),
        href=href,
        cls=base_cls,
        aria_label=label,
    )


def admin_sidebar(current: str = "/", profile=None) -> Aside:
    profile = profile or brand_profile()
    sidebar_nav = SidebarNavbar(
        *[
            SidebarNavItem(
                label,
                href=href,
                icon=icon,
                active=href == current,
                theme="dark",
                cls="admin-nav-link",
            )
            for label, href, icon in NAV_ITEMS
        ],
        theme="dark",
        sticky=False,
        collapsible=False,
        width="100%",
        cls="admin-sidebar-nav",
    )
    return Aside(
        Div(
            A(
                admin_logo(profile),
                Div(
                    Span(sidebar_brand_title(profile), cls="admin-brand-title"),
                    Span("Portfolio Admin", cls="admin-brand-subtitle"),
                    cls="admin-brand-text",
                ),
                href="/",
                cls="admin-brand",
            ),
            Div(
                Span("Workspace", cls="admin-sidebar-kicker"),
                sidebar_nav,
                cls="admin-sidebar-group",
            ),
            Div(
                Div(
                    A(
                        Icon("box-arrow-up-right", cls="me-2"),
                        "Public Site",
                        href=public_site_url(profile),
                        target="_blank",
                        rel="noreferrer",
                        cls="btn admin-nav-btn w-100",
                    ),
                    A(Icon("phone", cls="me-2"), "Install App", href="#", id="install-app-trigger", cls="btn admin-install-btn w-100"),
                    A(
                        Icon("box-arrow-right", cls="me-2"),
                        "Sign Out",
                        href="/logout",
                        cls="btn admin-install-btn w-100",
                        onclick="return confirm('Sign out of Neo Admin?')",
                    ),
                    cls="admin-sidebar-actions",
                ),
                cls="admin-sidebar-panel",
            ),
            cls="admin-sidebar-inner",
        ),
        cls="admin-sidebar d-none d-lg-flex",
    )


def admin_mobile_header(current: str = "/", title: str = "Overview", profile=None) -> Div:
    profile = profile or brand_profile()
    active_item = next((label for label, href, _ in NAV_ITEMS if href == current), title)
    return Div(
        Container(
            Div(
                A(admin_logo(profile), href="/", cls="admin-mobile-brand"),
                Div(
                    Span(active_item, cls="admin-mobile-title"),
                    cls="admin-mobile-text",
                ),
                A(
                    Icon("download"),
                    href="#",
                    id="install-app-trigger-mobile",
                    cls="admin-mobile-action",
                    aria_label="Install app",
                ),
                cls="admin-mobile-header-row",
            ),
        ),
        cls="admin-mobile-header d-lg-none",
    )


def admin_bottom_nav(current: str = "/") -> Div:
    main_items = BOTTOM_NAV_ITEMS[:4]
    return BottomNav(
        *[
            BottomNavItem(
                label,
                href=href,
                icon=icon,
                active=href == current,
                cls="admin-bottom-link",
            )
            for label, href, icon in main_items
        ],
        A(
            Icon("list", size="1.25em", cls="mb-1"),
            Small("Menu", cls="d-block admin-bottom-small"),
            href="#",
            data_bs_toggle="offcanvas",
            data_bs_target="#adminMobileDrawer",
            aria_label="Open menu",
            cls="nav-link d-flex flex-column align-items-center justify-content-center w-100 flex-grow-1 py-2 admin-bottom-link",
        ),
        variant="dark",
        cls="admin-bottom-nav d-lg-none",
        id="admin-bottom-nav",
    )


def admin_mobile_drawer(current: str = "/") -> Div:
    profile = brand_profile()
    nav_links = Div(
        *[_nav_link(label, href, icon, current) for label, href, icon in NAV_ITEMS],
        cls="admin-sidebar-links mt-0",
    )
    actions = Div(
        A(
            Icon("box-arrow-up-right", cls="me-2"),
            "Public Site",
            href=public_site_url(profile),
            target="_blank",
            rel="noreferrer",
            cls="btn admin-nav-btn w-100",
        ),
        A(
            Icon("phone", cls="me-2"),
            "Install App",
            href="#",
            id="install-app-trigger-drawer",
            cls="btn admin-install-btn w-100",
        ),
        A(
            Icon("box-arrow-right", cls="me-2"),
            "Sign Out",
            href="/logout",
            cls="btn admin-install-btn w-100",
            onclick="return confirm('Sign out of Neo Admin?')",
        ),
        cls="admin-sidebar-actions mt-4",
    )
    return Drawer(
        Div(
            P("Workspace", cls="admin-sidebar-kicker mb-3"),
            nav_links,
            actions,
            cls="admin-mobile-drawer-stack",
        ),
        drawer_id="adminMobileDrawer",
        title="Menu",
        placement="start",
        cls="admin-mobile-drawer d-lg-none",
        body_cls="admin-mobile-drawer-body",
        dark=True,
    )


def admin_install_drawer(profile=None) -> Div:
    profile = profile or brand_profile()
    return Drawer(
        Div(
            P("On iPhone or iPad, open the browser share menu and choose Add to Home Screen.", cls="admin-module-copy"),
            P("On Android, use the browser menu and choose Install App or Add to Home Screen if the native prompt does not appear automatically.", cls="admin-module-copy mb-0"),
            cls="admin-mobile-drawer-stack",
        ),
        drawer_id="adminInstallDrawer",
        title=f"Install {brand_name(profile)} Admin",
        placement="bottom",
        cls="admin-install-drawer",
        body_cls="admin-mobile-drawer-body",
        dark=True,
    )


def admin_shortcuts_modal() -> Div:
    """Keyboard shortcuts help modal — triggered by pressing '?'."""
    shortcuts = [
        ("?", "Show keyboard shortcuts"),
        ("g + d", "Go to Deals"),
        ("g + s", "Go to Submissions"),
        ("g + p", "Go to Projects"),
        ("g + b", "Go to Blog"),
        ("g + m", "Go to Media"),
    ]
    rows = Div(
        *[
            Div(
                Span(keys, cls="badge bg-secondary me-2", style="font-family:monospace;min-width:4rem;text-align:center;display:inline-block;"),
                Span(desc),
                cls="d-flex align-items-center gap-2 py-1",
            )
            for keys, desc in shortcuts
        ],
        cls="mt-3",
    )
    return Div(
        Div(
            Div(
                Div(
                    H1("Keyboard Shortcuts", cls="modal-title fs-5"),
                    Button(type="button", cls="btn-close", data_bs_dismiss="modal", aria_label="Close"),
                    cls="modal-header",
                ),
                Div(rows, cls="modal-body"),
                Div(
                    Button("Close", type="button", cls="btn admin-module-btn", data_bs_dismiss="modal"),
                    cls="modal-footer",
                ),
                cls="modal-content",
            ),
            cls="modal-dialog modal-dialog-centered",
        ),
        cls="modal fade",
        id="admin-shortcuts-modal",
        tabindex="-1",
        aria_hidden="true",
    )


def page_frame(*children, current: str = "/", title: str = "Overview"):
    profile = brand_profile()
    # Session expiry meta tag for client-side warning
    session_expires = int(_time.time()) + (8 * 3600)  # 8-hour rolling window
    return (
        Meta(name="session-expires-at", content=str(session_expires)),
        admin_mobile_header(current, title, profile),
        Div(
            admin_sidebar(current, profile),
            Main(
                Div(
                    Container(
                        Div(
                            P(brand_name(profile), cls="admin-kicker"),
                            H1(title, cls="admin-page-title"),
                            Div(cls="admin-page-header-divider"),
                            P(
                                f"Control panel for {brand_name(profile)}'s portfolio content, submissions, and publishing workflow.",
                                cls="admin-page-copy",
                            ),
                            cls="admin-page-header",
                        ),
                        *children,
                        cls="admin-shell",
                    ),
                    Footer(
                        Container(
                            Div(
                                Span(f"© 2026 {profile_name(profile)}", cls="admin-footer-link"),
                                Span("·", cls="admin-footer-sep"),
                                A("Public Site", href=public_site_url(profile), target="_blank", rel="noreferrer", cls="admin-footer-link"),
                                Span("·", cls="admin-footer-sep"),
                                A("Sign Out", href="/logout", cls="admin-footer-link", onclick="return confirm('Sign out of Neo Admin?')"),
                                cls="admin-footer-inner",
                            ),
                        ),
                        cls="admin-footer",
                    ),
                    cls="admin-content-wrap",
                ),
                cls="admin-app",
            ),
            cls="admin-layout",
        ),
        admin_bottom_nav(current),
        admin_mobile_drawer(current),
        admin_install_drawer(profile),
        admin_shortcuts_modal(),
        ModernToastStack(position="top-end", gap=2, id="toast-container"),
        # Global HTMX loading bar — shows at the top during any request
        Div(cls="admin-loading-bar", id="admin-loading-bar"),
    )
