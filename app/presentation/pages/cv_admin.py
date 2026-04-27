"""CV workspace for Neo Admin."""

from __future__ import annotations

from fasthtml.common import Div, Form, H2, H3, Input, Label, P, Span, Strong, Textarea
from faststrap import Badge, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.infrastructure.cv_repository import (
    get_cv_meta,
    get_cv_workspace_summary,
    list_certifications,
    list_competencies,
    list_core_skills,
    list_education,
    list_languages,
    list_tool_categories,
    list_work_history,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.pages.dashboard import SectionWrap
from app.presentation.shell import page_frame


def cv_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
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


def _stack_panel(title: str, lines: list[str]) -> Card:
    return Card(
        Div(
            H3(title, cls="admin-subsection-title"),
            Div(*[Div(item, cls="admin-stack-line") for item in lines], cls="admin-stack-list"),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )


def cv_workspace_page() -> tuple:
    meta = get_cv_meta()
    summary = get_cv_workspace_summary()
    work_history = list_work_history()
    education = list_education()
    certifications = list_certifications()
    tool_categories = list_tool_categories()
    languages = list_languages()
    core_skills = list_core_skills()
    competencies = list_competencies()

    editor_form = Form(
        Row(
            Col(_field("Full Name", "name", meta.name, placeholder="Olorundare Micheal Babawale", required=True), span=12, md=7),
            Col(_field("Role", "role", meta.role, placeholder="Full-Stack & AI Systems Architect", required=True), span=12, md=5, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Row(
            Col(_field("Email", "email", meta.email, input_type="email", placeholder="name@example.com"), span=12, md=6),
            Col(_field("Phone", "phone", meta.phone, placeholder="+234..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(_field("WhatsApp", "whatsapp", meta.whatsapp, placeholder="+234..."), span=12, md=6),
            Col(_field("Location", "location", meta.location, placeholder="Ilorin, Nigeria"), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(_field("GitHub URL", "github", meta.github, placeholder="https://github.com/..."), span=12, md=6),
            Col(_field("LinkedIn URL", "linkedin", meta.linkedin, placeholder="https://linkedin.com/in/..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        _textarea_field("Professional Summary", "summary", meta.summary, rows=7, required=True, placeholder="CV summary"),
        _textarea_field("Core Skills", "core_skills", "\n".join(core_skills), rows=8, placeholder="One skill per line"),
        _textarea_field("Competencies", "competencies", "\n".join(competencies), rows=6, placeholder="One competency per line"),
        Div(
            Input(type="submit", value="Save CV Profile", cls="btn admin-module-btn"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="cv-save-result", cls="mt-3"),
        action="/cv/save",
        method="post",
        hx_post="/cv/save",
        hx_target="#cv-save-result",
        hx_swap="innerHTML",
        cls="admin-cv-form",
    )

    insight_panel = Card(
        Div(
            Div(
                Span("Current profile", cls="admin-kicker"),
                H2(meta.name, cls="admin-section-title mb-2"),
                P(meta.summary, cls="admin-module-copy mb-0"),
                cls="admin-detail-copy",
            ),
            Div(
                Badge(summary.source, cls="text-bg-secondary admin-metric-delta"),
                Badge("Live sync on" if service_role_is_configured() else "Setup needed", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            Div(
                Row(
                    Col(
                        Div(
                            H3("Profile Snapshot", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Role", cls="admin-field-label"), Strong(meta.role)),
                                Div(Span("Email", cls="admin-field-label"), Strong(meta.email)),
                                Div(Span("Phone", cls="admin-field-label"), Strong(meta.phone)),
                                Div(Span("Location", cls="admin-field-label"), Strong(meta.location)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                    ),
                    Col(
                        Div(
                            H3("Profile Links", cls="admin-subsection-title"),
                            Div(
                                Div(Span("GitHub", cls="admin-field-label"), Strong(meta.github)),
                                Div(Span("LinkedIn", cls="admin-field-label"), Strong(meta.linkedin)),
                                Div(Span("WhatsApp", cls="admin-field-label"), Strong(meta.whatsapp)),
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
            Div(
                H3("CV Editor", cls="admin-subsection-title"),
                P("Update the profile, summary, and grouped skill surfaces that power both the interactive CV and the branded download.", cls="admin-module-copy"),
                editor_form,
                cls="admin-detail-block mt-4",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    reference_panels = Row(
        Col(
            _stack_panel(
                "Experience",
                [f"{item.title} | {item.organisation} | {item.period}" for item in work_history],
            ),
            span=12,
            lg=6,
        ),
        Col(
            _stack_panel(
                "Education & Certifications",
                [f"{item.degree} | {item.institution}" for item in education] + [f"{item.name} | {item.issuer}" for item in certifications],
            ),
            span=12,
            lg=6,
            cls="mt-4 mt-lg-0",
        ),
        cls="g-4",
    )
    reference_panels_two = Row(
        Col(
            _stack_panel(
                "Tools & Technologies",
                [f"{item.label}: {', '.join(item.tools[:4])}" for item in tool_categories],
            ),
            span=12,
            lg=6,
        ),
        Col(
            _stack_panel(
                "Languages",
                [f"{label} | {level} | {score}%" for label, level, score in languages],
            ),
            span=12,
            lg=6,
            cls="mt-4 mt-lg-0",
        ),
        cls="g-4 mt-1",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | CV Content",
            description="CV content workspace for managing the structured resume profile and brand-facing details.",
            url=f"{settings.base_url}/cv",
        ),
        *page_frame(
            Row(
                _summary_card("Work Items", str(summary.work_items), "Current experience entries in the structured CV timeline."),
                _summary_card("Certifications", str(summary.certifications), "Current credential entries in the structured CV data."),
                _summary_card("Tool Groups", str(summary.tool_groups), f"Live source: {summary.source}."),
                cls="g-4",
            ),
            SectionWrap(
                "CV Workspace",
                Row(
                    Col(insight_panel, span=12, lg=7),
                    Col(
                        Div(reference_panels, reference_panels_two, cls="admin-cv-side-stack"),
                        span=12,
                        lg=5,
                        cls="mt-4 mt-lg-0",
                    ),
                    cls="g-4",
                ),
            ),
            current="/cv",
            title="CV Content",
        ),
    )
