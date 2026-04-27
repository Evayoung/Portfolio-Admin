"""Settings workspace for Neo Admin."""

from __future__ import annotations

from fasthtml.common import Div, Form, H2, H3, Input, Label, P, Span, Strong, Textarea
from faststrap import Badge, Card, Col, Row, SEO

from app.config import settings
from app.infrastructure.auth_repository import get_admin_access_profile
from app.infrastructure.settings_repository import get_site_profile
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.pages.dashboard import SectionWrap
from app.presentation.shell import page_frame


def settings_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    tone_cls = {
        "success": "alert alert-success",
        "warning": "alert alert-warning",
        "danger": "alert alert-danger",
        "info": "alert alert-info",
    }.get(tone, "alert alert-info")
    return Div(H3(title, cls="h6 mb-2"), P(message, cls="mb-0"), cls=tone_cls)


def _summary_card(label: str, value: str, note: str) -> Col:
    return Col(
        Card(
            Div(
                Span(label, cls="admin-metric-label"),
                H3(value, cls="admin-metric-value"),
                P(note, cls="admin-module-copy mb-0"),
                cls="admin-metric-card-body",
            ),
            cls="admin-surface-card h-100",
        ),
        span=12,
        md=4,
    )


def _field(label: str, name: str, value: str = "", *, input_type: str = "text", placeholder: str = "", required: bool = False) -> Div:
    return Div(
        Label(label, fr=name, cls="admin-form-label"),
        Input(
            type=input_type,
            id=name,
            name=name,
            value=value,
            placeholder=placeholder,
            required=required,
            cls="form-control admin-form-control",
        ),
        cls="admin-form-group",
    )


def _textarea_field(label: str, name: str, value: str = "", *, rows: int = 5, placeholder: str = "", required: bool = False) -> Div:
    return Div(
        Label(label, fr=name, cls="admin-form-label"),
        Textarea(
            value,
            id=name,
            name=name,
            rows=rows,
            placeholder=placeholder,
            required=required,
            cls="form-control admin-form-control admin-form-textarea",
        ),
        cls="admin-form-group",
    )


def settings_workspace_page() -> tuple:
    profile = get_site_profile()
    access = get_admin_access_profile()
    identity_panel = Card(
        Div(
            Div(
                Span("Public identity", cls="admin-kicker"),
                H2(profile.full_name, cls="admin-section-title mb-2"),
                P("This workspace manages the profile and metadata the public portfolio uses for branding, contact details, and SEO defaults.", cls="admin-module-copy mb-0"),
                cls="admin-detail-copy",
            ),
            Div(
                Badge(profile.source.title(), cls="text-bg-secondary admin-metric-delta"),
                Badge("Write enabled" if service_role_is_configured() else "Read-only for now", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            Div(
                Row(
                    Col(
                        Div(
                            H3("Current Profile", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Display Name", cls="admin-field-label"), Strong(profile.full_name)),
                                Div(Span("Role", cls="admin-field-label"), Strong(profile.role)),
                                Div(Span("Site Label", cls="admin-field-label"), Strong(profile.site_name)),
                                Div(Span("Site URL", cls="admin-field-label"), Strong(profile.site_url)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                    ),
                    Col(
                        Div(
                            H3("Contact & SEO", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Email", cls="admin-field-label"), Strong(profile.email)),
                                Div(Span("Phone", cls="admin-field-label"), Strong(profile.phone)),
                                Div(Span("Location", cls="admin-field-label"), Strong(profile.location)),
                                Div(Span("SEO Title", cls="admin-field-label"), Strong(profile.seo_title)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                        cls="mt-4 mt-md-0",
                    ),
                    cls="g-4 mt-1",
                ),
                cls="mt-4",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    form = Form(
        Row(
            Col(_field("Full Name", "full_name", profile.full_name, placeholder="Olorundare Micheal Babawale", required=True), span=12, md=7),
            Col(_field("Role", "role", profile.role, placeholder="Full-Stack & AI Systems Architect", required=True), span=12, md=5, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Row(
            Col(_field("Site Label", "site_name", profile.site_name, placeholder="Micheal Olorundare Portfolio", required=True), span=12, md=6),
            Col(_field("Site URL", "site_url", profile.site_url, input_type="url", placeholder="https://your-domain.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(_field("Email", "email", profile.email, input_type="email", placeholder="name@example.com"), span=12, md=6),
            Col(_field("Phone", "phone", profile.phone, placeholder="+234..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(_field("WhatsApp", "whatsapp", profile.whatsapp, placeholder="+234..."), span=12, md=6),
            Col(_field("Location", "location", profile.location, placeholder="Ilorin, Nigeria"), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(_field("GitHub URL", "github", profile.github, input_type="url", placeholder="https://github.com/..."), span=12, md=6),
            Col(_field("LinkedIn URL", "linkedin", profile.linkedin, input_type="url", placeholder="https://linkedin.com/in/..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        _textarea_field("SEO Title", "seo_title", profile.seo_title, rows=2, required=True, placeholder="Portfolio SEO title"),
        _textarea_field("SEO Description", "seo_description", profile.seo_description, rows=5, required=True, placeholder="Default meta description"),
        Div(
            Input(type="submit", value="Save Settings", cls="btn admin-module-btn"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="settings-save-result", cls="mt-3"),
        action="/settings/save",
        method="post",
        hx_post="/settings/save",
        hx_target="#settings-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )

    editor_panel = Card(
        Div(
            H3("Settings Editor", cls="admin-subsection-title"),
            P("The site label powers the public short-name brand, while the profile and contact fields sync into the public portfolio and CV surfaces.", cls="admin-module-copy"),
            form,
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    access_form = Form(
        _field("Login Email", "login_email", access.login_email, input_type="email", placeholder="admin@neoportfolio.dev", required=True),
        _field("New Password", "password", "", input_type="password", placeholder="Leave blank to keep the current password"),
        _field("Confirm Password", "confirm_password", "", input_type="password", placeholder="Repeat the new password"),
        Div(
            Input(type="submit", value="Save Admin Access", cls="btn admin-module-btn"),
            Span(
                "Credentials are hashed before storage" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="access-save-result", cls="mt-3"),
        action="/settings/access",
        method="post",
        hx_post="/settings/access",
        hx_target="#access-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )

    access_panel = Card(
        Div(
            H3("Admin Access", cls="admin-subsection-title"),
            P("Seeded credentials get you in the first time. After that, you can rotate the login email and password here without touching code.", cls="admin-module-copy"),
            Div(
                Div(Span("Current Login", cls="admin-field-label"), Strong(access.login_email)),
                Div(Span("Credential Source", cls="admin-field-label"), Strong(access.source.title())),
                cls="admin-field-grid admin-detail-block mb-4",
            ),
            access_form,
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Settings",
            description="Settings workspace for managing public identity, profile links, and SEO defaults.",
            url=f"{settings.base_url}/settings",
        ),
        *page_frame(
            Row(
                _summary_card("Profile Source", profile.source.title(), "Where the current public identity data is being loaded from."),
                _summary_card("Brand Label", profile.site_name.replace(" Portfolio", ""), "This drives the public short-name brand treatment."),
                _summary_card("Public URL", profile.site_url.replace("https://", ""), "Primary domain used in SEO and public links."),
                cls="g-4",
            ),
            SectionWrap(
                "Settings Workspace",
                Row(
                    Col(identity_panel, span=12, lg=5),
                    Col(
                        Div(editor_panel, access_panel, cls="admin-settings-stack"),
                        span=12,
                        lg=7,
                        cls="mt-4 mt-lg-0",
                    ),
                    cls="g-4",
                ),
            ),
            current="/settings",
            title="Settings",
        ),
    )
