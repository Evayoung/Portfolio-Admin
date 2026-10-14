"""Deal overview tab with a concise client, project, and document snapshot."""

from __future__ import annotations

from fasthtml.common import A, Div, H3, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Row, SEO, Spinner

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import get_deal_with_documents
from app.presentation.pages.deal_helpers import _money, _status_color, _workflow_pipeline
from app.presentation.shell import page_frame


def _overview_tab(selected: AdminDeal) -> Div:
    """Show the facts needed to orient work, without rendering the full proposal."""
    docs = sorted(selected.documents, key=lambda doc: doc.updated_at, reverse=True)
    recent_docs = docs[:4]

    client_card = Card(
        H3("Client", cls="admin-subsection-title"),
        Div(
            Div(Span("Name", cls="admin-field-label"), Strong(selected.client_name or "Not set")),
            Div(Span("Email", cls="admin-field-label"), Strong(selected.client_email or "Not set")),
            Div(Span("Phone", cls="admin-field-label"), Strong(selected.client_phone or "Not set")),
            Div(Span("Company", cls="admin-field-label"), Strong(selected.company or "Independent")),
            cls="admin-field-grid",
        ),
        cls="admin-detail-block h-100",
    )

    project_card = Card(
        Div(
            H3("Project brief", cls="admin-subsection-title mb-0"),
            A(
                Icon("pencil-square", cls="me-1"),
                "Edit",
                href=f"/deals/{selected.deal_id}?view=edit",
                cls="admin-project-meta",
            ),
            cls="d-flex align-items-center justify-content-between gap-2",
        ),
        P(selected.summary or "No project brief saved yet.", cls="admin-module-copy deal-overview-summary mt-3 mb-3"),
        Div(
            Div(Span("Service", cls="admin-field-label"), Strong(selected.service_type or "Not set")),
            Div(Span("Deposit", cls="admin-field-label"), Strong(f"{selected.deposit_percent}%")),
            cls="admin-field-grid",
        ),
        cls="admin-detail-block h-100",
    )

    document_rows = [
        Div(
            Div(
                Span(doc.kind.title(), cls="admin-field-label"),
                Badge(
                    doc.status.replace("_", " ").title(),
                    cls=f"bg-{_status_color(doc.status)} bg-opacity-10 text-{_status_color(doc.status)}",
                ),
                Span(_money(doc.total_amount), cls="fw-semibold ms-auto"),
                cls="d-flex align-items-center flex-wrap gap-2",
            ),
            Div(doc.title, cls="admin-project-title mt-1"),
            Span(doc.document_number, cls="admin-project-meta") if doc.document_number else "",
            cls="deal-overview-document",
        )
        for doc in recent_docs
    ]

    documents_card = Card(
        Div(
            Div(
                H3("Documents", cls="admin-subsection-title mb-0"),
                Span(f"{len(docs)} total", cls="admin-project-meta"),
                cls="d-flex align-items-center gap-2",
            ),
            A(
                "Open documents",
                Icon("arrow-right", cls="ms-1"),
                href=f"/deals/{selected.deal_id}?view=documents",
                cls="admin-project-meta",
            ),
            cls="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2",
        ),
        Div(*document_rows, cls="deal-overview-document-list") if document_rows else P(
            "No documents have been created for this deal yet.",
            cls="admin-module-copy mb-0",
        ),
        cls="admin-detail-block mt-3",
    )

    return Div(
        Row(
            Col(client_card, span=12, lg=5),
            Col(project_card, span=12, lg=7, cls="mt-3 mt-lg-0"),
            cls="g-3",
        ),
        documents_card,
        cls="deal-overview-workspace",
    )


def deal_overview_page(*, deal_id: str = "", view: str = "overview") -> tuple:
    """Deal overview page layout."""
    selected = get_deal_with_documents(deal_id) if deal_id else None
    if not selected:
        return (
            *SEO(
                title=f"{settings.app_name} | Deal Not Found",
                description="Deal not found.",
                url=f"{settings.base_url}/deals",
            ),
            *page_frame(
                EmptyState(
                    icon="exclamation-circle",
                    title="Deal not found",
                    description="The deal you're looking for doesn't exist or has been deleted.",
                    cls="py-5",
                ),
                current="/deals",
                title="Deal Not Found",
            ),
        )

    def _nav_pill(label: str, target_view: str) -> A:
        pill_href = f"/deals/{deal_id}?view={target_view}"
        return A(
            label,
            href=pill_href,
            hx_get=pill_href,
            hx_target="body",
            hx_swap="innerHTML",
            hx_push_url="true",
            cls=f"admin-filter-chip{' active' if view == target_view else ''}",
        )

    nav_pills = Div(
        _nav_pill("Overview", "overview"),
        _nav_pill("Documents", "documents"),
        _nav_pill("Edit", "edit"),
        cls="d-flex flex-wrap gap-2 mb-4",
    )

    back_link = A(
        Icon("arrow-left", cls="me-2"),
        "Back to Pipeline",
        Spinner(size="sm", cls="admin-back-spinner ms-2"),
        href="/deals",
        hx_get="/deals",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        hx_indicator="#deal-back-link",
        id="deal-back-link",
        cls="admin-back-link mb-3",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | {selected.project_title}",
            description=f"Deal details for {selected.project_title}",
            url=f"{settings.base_url}/deals/{deal_id}",
        ),
        *page_frame(
            back_link,
            Div(
                Div(
                    Span(selected.client_name, cls="admin-project-meta"),
                    Badge(
                        selected.stage.replace("_", " ").title(),
                        cls=f"bg-{_status_color(selected.stage)} bg-opacity-10 text-{_status_color(selected.stage)} ms-2",
                    ),
                    Span(_money(selected.amount_ngn), cls="admin-project-meta ms-2"),
                    cls="d-flex align-items-center gap-2 flex-wrap",
                ),
                _workflow_pipeline(selected),
                cls="deal-detail-header mb-3",
            ),
            nav_pills,
            Div(
                _overview_tab(selected),
                cls=[Fx.base, Fx.fade_in, "deal-overview-page"],
            ),
            current="/deals",
            title=selected.project_title,
        ),
    )
