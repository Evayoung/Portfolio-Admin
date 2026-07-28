"""Pipeline list page for deals, proposals, quotes, and invoices."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong, Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Modal, Row, SEO

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
    """Render a deal card for the pipeline list grid with HTMX loading — matches Blog/Projects pattern."""
    docs = item.documents
    latest = item.latest_document
    latest_status = latest.status.replace("_", " ").title() if latest else "No docs"
    card_id = f"deal-card-{item.deal_id}"
    href = f"/deals/{item.deal_id}"
    preview_modal_id = f"deal-preview-modal-{item.deal_id}"

    # Document kind badges
    doc_badges = []
    seen_kinds = set()
    for doc in docs:
        if doc.kind not in seen_kinds:
            seen_kinds.add(doc.kind)
            color = _document_kind_color(doc.kind)
            doc_badges.append(
                Badge(
                    doc.kind.title(),
                    cls=f"bg-{color} bg-opacity-10 text-{color}",
                )
            )

    card_body = Div(
        Div(
            Span(item.stage.replace("_", " ").title(), cls="admin-project-category"),
            Badge(latest_status, cls=f"bg-{_status_color(latest.status) if latest else 'secondary'} bg-opacity-10 text-{_status_color(latest.status) if latest else 'secondary'}"),
            cls="d-flex align-items-center gap-2 flex-wrap",
        ),
        Span(_money(item.amount_ngn), cls="admin-project-meta"),
        H3(
            item.project_title,
            Span(cls="admin-card-loading-spinner"),
            cls="admin-project-title d-flex justify-content-between align-items-center",
        ),
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
            card_body,
            href=href,
            hx_get=href,
            hx_target="body",
            hx_swap="innerHTML",
            hx_push_url="true",
            hx_indicator=f"#{card_id}",
            cls="admin-project-card-link",
        ),
        # Card quick action bar — mirrors Blog/Projects pattern
        Div(
            Button(
                Icon("eye", cls="me-1"),
                "Quick Preview",
                type="button",
                cls="btn admin-muted-btn btn-sm",
                data_bs_toggle="modal",
                data_bs_target=f"#{preview_modal_id}",
            ),
            A(
                Icon("arrow-right", cls="me-1"),
                "Open Deal",
                href=href,
                hx_get=href,
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                hx_indicator=f"#{card_id}",
                cls="btn admin-icon-btn admin-module-btn btn-sm",
            ),
            cls="d-flex justify-content-between align-items-center pt-3 mt-3 border-top border-secondary border-opacity-10",
        ),
        id=card_id,
        cls=[Fx.base, Fx.fade_in, Fx.hover_lift, "admin-surface-card admin-project-card h-100"],
    )


def _deal_quick_preview_modal(item: AdminDeal) -> Modal:
    """Quick Preview modal for a deal — mirrors Blog/Projects root-level preview pattern."""
    modal_id = f"deal-preview-modal-{item.deal_id}"
    docs = item.documents
    latest = item.latest_document
    doc_counts = {"proposal": 0, "quote": 0, "invoice": 0}
    for doc in docs:
        doc_counts[doc.kind] = doc_counts.get(doc.kind, 0) + 1

    stage_color = _status_color(item.stage)
    latest_color = _status_color(latest.status) if latest else "secondary"

    return Modal(
        Div(
            # Stage + Status header strip
            Div(
                Badge(item.stage.replace("_", " ").title(), cls=f"bg-{stage_color} bg-opacity-10 text-{stage_color} fs-6 me-2"),
                Badge(latest.status.replace("_", " ").title() if latest else "No Docs",
                      cls=f"bg-{latest_color} bg-opacity-10 text-{latest_color} fs-6"),
                cls="d-flex flex-wrap gap-1 mb-3",
            ),
            H2(item.project_title, cls="admin-section-title mb-1 fs-3"),
            P(item.client_name, cls="admin-project-meta mb-3"),
            # Key financials block
            Div(
                Div(
                    Div(Span("Amount", cls="admin-field-label fw-bold"), Strong(_money(item.amount_ngn))),
                    Div(Span("Deposit", cls="admin-field-label fw-bold"), Strong(f"{item.deposit_percent}%")),
                    Div(Span("Service", cls="admin-field-label fw-bold"), Strong(item.service_type or "Not set")),
                    Div(Span("Company", cls="admin-field-label fw-bold"), Strong(item.company or "Independent")),
                    cls="admin-field-grid",
                ),
                cls="admin-detail-block p-3 mb-4",
            ),
            # Document breakdown
            Div(
                Span("Documents", cls="admin-field-label mb-2 d-block fw-bold"),
                Div(
                    Div(Span("Proposals", cls="admin-project-meta"), Strong(str(doc_counts["proposal"])),
                        cls="d-flex justify-content-between"),
                    Div(Span("Quotes", cls="admin-project-meta"), Strong(str(doc_counts["quote"])),
                        cls="d-flex justify-content-between"),
                    Div(Span("Invoices", cls="admin-project-meta"), Strong(str(doc_counts["invoice"])),
                        cls="d-flex justify-content-between"),
                    Div(Span("Total", cls="admin-project-meta fw-bold"), Strong(str(len(docs))),
                        cls="d-flex justify-content-between mt-2 pt-2 border-top border-secondary border-opacity-10"),
                    cls="admin-field-grid",
                ),
                cls="admin-detail-block p-3 mb-4",
            ),
            # Summary excerpt
            Div(
                Span("Project Brief", cls="admin-field-label mb-2 d-block fw-bold"),
                P(item.summary[:400] + ("..." if len(item.summary) > 400 else "") or "No summary provided.",
                  cls="admin-module-copy text-muted fst-italic mb-0"),
                cls="admin-detail-block p-3 mb-3",
            ),
            # Footer CTAs
            Div(
                A(
                    Icon("arrow-right-circle", cls="me-1"),
                    "Open Deal →",
                    href=f"/deals/{item.deal_id}",
                    hx_get=f"/deals/{item.deal_id}",
                    hx_target="body",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    cls="btn admin-module-btn",
                ),
                Button("Close Preview", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
                cls="d-flex justify-content-between align-items-center mt-4 pt-3 border-top border-secondary border-opacity-10",
            ),
        ),
        modal_id=modal_id,
        title=f"Deal Preview: {item.project_title}",
        size="lg",
        scrollable=True,
        centered=True,
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


def deals_workspace_page(*, stage: str = "all", document_kind: str = "all", search: str = "") -> tuple:
    """Pipeline list page — responsive grid, quick preview modals, unified filter bar."""
    all_items = list_deals()
    items = all_items
    if stage != "all" or document_kind != "all" or search:
        items = list_deals(stage=stage, document_kind=document_kind, search=search)
    summary = get_deal_workspace_summary()

    # ── Pipeline stage strip with counts ────────────────────────────────────
    stage_counts = {s: sum(1 for i in all_items if i.stage == s) for s, _ in _stage_options()}
    pipeline_strip = Div(
        *[
            A(
                Span(str(stage_counts.get(s, 0)), cls="admin-pipeline-count"),
                Span(label, cls="admin-pipeline-label"),
                Span(cls="admin-filter-loading-spinner"),
                href=f"/deals?stage={s}&document_kind={document_kind}&search={search}",
                hx_get=f"/deals?stage={s}&document_kind={document_kind}&search={search}",
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                cls=f"admin-pipeline-stage{' active' if stage == s else ''}",
            )
            for s, label in _stage_options()
        ],
        cls="admin-pipeline-strip",
    )

    # ── Document-kind refinement — branded admin-toggle-btn style ───────────
    doc_kind_options = [
        ("all", "All Docs"),
        ("proposal", "Proposals"),
        ("quote", "Quotes"),
        ("invoice", "Invoices"),
    ]
    document_kind_filter = Div(
        *[
            A(
                label,
                Span(cls="admin-filter-loading-spinner"),
                href=f"/deals?stage={stage}&document_kind={dk}&search={search}",
                hx_get=f"/deals?stage={stage}&document_kind={dk}&search={search}",
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                aria_label=f"Filter by {label}",
                cls=f"btn admin-toggle-btn{' active' if document_kind == dk else ''}",
            )
            for dk, label in doc_kind_options
        ],
        cls="admin-filter-toggle-group flex-wrap",
    )

    # ── Search bar ──────────────────────────────────────────────────────────
    search_form = search_filter_bar(
        endpoint="/deals",
        placeholder="Search client, company, project, or summary",
        search_value=search,
        hidden_fields={"stage": stage, "document_kind": document_kind},
        form_cls="admin-search-form admin-filter-bar mb-4",
        hx_target="body",
        hx_swap="innerHTML",
        push_url=True,
    )

    # ── Combined filter cluster: stage strip → doc-kind → search ───────────
    deals_controls = Div(
        pipeline_strip,
        Div(
            document_kind_filter,
            cls="d-flex flex-wrap align-items-center mb-3 mt-3",
        ),
        search_form,
        cls="admin-deals-controls",
    )

    # ── Deal cards in responsive grid (matches Blog/Projects) ───────────────
    deal_grid = Row(
        *[Col(_deal_card(item), span=12, md=6, lg=4) for item in items],
        cls="g-4",
    ) if items else EmptyState(
        icon="briefcase",
        title="No deals match this view",
        description="Try a different pipeline stage or create a new deal from the Quick Document form.",
        action=Button(
            Icon("plus-lg", cls="me-1"),
            "Quick Document",
            type="button",
            cls="btn admin-module-btn mt-3",
            data_bs_toggle="modal",
            data_bs_target="#quickDocModal",
        ),
        cls="py-5",
    )

    # ── Quick document modal ─────────────────────────────────────────────────
    quick_doc_modal = Modal(
        _quick_document_form(),
        modal_id="quickDocModal",
        title="Quick Document",
        size="lg",
        centered=True,
    )

    # ── Root-level quick preview modals (one per deal card) ─────────────────
    preview_modals = [_deal_quick_preview_modal(item) for item in items]

    # ── Main content panel ──────────────────────────────────────────────────
    list_panel = Card(
        Div(
            Div(
                Div(
                    H2("Pipeline Records", cls="admin-section-title"),
                    P("Track every client from lead to payment. Click any deal to view documents, responses, and generate next steps.", cls="admin-module-copy mb-0"),
                ),
                Div(
                    Button(
                        Icon("plus-lg", cls="me-1"),
                        Span("Quick Document"),
                        type="button",
                        cls="btn admin-module-btn",
                        data_bs_toggle="modal",
                        data_bs_target="#quickDocModal",
                    ),
                    cls="d-flex flex-wrap gap-2 mt-3 mt-md-0",
                ),
                cls="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-4",
            ),
            deals_controls,
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
                list_panel,
            ),
            quick_doc_modal,
            *preview_modals,
            current="/deals",
            title="Deals",
        ),
    )
