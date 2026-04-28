"""Dashboard page helpers for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Div, H2, H3, P, Span, Strong
from faststrap import Card, Col, Icon, Row, SEO

from app.config import settings
from app.infrastructure.github_repository import get_github_stats
from app.infrastructure.seed_data import ACTIVITY, METRICS, MODULES
from app.infrastructure.deal_repository import get_deal_workspace_summary
from app.presentation.page_helpers import overview_metric_card
from app.presentation.shell import page_frame


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
    github = get_github_stats()
    deal_summary = get_deal_workspace_summary()
    metrics = Row(*[overview_metric_card(item) for item in METRICS], cls="g-4")

    # Pipeline revenue strip — derived from live deal data
    revenue_strip = Div(
        Div(
            Span("Active Deals", cls="admin-revenue-label"),
            Div(str(deal_summary.total), cls="admin-revenue-value"),
            cls="admin-revenue-cell",
        ),
        Div(
            Span("Documents Issued", cls="admin-revenue-label"),
            Div(
                str(deal_summary.proposals + deal_summary.quotes + deal_summary.invoices),
                cls="admin-revenue-value",
            ),
            cls="admin-revenue-cell",
        ),
        Div(
            Span("Proposals", cls="admin-revenue-label"),
            Div(str(deal_summary.proposals), cls="admin-revenue-value"),
            cls="admin-revenue-cell",
        ),
        Div(
            Span("Invoices", cls="admin-revenue-label"),
            Div(str(deal_summary.invoices), cls="admin-revenue-value"),
            cls="admin-revenue-cell",
        ),
        cls="admin-revenue-strip",
    )
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
    github_card = Card(
        Div(
            H2("GitHub Pulse", cls="admin-section-title"),
            P(
                "Recent open-source proof pulled from your GitHub profile. This stays graceful even when the API is unavailable.",
                cls="admin-module-copy",
            ),
            Div(
                Div(Span("Profile", cls="admin-field-label"), Strong(github.username)),
                Div(Span("Public Repos", cls="admin-field-label"), Strong(str(github.public_repos))),
                Div(Span("Stars", cls="admin-field-label"), Strong(str(github.stars))),
                Div(Span("Followers", cls="admin-field-label"), Strong(str(github.followers))),
                Div(Span("Recent Commits", cls="admin-field-label"), Strong(str(github.recent_commits))),
                Div(Span("Source", cls="admin-field-label"), Strong(github.source.title())),
                cls="admin-field-grid mt-3",
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
            revenue_strip,
            SectionWrap("Content Modules", modules),
            Row(
                Col(activity, span=12, lg=7),
                Col(next_steps, span=12, lg=5, cls="mt-4 mt-lg-0"),
                cls="g-4 mt-1",
            ),
            Row(
                Col(github_card, span=12),
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
