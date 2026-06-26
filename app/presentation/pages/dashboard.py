"""Dashboard page helpers for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Div, H2, H3, P, Span, Strong
from faststrap import Card, Col, Icon, MetricCard, Row, SEO
from faststrap.presets import AutoRefresh, LazyLoad

from app.config import settings
from app.infrastructure.blog_repository import get_blog_workspace_summary
from app.infrastructure.cv_repository import get_cv_workspace_summary
from app.infrastructure.deal_repository import get_deal_workspace_summary
from app.infrastructure.project_repository import get_project_workspace_summary
from app.infrastructure.seed_data import METRICS, MODULES
from app.infrastructure.submission_repository import get_submission_workspace_summary
from app.presentation.page_helpers import overview_metric_card, SectionWrap
from app.presentation.shell import page_frame


def _module_card(item) -> Col:
    return Col(
        Card(
            Div(
                Div(Icon(item.icon, cls="admin-module-icon"), cls="admin-module-icon-box"),
                Span(item.count, cls="admin-module-count"),
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


def _workspace_status_card(projects, blog, submissions, deals, cv) -> Div:
    """Live at-a-glance counts for every content module."""

    def _stat(label: str, primary: str, note: str) -> Div:
        return Div(
            Div(
                Span(label, cls="admin-field-label"),
                Strong(primary),
            ),
            P(note, cls="admin-project-meta mb-0 mt-1"),
            cls="admin-detail-block",
        )

    return Card(
        Div(
            H2("Workspace Status", cls="admin-section-title"),
            P(
                "Live counts pulled directly from each content module.",
                cls="admin-module-copy",
            ),
            Row(
                Col(
                    _stat("Projects", str(projects.total), f"{projects.featured} featured"),
                    _stat("Blog Posts", str(blog.total), f"{blog.published} published"),
                    _stat("CV Entries", str(cv.work_items), f"{cv.certifications} certifications"),
                    span=12,
                    md=6,
                    cls="admin-cv-side-stack",
                ),
                Col(
                    _stat("Submissions", str(submissions.total), f"{submissions.new_items} open · needs review"),
                    _stat("Active Deals", str(deals.total), f"{deals.proposals} proposals · {deals.invoices} invoices"),
                    span=12,
                    md=6,
                    cls="admin-cv-side-stack mt-4 mt-md-0",
                ),
                cls="g-4 mt-1",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card",
    )


def _metrics_ring() -> Row:
    """Render the metrics row — both full-page and HTMX partial use this."""
    return Row(*[overview_metric_card(item) for item in METRICS], cls="g-4")


def _workspace_status_partial() -> Div:
    """Render just the workspace status card — used by LazyLoad."""
    return Div(
        _workspace_status_card(
            get_project_workspace_summary(),
            get_blog_workspace_summary(),
            get_submission_workspace_summary(),
            get_deal_workspace_summary(),
            get_cv_workspace_summary(),
        ),
        cls="admin-section-block",
    )


def overview_page() -> tuple:
    deal_summary = get_deal_workspace_summary()

    metrics = AutoRefresh(
        endpoint="/dashboard/metrics",
        target="this",
        interval=30000,
        content=_metrics_ring(),
        hx_swap="outerHTML",
    )

    # Pipeline revenue strip — MetricCard row from live deal data
    revenue_strip = Row(
        Col(MetricCard("Active Deals", str(deal_summary.total), cls="admin-surface-card h-100"), span=6, md=3),
        Col(MetricCard("Documents Issued", str(deal_summary.proposals + deal_summary.quotes + deal_summary.invoices), cls="admin-surface-card h-100"), span=6, md=3),
        Col(MetricCard("Proposals", str(deal_summary.proposals), cls="admin-surface-card h-100"), span=6, md=3),
        Col(MetricCard("Invoices", str(deal_summary.invoices), cls="admin-surface-card h-100"), span=6, md=3),
        cls="g-4",
    )

    modules = Row(*[_module_card(item) for item in MODULES], cls="g-4")

    return (
        *SEO(
            title=f"{settings.app_name} | Overview",
            description="Admin dashboard shell for managing NeoPortfolio content and submissions.",
            url=settings.base_url,
        ),
        *page_frame(
            metrics,
            revenue_strip,
            SectionWrap("Content Modules", modules),
            LazyLoad(
                endpoint="/dashboard/workspace-status",
                placeholder=Div(
                    Div(cls="placeholder-glow"),
                    cls="admin-surface-card",
                    style="height:12rem;",
                ),
            ),
            current="/",
            title="Overview",
        ),
    )


