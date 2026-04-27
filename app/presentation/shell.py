"""Shared layout helpers for the Neo Admin UI."""

from __future__ import annotations

from fasthtml.common import A, Aside, Div, Footer, H1, Main, P, Span
from faststrap import Container, Icon

from app.config import settings

NAV_ITEMS = (
    ("Overview", "/", "grid"),
    ("Projects", "/projects", "kanban"),
    ("Blog", "/blog", "journal-richtext"),
    ("CV", "/cv", "file-earmark-person"),
    ("Submissions", "/submissions", "inbox"),
    ("Settings", "/settings", "sliders"),
)

BOTTOM_NAV_ITEMS = NAV_ITEMS[:5]


def admin_logo() -> Span:
    return Span(
        Span("N", cls="admin-logo-letter"),
        Span("A", cls="admin-logo-letter admin-logo-letter-alt"),
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


def admin_sidebar(current: str = "/") -> Aside:
    return Aside(
        Div(
            A(
                admin_logo(),
                Div(
                    Span("Neo Admin", cls="admin-brand-title"),
                    Span("Mobile-first control room", cls="admin-brand-subtitle"),
                    cls="admin-brand-text",
                ),
                href="/",
                cls="admin-brand",
            ),
            Div(
                Span("Workspace", cls="admin-sidebar-kicker"),
                Div(
                    *[_nav_link(label, href, icon, current) for label, href, icon in NAV_ITEMS],
                    cls="admin-sidebar-links",
                ),
                cls="admin-sidebar-group",
            ),
            Div(
                P(
                    "Install the dashboard on your phone for quick publishing, inbox review, and CV updates.",
                    cls="admin-sidebar-note",
                ),
                Div(
                    A(
                        Icon("box-arrow-up-right", cls="me-2"),
                        "Public Site",
                        href="https://olorundaremicheal.vercel.app",
                        target="_blank",
                        rel="noreferrer",
                        cls="btn admin-nav-btn w-100",
                    ),
                    A(
                        Icon("phone", cls="me-2"),
                        "Install App",
                        href="#",
                        id="install-app-trigger",
                        cls="btn admin-install-btn w-100 d-none",
                    ),
                    cls="admin-sidebar-actions",
                ),
                cls="admin-sidebar-panel",
            ),
            cls="admin-sidebar-inner",
        ),
        cls="admin-sidebar d-none d-lg-flex",
    )


def admin_mobile_header(current: str = "/", title: str = "Overview") -> Div:
    active_item = next((label for label, href, _ in NAV_ITEMS if href == current), title)
    return Div(
        Container(
            Div(
                A(admin_logo(), href="/", cls="admin-mobile-brand"),
                Div(
                    Span("Neo Admin", cls="admin-mobile-kicker"),
                    Span(active_item, cls="admin-mobile-title"),
                    cls="admin-mobile-text",
                ),
                Div(
                    A(
                        Icon("sliders"),
                        href="/settings",
                        cls="admin-mobile-action",
                        aria_label="Open settings",
                    ),
                    A(
                        Icon("download"),
                        href="#",
                        id="install-app-trigger-mobile",
                        cls="admin-mobile-action d-none",
                        aria_label="Install app",
                    ),
                    cls="admin-mobile-actions",
                ),
                cls="admin-mobile-header-row",
            ),
        ),
        cls="admin-mobile-header d-lg-none",
    )


def admin_bottom_nav(current: str = "/") -> Div:
    return Div(
        Container(
            Div(
                *[_nav_link(label, href, icon, current, compact=True) for label, href, icon in BOTTOM_NAV_ITEMS],
                cls="admin-bottom-nav-inner",
            )
        ),
        cls="admin-bottom-nav d-lg-none",
        id="admin-bottom-nav",
    )


def page_frame(*children, current: str = "/", title: str = "Overview"):
    return (
        admin_mobile_header(current, title),
        Div(
            admin_sidebar(current),
            Main(
                Div(
                    Container(
                        Div(
                            P("Neo Admin", cls="admin-kicker"),
                            H1(title, cls="admin-page-title"),
                            P(
                                f"Control panel for {settings.owner_name}'s portfolio content, submissions, and publishing workflow.",
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
                                P(
                                    f"{chr(169)} 2026 {settings.owner_name}. Mobile-first publishing dashboard for your portfolio.",
                                    cls="admin-footer-copy",
                                ),
                                cls="d-flex justify-content-center text-center",
                            )
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
    )
