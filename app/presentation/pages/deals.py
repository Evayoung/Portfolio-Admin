"""Client and project document workspace for the admin dashboard."""

from __future__ import annotations

from urllib.parse import urlencode

from fasthtml.common import A, Div, Form, H2, H3, Input, Label, Option, P, Script, Select, Span, Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr
from faststrap import Badge, Button, Card, Col, EmptyState, Icon, Modal, Row, SEO

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import (
    get_deal_workspace_summary,
    list_deals,
)
from app.infrastructure.payment_account_repository import list_payment_accounts
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import floating_field, loading_action_button, search_filter_bar, status_alert, textarea_field, toggle_pill_group
from app.presentation.pages.deal_documents import documents_tab
from app.presentation.shell import page_frame


def deal_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _money(value: int) -> str:
    return f"\u20a6{value:,.0f}"


def _stage_options() -> list[tuple[str, str]]:
    return [
        ("lead", "Lead"),
        ("proposal", "Proposal"),
        ("quoted", "Quoted"),
        ("invoiced", "Invoiced"),
        ("paid", "Paid"),
        ("delivered", "Delivered"),
    ]


def _document_kind_icon(kind: str) -> str:
    return {"proposal": "file-earmark-text", "quote": "receipt", "invoice": "credit-card"}.get(kind, "file-earmark")


def _document_kind_color(kind: str) -> str:
    return {"proposal": "primary", "quote": "info", "invoice": "success"}.get(kind, "secondary")


def _status_color(status: str) -> str:
    return {
        "draft": "secondary",
        "sent": "primary",
        "accepted": "success",
        "paid": "success",
        "rejected": "danger",
        "expired": "warning",
    }.get(status, "secondary")


def _quick_document_form(prefill: dict[str, str] | None = None) -> Form:
    """Quick document creation form for standalone invoices/quotes."""
    accounts = list_payment_accounts()
    values = prefill or {}
    initial_title = values.get("project_title", "")
    initial_summary = values.get("summary", "")
    return Form(
        Div(
            P("Client", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Client Name", "client_name", values.get("client_name", ""), placeholder="Client or contact name", required=True), span=12, md=6),
                Col(floating_field("Client Email", "client_email", values.get("client_email", ""), input_type="email", placeholder="client@example.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Row(
                Col(floating_field("Client Phone", "client_phone", values.get("client_phone", ""), placeholder="+234..."), span=12, md=6),
                Col(floating_field("Company", "company", values.get("company", ""), placeholder="Optional company"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-3",
            ),
            cls="admin-form-section mt-0",
        ),
        Div(
            P("Document", cls="admin-form-section-title"),
            Row(
                Col(
                    Div(
                        Label("Document Type", cls="admin-form-label"),
                        toggle_pill_group("document_kind", [("proposal", "Proposal"), ("quote", "Quote"), ("invoice", "Invoice")], selected_value="invoice"),
                        cls="admin-form-group",
                    ),
                    span=12, md=7,
                ),
                Col(
                    Div(
                        Label("Status", cls="admin-form-label"),
                        Select(
                            *[Option(label, value=value, selected=value == "draft") for value, label in [("draft", "Draft"), ("sent", "Sent")]],
                            name="document_status",
                            cls="form-select admin-form-control",
                        ),
                        cls="admin-form-group",
                    ),
                    span=12, md=5, cls="mt-3 mt-md-0",
                ),
                cls="g-3",
            ),
            floating_field("Project / Work Title", "project_title", initial_title, placeholder="Logo cleanup, landing page, consultation", required=True),
            floating_field("Document Title", "document_title", values.get("document_title", initial_title), placeholder="Invoice for consultation", required=True),
            textarea_field("Short Summary", "summary", initial_summary, rows=3, placeholder="Short context for the work, payment, or approval request."),
            cls="admin-form-section",
        ),
        Div(
            P("Money & Dates", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Amount (\u20a6)", "amount_ngn", "", input_type="number", placeholder="50000"), span=12, md=6),
                Col(floating_field("Deposit %", "deposit_percent", "100", input_type="number", placeholder="100"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            Row(
                Col(floating_field("Valid Until", "valid_until", "", input_type="date"), span=12, md=6),
                Col(floating_field("Due Date", "due_date", "", input_type="date"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            textarea_field("Payment Terms", "payment_terms", "", rows=3, placeholder="Bank transfer, due on receipt, or friendly payment note."),
            cls="admin-form-section",
        ),
        Div(
            loading_action_button("Generate Quick Document", endpoint="/deals/quick", target="#quick-document-result"),
            Span(
                "Creates a lightweight record and client link" if service_role_is_configured() else "Add the service-role key to enable generation",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(
            P(
                "Generate a lightweight deal record and client link — the result will appear here.",
                cls="admin-module-copy text-muted mb-0",
            ),
            id="quick-document-result",
            cls="mt-3",
        ),
        action="/deals/quick",
        method="post",
        hx_post="/deals/quick",
        hx_target="#quick-document-result",
        hx_swap="innerHTML",
        cls="admin-settings-form admin-quick-doc",
    )


def deals_workspace_page(
    *,
    stage: str = "all",
    document_kind: str = "all",
    document_status: str = "all",
    search: str = "",
    deal_id: str = "",
    prefill: dict[str, str] | None = None,
    open_quick: bool = False,
) -> tuple:
    all_items = list_deals()
    items = list_deals(stage=stage, document_kind=document_kind, document_status=document_status, search=search)
    selected = next((item for item in items if item.deal_id == deal_id), None)
    if selected is None and items:
        selected = items[0]
    selected_id = selected.deal_id if selected else ""
    summary = get_deal_workspace_summary()

    def deals_href(*, next_stage=stage, next_kind=document_kind, next_status=document_status, next_search=search, next_deal=""):
        return "/deals?" + urlencode({
            "stage": next_stage,
            "document_kind": next_kind,
            "document_status": next_status,
            "search": next_search,
            "deal_id": next_deal,
        })

    stage_counts = {value: sum(1 for item in all_items if item.stage == value) for value, _ in _stage_options()}
    stage_strip = Div(
        *[
            A(
                Span(str(len(all_items)) if value == "all" else str(stage_counts.get(value, 0)), cls="admin-pipeline-count"),
                Span(label, cls="admin-pipeline-label"),
                href=deals_href(next_stage=value),
                hx_get=deals_href(next_stage=value),
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                cls=f"admin-pipeline-stage{' active' if stage == value else ''}",
            )
            for value, label in [("all", "All projects"), *_stage_options()]
        ],
        cls="admin-pipeline-strip",
    )

    kind_options = [("all", "All documents"), ("proposal", "Proposals"), ("quote", "Quotes"), ("invoice", "Invoices")]
    kind_filter = Div(
        *[
            A(
                label,
                href=deals_href(next_kind=value),
                hx_get=deals_href(next_kind=value),
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                cls=f"btn admin-toggle-btn{' active' if document_kind == value else ''}",
            )
            for value, label in kind_options
        ],
        cls="admin-filter-toggle-group",
    )
    status_options = [("all", "Any status"), ("draft", "Draft"), ("sent", "Sent"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("paid", "Paid"), ("expired", "Expired")]
    status_filter = Div(
        *[
            A(
                label,
                href=deals_href(next_status=value),
                hx_get=deals_href(next_status=value),
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                cls=f"admin-filter-chip{' active' if document_status == value else ''}",
            )
            for value, label in status_options
        ],
        cls="admin-filter-row",
    )
    search_form = search_filter_bar(
        endpoint="/deals",
        placeholder="Search client, project, email, or document number",
        search_value=search,
        hidden_fields={
            "stage": stage,
            "document_kind": document_kind,
            "document_status": document_status,
        },
        form_cls="admin-search-form admin-filter-bar mb-3",
        hx_target="body",
        hx_swap="innerHTML",
        push_url=True,
    )

    def workspace_row(item: AdminDeal) -> A:
        latest = item.latest_document
        counts: dict[str, int] = {}
        for document in item.documents:
            counts[document.kind] = counts.get(document.kind, 0) + 1
        doc_chips = [
            Badge(
                f"{kind.title()} x {count}" if count > 1 else kind.title(),
                cls=f"admin-workspace-doc-kind admin-workspace-doc-{_document_kind_color(kind)}",
            )
            for kind, count in sorted(counts.items())
        ]
        href = deals_href(next_deal=item.deal_id)
        return A(
            Div(
                Div(
                    Div(
                        H3(item.project_title, cls="admin-workspace-item-title"),
                        P(item.client_name, cls="admin-workspace-item-client mb-0"),
                        cls="min-w-0",
                    ),
                    Badge(
                        latest.status.replace("_", " ").title() if latest else "No docs",
                        cls=f"admin-workspace-status admin-workspace-status-{_status_color(latest.status) if latest else 'secondary'}",
                    ),
                    cls="d-flex justify-content-between align-items-start gap-2",
                ),
                Div(
                    *doc_chips,
                    Span(f"{len(item.documents)} documents", cls="admin-workspace-item-count"),
                    cls="d-flex flex-wrap align-items-center gap-2 mt-2",
                ),
                Div(
                    Span(item.stage.replace("_", " ").title(), cls="admin-workspace-item-stage"),
                    Span(latest.updated_at if latest and latest.updated_at else "No recent activity", cls="admin-workspace-item-date"),
                    cls="d-flex justify-content-between align-items-center gap-2 mt-2",
                ),
                cls="admin-workspace-item-body",
            ),
            href=href,
            hx_get=href,
            hx_target="body",
            hx_swap="innerHTML",
            hx_push_url="true",
            aria_current="true" if selected_id == item.deal_id else None,
            cls=f"admin-workspace-item{' is-selected' if selected_id == item.deal_id else ''}",
        )

    if selected:
        latest = selected.latest_document
        contact = [
            A(selected.client_email, href=f"mailto:{selected.client_email}", cls="admin-workspace-contact-link") if selected.client_email else "",
            Span(selected.client_phone, cls="admin-workspace-contact") if selected.client_phone else "",
            Span(selected.company, cls="admin-workspace-contact") if selected.company else "",
        ]
        detail_content = Div(
            Div(
                Div(
                    Div(
                        Span("CLIENT / PROJECT", cls="admin-kicker"),
                        H2(selected.project_title, cls="admin-section-title mb-1"),
                        Div(Span(selected.client_name, cls="admin-workspace-client-name"), *[item for item in contact if item], cls="d-flex flex-wrap align-items-center gap-2"),
                    ),
                    Div(
                        Badge(selected.stage.replace("_", " ").title(), cls="admin-workspace-status admin-workspace-status-info"),
                        Badge(
                            latest.status.replace("_", " ").title() if latest else "No documents",
                            cls=f"admin-workspace-status admin-workspace-status-{_status_color(latest.status) if latest else 'secondary'}",
                        ),
                        cls="d-flex flex-wrap gap-2",
                    ),
                    cls="d-flex flex-column flex-xl-row justify-content-between align-items-start gap-3",
                ),
                P(selected.summary or "No project summary has been added yet.", cls="admin-module-copy mt-3 mb-0"),
                Div(
                    A(Icon("pencil", cls="me-1"), "Edit project", href=f"/deals/{selected.deal_id}?view=edit", cls="btn admin-muted-btn btn-sm"),
                    A(Icon("box-arrow-up-right", cls="me-1"), "Open full workspace", href=f"/deals/{selected.deal_id}?view=documents", cls="btn admin-module-btn btn-sm"),
                    cls="d-flex flex-wrap gap-2 mt-3",
                ),
                cls="admin-workspace-detail-head",
            ),
            Div(
                Div(
                    H3("Project documents", cls="admin-subsection-title mb-0"),
                    Span(f"{len(selected.documents)} total", cls="admin-workspace-item-count"),
                    cls="d-flex align-items-center justify-content-between gap-2 mb-3",
                ),
                documents_tab(selected, newest_first=True),
                cls="admin-workspace-documents",
            ),
            cls="admin-surface-card admin-workspace-detail h-100",
        )
    else:
        detail_content = Div(
            EmptyState(
                icon="briefcase",
                title="No client projects found",
                description="Adjust a filter or create a quick document to start a client workspace.",
                cls="py-5",
            ),
            cls="admin-surface-card admin-workspace-detail h-100",
        )

    list_panel = Div(
        Div(
            Div(
                H2("Client projects", cls="admin-subsection-title mb-0"),
                Span(f"{len(items)} shown", cls="admin-workspace-item-count"),
                cls="d-flex justify-content-between align-items-center gap-2 mb-2",
            ),
            Div(*[workspace_row(item) for item in items], cls="admin-workspace-list") if items else EmptyState(
                icon="search",
                title="No client projects found",
                description="Adjust a filter or search for another client, project, or document.",
                cls="py-4",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card admin-workspace-list-panel h-100",
    )
    workspace = Row(
        Col(list_panel, span=12, lg=4),
        Col(detail_content, span=12, lg=8),
        cls="g-4 align-items-start",
    )

    quick_doc_modal = Modal(
        _quick_document_form(prefill),
        modal_id="quickDocModal",
        title="Quick Document",
        size="lg",
        centered=True,
    )
    quick_doc_autopen = Script(
        "document.addEventListener('DOMContentLoaded',function(){var m=document.getElementById('quickDocModal');if(m&&window.bootstrap){bootstrap.Modal.getOrCreateInstance(m).show();}});"
    ) if open_quick else ""

    document_total = summary.proposals + summary.quotes + summary.invoices
    return (
        *SEO(
            title=f"{settings.app_name} | Deals",
            description="Client project workspaces for proposals, quotations, invoices, links, and payment responses.",
            url=f"{settings.base_url}/deals",
        ),
        *page_frame(
            Div(
                Div(
                    Div(
                        H2("Client and project documents", cls="admin-section-title mb-1"),
                        P(f"{summary.total} workspaces | {document_total} documents. Search or select a project.", cls="admin-module-copy mb-0"),
                        cls="flex-grow-1 min-w-0",
                    ),
                    Button(
                        Icon("plus-lg"),
                        Span("Quick Document", cls="d-none d-sm-inline ms-1"),
                        type="button",
                        cls="btn admin-module-btn admin-deals-quick-add",
                        aria_label="Create quick document",
                        title="Create quick document",
                        data_bs_toggle="modal",
                        data_bs_target="#quickDocModal",
                    ),
                    cls="d-flex flex-row justify-content-between align-items-start gap-2 mb-2",
                ),
                Div(stage_strip, kind_filter, status_filter, search_form, cls="admin-deals-controls"),
                workspace,
                cls="admin-deals-workspace",
            ),
            quick_doc_modal,
            quick_doc_autopen,
            current="/deals",
            title="Client Projects",
        ),
    )
