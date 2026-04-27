"""Authentication pages for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, Input, Label, P
from faststrap import Card, Col, Container, Row, SEO

from app.config import settings
from app.presentation.shell import admin_logo


def login_page(*, next_path: str = "/", message: str = "", tone: str = "info", login_email: str = "") -> tuple:
    alert = None
    if message:
        tone_cls = {
            "success": "alert alert-success",
            "warning": "alert alert-warning",
            "danger": "alert alert-danger",
            "info": "alert alert-info",
        }.get(tone, "alert alert-info")
        alert = Div(P(message, cls="mb-0"), cls=tone_cls)

    login_form = Form(
        Div(
            Label("Login Email", fr="login_email", cls="admin-form-label"),
            Input(
                type="email",
                id="login_email",
                name="login_email",
                value=login_email,
                required=True,
                autocomplete="username",
                cls="form-control admin-form-control",
            ),
            cls="admin-form-group",
        ),
        Div(
            Label("Password", fr="password", cls="admin-form-label"),
            Input(
                type="password",
                id="password",
                name="password",
                required=True,
                autocomplete="current-password",
                cls="form-control admin-form-control",
            ),
            cls="admin-form-group mt-3",
        ),
        Input(type="hidden", name="next", value=next_path or "/"),
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
            Div(admin_logo(), cls="admin-login-logo"),
            P("Neo Admin", cls="admin-kicker mb-2"),
            H2("Sign In", cls="admin-login-title"),
            P("Protected publishing dashboard for portfolio content, inbox management, and settings control.", cls="admin-module-copy"),
            login_form,
            Div(
                A("View Public Site", href="https://olorundaremicheal.vercel.app", target="_blank", rel="noreferrer", cls="btn admin-install-btn w-100 mt-3"),
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
