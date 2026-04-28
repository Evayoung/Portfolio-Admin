"""Authentication pages for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, Input, P
from faststrap import Card, Col, Container, Row, SEO

from app.config import settings
from app.infrastructure.settings_repository import get_site_profile
from app.presentation.page_helpers import floating_field, status_alert
from app.presentation.shell import admin_logo, brand_name, public_site_url


def login_page(*, next_path: str = "/", message: str = "", tone: str = "info", login_email: str = "") -> tuple:
    profile = get_site_profile()
    display_name = brand_name(profile)
    alert = None
    if message:
        alert = status_alert("Sign-in status", message, tone)

    login_form = Form(
        floating_field(
            "Login Email",
            "login_email",
            login_email,
            input_type="email",
            placeholder="you@example.com",
            required=True,
            autocomplete="username",
        ),
        floating_field(
            "Password",
            "password",
            input_type="password",
            placeholder="Password",
            required=True,
            autocomplete="current-password",
        ),
        Input(type="hidden", name="next_path", value=next_path or "/"),
        alert if alert else "",
        Div(
            Input(type="submit", value="Sign In", cls="btn admin-module-btn w-100"),
            cls="mt-4",
        ),
        method="post",
        action="/login",
        cls="admin-login-form",
    )

    panel = Card(
        Div(
            Div(admin_logo(profile), cls="admin-login-logo"),
            P(display_name, cls="admin-kicker mb-2"),
            H2("Sign In", cls="admin-login-title"),
            P("Please sign in to access the dashboard.", cls="admin-module-copy"),
            login_form,
            Div(
                A("View Public Site", href=public_site_url(profile), target="_blank", rel="noreferrer", cls="btn admin-install-btn w-100 mt-3"),
                cls="admin-login-actions",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Sign In",
            description="Sign in to the Neo Admin publishing dashboard.",
            url=f"{settings.base_url}/login",
        ),
        Container(
            Row(
                Col(panel, span=12, md=8, lg=5),
                cls="justify-content-center py-5 min-vh-100 align-items-center",
            ),
            cls="admin-login-shell",
        ),
    )
