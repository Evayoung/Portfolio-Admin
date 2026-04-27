"""Shared layout helpers for the Neo Admin UI."""

from __future__ import annotations

from fasthtml.common import A, Aside, Div, Footer, H1, Main, P, Small, Span
from faststrap import BottomNav, BottomNavItem, Container, Drawer, Icon

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
                    A(Icon("phone", cls="me-2"), "Install App", href="#", id="install-app-trigger", cls="btn admin-install-btn w-100"),
                    A(
                        Icon("box-arrow-right", cls="me-2"),
                        "Sign Out",
                        href="/logout",
                        cls="btn admin-install-btn w-100",
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
                        Icon("list"),
                        href="#",
                        data_bs_toggle="offcanvas",
                        data_bs_target="#adminMobileDrawer",
                        cls="admin-mobile-action",
                        aria_label="Open menu",
                    ),
                    A(
                        Icon("download"),
                        href="#",
                        id="install-app-trigger-mobile",
                        cls="admin-mobile-action",
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
            Small("Menu", cls="d-block", style="font-size: 0.75rem; line-height: 1;"),
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
    nav_links = Div(
        *[_nav_link(label, href, icon, current) for label, href, icon in NAV_ITEMS],
        cls="admin-sidebar-links mt-0",
    )
    actions = Div(
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
            id="install-app-trigger-drawer",
            cls="btn admin-install-btn w-100",
        ),
        A(
            Icon("box-arrow-right", cls="me-2"),
            "Sign Out",
            href="/logout",
            cls="btn admin-install-btn w-100",
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


def admin_install_drawer() -> Div:
    return Drawer(
        Div(
            P("On iPhone or iPad, open the browser share menu and choose Add to Home Screen.", cls="admin-module-copy"),
            P("On Android, use the browser menu and choose Install App or Add to Home Screen if the native prompt does not appear automatically.", cls="admin-module-copy mb-0"),
            cls="admin-mobile-drawer-stack",
        ),
        drawer_id="adminInstallDrawer",
        title="Install Neo Admin",
        placement="bottom",
        cls="admin-install-drawer",
        body_cls="admin-mobile-drawer-body",
        dark=True,
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
                                    f"{chr(169)} 2026 {settings.owner_name}.",
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
        admin_mobile_drawer(current),
        admin_install_drawer(),
    )
