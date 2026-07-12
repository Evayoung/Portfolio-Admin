"""Pipeline list page for deals, proposals, quotes, and invoices."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong, Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr
from faststrap import Badge, Card, Col, EmptyState, Modal, Row, SEO

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import (
    get_deal_workspace_summary,
    list_deals,
)
from app.infrastructure.payment_account_repository import list_payment_accounts
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, floating_field, loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def deal_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(
        label,
        Span(cls="admin-filter-loading-spinner"),
        href=href,
        hx_get=href,
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        cls=f"admin-filter-chip{' active' if active else ''}",
    )


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


def _deal_card(item: AdminDeal) -> Card:
    """Render a deal card for the pipeline list grid with HTMX loading."""
    docs = item.documents
    doc_count = len(docs)
    latest = item.latest_document
    latest_status = latest.status.replace("_", " ").title() if latest else "No docs"

    # Document kind badges
    doc_badges = []
    seen_kinds = set()
    for doc in docs:
        if doc.kind not in seen_kinds:
            seen_kinds.add(doc.kind)
            color = _document_kind_color(doc.kind)
            doc_badges.append(
                Badge(
                    Span(
                        doc.kind.title(),
                        cls=f"badge bg-{color} bg-opacity-10 text-{color}",
                    ),
                )
            )

    card_content = Div(
        Div(
            Span(item.stage.replace("_", " ").title(), cls="admin-project-category"),
            Badge(latest_status, cls=f"bg-{_status_color(latest.status) if latest else 'secondary'} bg-opacity-10 text-{_status_color(latest.status) if latest else 'secondary'}"),
            cls="d-flex align-items-center gap-2 flex-wrap",
        ),
        Span(_money(item.amount_ngn), cls="admin-project-meta"),
        H3(item.project_title, cls="admin-project-title"),
        P(item.summary[:120] + ("..." if len(item.summary) > 120 else ""), cls="admin-project-copy"),
        Div(
            Span(item.client_name, cls="admin-project-meta"),
            *doc_badges,
            cls="d-flex align-items-center flex-wrap gap-2 mt-3",
        ),
        cls="admin-project-card-body",
    )

    return Card(
        A(
            card_content,
            Span(cls="admin-card-loading-spinner"),
            href=f"/deals/{item.deal_id}",
            hx_get=f"/deals/{item.deal_id}",
            hx_target="body",
            hx_swap="innerHTML",
            hx_push_url="true",
            hx_indicator=f"#deal-card-{item.deal_id}",
            cls="deal-card-link",
        ),
        id=f"deal-card-{item.deal_id}",
        cls="admin-surface-card admin-project-card deal-card",
    )


def _quick_document_form() -> Form:
    """Quick document creation form for standalone invoices/quotes."""
    accounts = list_payment_accounts()
    return Form(
        Div(
            P("Client", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Client Name", "client_name", "", placeholder="Client or contact name", required=True), span=12, md=6),
                Col(floating_field("Client Email", "client_email", "", input_type="email", placeholder="client@example.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Row(
                Col(floating_field("Client Phone", "client_phone", "", placeholder="+234..."), span=12, md=6),
                Col(floating_field("Company", "company", "", placeholder="Optional company"), span=12, md=6, cls="mt-3 mt-md-0"),
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
            floating_field("Project / Work Title", "project_title", "", placeholder="Logo cleanup, landing page, consultation", required=True),
            floating_field("Document Title", "document_title", "", placeholder="Invoice for consultation", required=True),
            textarea_field("Short Summary", "summary", "", rows=3, placeholder="Short context for the work, payment, or approval request."),
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
        Div(id="quick-document-result", cls="mt-3"),
        action="/deals/quick",
        method="post",
        hx_post="/deals/quick",
        hx_target="#quick-document-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )


def deals_workspace_page(*, stage: str = "all", document_kind: str = "all", search: str = "") -> tuple:
    """Pipeline list page — clean, minimal, focused on the deal cards."""
    all_items = list_deals()
    items = all_items
    if stage != "all" or document_kind != "all" or search:
        items = list_deals(stage=stage, document_kind=document_kind, search=search)
    summary = get_deal_workspace_summary()

    # Pipeline stage strip with counts
    stage_counts = {s: sum(1 for i in all_items if i.stage == s) for s, _ in _stage_options()}
    pipeline_strip = Div(
        *[
            A(
                Span(str(stage_counts.get(s, 0)), cls="admin-pipeline-count"),
                Span(label, cls="admin-pipeline-label"),
                href=f"/deals?stage={s}&document_kind={document_kind}&search={search}",
                cls=f"admin-pipeline-stage{' active' if stage == s else ''}",
            )
            for s, label in _stage_options()
        ],
        cls="admin-pipeline-strip",
    )

    # Filter chips
    stage_links = Div(
        _filter_link("All Stages", f"/deals?stage=all&document_kind={document_kind}&search={search}", active=stage == "all"),
        _filter_link("Lead", f"/deals?stage=lead&document_kind={document_kind}&search={search}", active=stage == "lead"),
        _filter_link("Proposal", f"/deals?stage=proposal&document_kind={document_kind}&search={search}", active=stage == "proposal"),
        _filter_link("Quoted", f"/deals?stage=quoted&document_kind={document_kind}&search={search}", active=stage == "quoted"),
        _filter_link("Invoiced", f"/deals?stage=invoiced&document_kind={document_kind}&search={search}", active=stage == "invoiced"),
        cls="admin-filter-row",
    )
    document_links = Div(
        _filter_link("All Docs", f"/deals?stage={stage}&document_kind=all&search={search}", active=document_kind == "all"),
        _filter_link("Proposals", f"/deals?stage={stage}&document_kind=proposal&search={search}", active=document_kind == "proposal"),
        _filter_link("Quotes", f"/deals?stage={stage}&document_kind=quote&search={search}", active=document_kind == "quote"),
        _filter_link("Invoices", f"/deals?stage={stage}&document_kind=invoice&search={search}", active=document_kind == "invoice"),
        cls="admin-filter-row mt-3",
    )
    search_form = search_filter_bar(
        endpoint="/deals",
        placeholder="Search client, company, project, or summary",
        search_value=search,
        hidden_fields={"stage": stage, "document_kind": document_kind},
        form_cls="admin-search-form admin-filter-bar mt-3",
        hx_target="body",
        hx_swap="innerHTML",
        push_url=True,
    )

    # Deal cards in responsive grid
    deal_grid = Div(
        *[_deal_card(item) for item in items],
        cls="row g-4 admin-deal-grid",
    ) if items else EmptyState(
        icon="briefcase",
        title="No deals match this view",
        description="Try a different pipeline stage or create a new deal from the editor.",
        cls="py-5",
    )

    # Quick document modal
    quick_doc_modal = Modal(
        Div(
            Div(
                H3("Quick Document", cls="modal-title fs-5"),
                Button(type="button", cls="btn-close", data_bs_dismiss="modal", aria_label="Close"),
                cls="modal-header",
            ),
            Div(
                _quick_document_form(),
                cls="modal-body",
            ),
            cls="modal-dialog modal-lg",
        ),
        id="quickDocModal",
        tabindex="-1",
        aria_hidden="true",
    )

    # Main content panel
    list_panel = Card(
        Div(
            Div(
                H2("Pipeline Records", cls="admin-section-title"),
                P("Track every client from lead to payment. Click any deal to view documents, responses, and generate next steps.", cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            pipeline_strip,
            Div(stage_links, document_links, cls="mt-3"),
            search_form,
            Div(
                cls="d-flex justify-content-between align-items-center mt-4 mb-3",
            ),
            deal_grid,
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Deals",
            description="Client pipeline workspace for proposals, quotations, and invoices.",
            url=f"{settings.base_url}/deals",
        ),
        *page_frame(
            Row(
                summary_card("Client Deals", str(summary.total), "Every client record keeps proposal, quote, and invoice context together."),
                summary_card("Proposals", str(summary.proposals), "Early-stage structured scopes ready for review."),
                summary_card("Quotes", str(summary.quotes), "Fixed-scope pricing records with expiry support."),
                summary_card("Invoices", str(summary.invoices), "Payment requests tied back to approved work.", xl=3),
                cls="g-4",
            ),
            SectionWrap(
                "Deals Pipeline",
                Div(
                    list_panel,
                    Div(
                        Button(
                            "Quick Document",
                            type="button",
                            cls="btn admin-install-btn",
                            data_bs_toggle="modal",
                            data_bs_target="#quickDocModal",
                        ),
                            cls="mt-3 text-end",
                        ),
                    cls="",
                ),
            ),
            quick_doc_modal,
            current="/deals",
            title="Deals",
        ),
    )
