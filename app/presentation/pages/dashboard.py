"""Dashboard page helpers for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Div, H2, H3, P, Span
from faststrap import Badge, Card, Col, Container, EmptyState, Icon, Row, SEO

from app.config import settings
from app.infrastructure.seed_data import ACTIVITY, METRICS, MODULES
from app.presentation.shell import page_frame


def _metric_card(item) -> Col:
    return Col(
        Card(
            Div(
                Span(item.label, cls="admin-metric-label"),
                H3(item.value, cls="admin-metric-value"),
                Badge(item.delta, cls=f"admin-metric-delta text-bg-{item.tone}"),
                cls="admin-metric-card-body",
            ),
            cls="admin-surface-card h-100",
        ),
        span=12,
        md=6,
        xl=3,
    )


def _module_card(item) -> Col:
    return Col(
        Card(
            Div(
                Div(
                    Div(Icon(item.icon, cls="admin-module-icon"), cls="admin-module-icon-box"),
                    Span(item.count, cls="admin-module-count"),
                    cls="d-flex justify-content-between align-items-start gap-3",
                ),
                H3(item.title, cls="admin-module-title"),
                P(item.description, cls="admin-module-copy"),
                A("Open Workspace", href=item.href, cls="btn admin-module-btn mt-3"),
                cls="admin-module-card-body",
            ),
            cls="admin-surface-card h-100",
        ),
        span=12,
        md=6,
        xl=4,
    )


def overview_page() -> tuple:
    metrics = Row(*[_metric_card(item) for item in METRICS], cls="g-4")
    modules = Row(*[_module_card(item) for item in MODULES], cls="g-4")
    activity = Card(
        Div(
            H2("Recent Activity", cls="admin-section-title"),
            Div(
                *[
                    Div(
                        Div(
                            Span(item.status, cls="admin-activity-status"),
                            H3(item.title, cls="admin-activity-title"),
                            P(item.detail, cls="admin-activity-copy"),
                            cls="admin-activity-body",
                        ),
                        cls="admin-activity-item",
                    )
                    for item in ACTIVITY
                ],
                cls="admin-activity-list",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card",
    )
    next_steps = Card(
        Div(
            H2("System Highlights", cls="admin-section-title"),
            Div(
                *[
                    Div(
                        Span(f"0{idx}", cls="admin-step-index"),
                        Div(
                            H3(title, cls="admin-step-title"),
                            P(copy, cls="admin-step-copy"),
                            cls="admin-step-text",
                        ),
                        cls="admin-step-row",
                    )
                    for idx, (title, copy) in enumerate(
                        (
                            ("Live content control", "Projects, blog, CV, submissions, and settings all share the same production-ready workflow."),
                            ("Inbox visibility", "Contact and booking requests flow from the public site straight into the admin dashboard."),
                            ("Public sync", "The portfolio reads managed content from Supabase while keeping local fallbacks for resilience."),
                            ("Mobile-first shell", "The installable admin experience stays fast and usable across desktop, tablet, and phone."),
                            ),
                        start=1,
                    )
                ],
                cls="admin-step-list",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )
    return (
        *SEO(
            title=f"{settings.app_name} | Overview",
            description="Admin dashboard shell for managing NeoPortfolio content and submissions.",
            url=settings.base_url,
        ),
        *page_frame(
            metrics,
            SectionWrap("Content Modules", modules),
            Row(
                Col(activity, span=12, lg=7),
                Col(next_steps, span=12, lg=5, cls="mt-4 mt-lg-0"),
                cls="g-4 mt-1",
            ),
            current="/",
            title="Overview",
        ),
    )


def SectionWrap(title: str, content):
    return Div(
        H2(title, cls="admin-section-title"),
        content,
        cls="admin-section-block",
    )
