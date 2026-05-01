"""Client pipeline workspace for proposals, quotes, and invoices."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import (
    get_deal,
    get_deal_workspace_summary,
    list_document_responses,
    list_deals,
)
from app.infrastructure.payment_account_repository import list_payment_accounts
from app.infrastructure.submission_repository import get_submission
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import floating_field, loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.pages.dashboard import SectionWrap
from app.presentation.shell import page_frame


def deal_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(label, href=href, cls=f"admin-filter-chip{' active' if active else ''}")


def _money(value: int) -> str:
    return f"N{value:,.0f}"


def _public_document_url(token: str) -> str:
    return f"{settings.base_url.rstrip('/')}/documents/{token}"


def _document_action_form(*, deal_id: str, document_id: str, document_kind: str, status: str, label: str, button_cls: str = "btn admin-module-btn mt-3") -> Form:
    target_id = f"deal-document-status-result-{document_id}"
    return Form(
        Input(type="hidden", name="deal_id", value=deal_id),
        Input(type="hidden", name="document_id", value=document_id),
        Input(type="hidden", name="document_kind", value=document_kind),
        Input(type="hidden", name="status", value=status),
        loading_action_button(label, endpoint="/deals/documents/update", target=f"#{target_id}", button_cls=button_cls),
        action="/deals/documents/update",
        method="post",
        hx_post="/deals/documents/update",
        hx_target=f"#{target_id}",
        hx_swap="innerHTML",
        cls="d-inline-flex",
    )


def _deal_card(item, *, selected: bool, stage: str, document_kind: str, search: str) -> Card:
    href = f"/deals?deal_id={item.deal_id}&stage={stage}&document_kind={document_kind}&search={search}"
    latest = item.latest_document
    latest_label = latest.kind.title() if latest else "Draft"
    latest_status = latest.status.replace("_", " ").title() if latest else "No document yet"
    return Card(
        A(
            Div(
                Div(
                    Div(
                        Span(item.stage.replace("_", " ").title(), cls="admin-project-category"),
                        Badge(latest_label, cls="text-bg-secondary admin-project-flag"),
                        cls="d-flex align-items-center gap-2 flex-wrap",
                    ),
                    Span(_money(item.amount_ngn), cls="admin-project-meta"),
                    cls="d-flex justify-content-between align-items-start gap-2",
                ),
                H3(item.project_title, cls="admin-project-title"),
                P(item.summary, cls="admin-project-copy"),
                Div(
                    Span(item.client_name, cls="admin-project-meta"),
                    Span(latest_status, cls="admin-project-meta"),
                    cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
                ),
                cls="admin-project-card-body",
            ),
            href=href,
            cls=f"admin-project-card-link{' is-selected' if selected else ''}",
        ),
        cls="admin-surface-card admin-project-card",
    )


def _stage_options() -> list[tuple[str, str]]:
    return [
        ("lead", "Lead"),
        ("proposal", "Proposal"),
        ("quoted", "Quoted"),
        ("invoiced", "Invoiced"),
        ("paid", "Paid"),
        ("delivered", "Delivered"),
    ]


def _document_options() -> list[tuple[str, str]]:
    return [
        ("proposal", "Proposal"),
        ("quote", "Quote"),
        ("invoice", "Invoice"),
    ]


def _document_status_options() -> list[tuple[str, str]]:
    return [
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("accepted", "Accepted"),
        ("paid", "Paid"),
        ("expired", "Expired"),
    ]


def _document_stack(selected) -> Div:
    documents = selected.documents if selected else ()
    if not documents:
        return EmptyState(
            icon="file-earmark-text",
            title="No documents yet",
            description="Use the editor below to draft the first proposal, quote, or invoice for this client.",
            cls="py-4",
        )
    return Div(
        *[
            _document_card(selected, document)
            for document in documents
        ],
        cls="admin-panel-stack mt-4",
    )


def _document_card(selected, document) -> Div:
    responses = list_document_responses(document.document_id)
    latest_response = responses[0] if responses else None
    response_action = latest_response.action if latest_response else ""
    return Div(
        Div(
            Div(
                Span(document.kind.title(), cls="admin-project-category"),
                Badge(document.status.replace("_", " ").title(), cls="text-bg-secondary admin-project-flag"),
                cls="d-flex align-items-center gap-2 flex-wrap",
            ),
            Span(document.document_number, cls="admin-project-meta"),
            cls="d-flex justify-content-between align-items-start gap-3 flex-wrap",
        ),
        H3(document.title, cls="admin-project-title mt-3"),
        Div(
            Div(Span("Total", cls="admin-field-label"), Strong(_money(document.total_amount))),
            Div(Span("Valid Until", cls="admin-field-label"), Strong(document.valid_until or "Not set")),
            Div(Span("Due Date", cls="admin-field-label"), Strong(document.due_date or "Not set")),
            cls="admin-field-grid mt-3",
        ),
        Div(
            Div(Span("Client Link", cls="admin-field-label"), Strong("Share-ready" if document.public_token else "Not available")),
            Div(
                Span("Responses", cls="admin-field-label"),
                Strong(str(len(responses))),
            ),
            Div(
                Span("Latest Client Action", cls="admin-field-label"),
                Strong(latest_response.action.replace("_", " ").title() if latest_response else "No response yet"),
            ),
            cls="admin-field-grid mt-3",
        ),
        P(
            f"{latest_response.responder_name or 'Client'} | {latest_response.created_at} | {latest_response.comment or 'No comment supplied.'}"
            if latest_response
            else "No client feedback has been recorded on this document yet.",
            cls="admin-module-copy mt-3 mb-0",
        ),
        Div(
            A(
                "Download PDF",
                href=f"/deals/{selected.deal_id}/documents/{document.kind}/pdf",
                cls="btn admin-install-btn mt-3",
            ),
            A(
                "Open Client Link",
                href=f"/documents/{document.public_token}",
                cls="btn admin-module-btn mt-3",
                target="_blank",
            )
            if document.public_token
            else "",
            A(
                "Copy Link",
                href="#",
                cls="btn admin-install-btn mt-3",
                data_copy_target=_public_document_url(document.public_token),
                data_copy_label="Copy Link",
            )
            if document.public_token
            else "",
            _document_action_form(
                deal_id=selected.deal_id,
                document_id=document.document_id,
                document_kind=document.kind,
                status="sent",
                label="Mark Sent",
                button_cls="btn admin-install-btn mt-3",
            )
            if document.status == "draft"
            else "",
            _document_action_form(
                deal_id=selected.deal_id,
                document_id=document.document_id,
                document_kind=document.kind,
                status="paid",
                label="Confirm Paid",
            )
            if document.kind == "invoice" and document.status != "paid" and response_action == "payment_submitted"
            else "",
            cls="d-flex flex-wrap gap-2",
        ),
        P(_public_document_url(document.public_token), cls="admin-project-meta mt-2 mb-0") if document.public_token else "",
        Div(id=f"deal-document-status-result-{document.document_id}", cls="mt-3"),
        cls="admin-detail-block",
    )


def _deal_from_submission(entry_id: str, kind: str) -> AdminDeal | None:
    submission = get_submission(entry_id, kind=kind or "all")
    if not submission:
        return None
    service_label = submission.service or ("client-inquiry" if submission.kind == "contact" else "booking-request")
    project_title = submission.subject or submission.service or f"{submission.kind.title()} Request"
    budget_note = " / ".join(part for part in (submission.budget, submission.timeline) if part)
    return AdminDeal(
        deal_id="",
        client_name=submission.name or "",
        client_email=submission.email or "",
        client_phone=submission.phone or "",
        company="",
        project_title=project_title,
        service_type=service_label,
        stage="lead",
        summary=submission.message or "",
        background_text=submission.message or "",
        scope_notes="",
        option_notes_text="",
        tech_stack=(),
        timeline_text=submission.timeline or "",
        payment_terms="",
        line_items_text="",
        exclusions_text="",
        closing_note="",
        amount_ngn=0,
        deposit_percent=50,
        source="submission",
        documents=(),
        latest_document=None,
    )


def _editor_form(selected, *, stage: str, document_kind: str, search: str) -> Form:
    latest = selected.latest_document if selected else None
    selected_stage = selected.stage if selected else "lead"
    selected_kind = latest.kind if latest else "proposal"
    selected_status = latest.status if latest else "draft"
    accounts = list_payment_accounts()
    return Form(
        Input(type="hidden", name="deal_id", value=selected.deal_id if selected else ""),
        Input(type="hidden", name="current_stage", value=stage),
        Input(type="hidden", name="current_document_kind", value=document_kind),
        Input(type="hidden", name="current_search", value=search),

        # ── Group 1: Client Info ─────────────────────────────────
        Div(
            P("Client Info", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Client Name", "client_name", selected.client_name if selected else "", placeholder="Client or company contact", required=True), span=12, md=6),
                Col(floating_field("Client Email", "client_email", selected.client_email if selected else "", input_type="email", placeholder="client@example.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Row(
                Col(floating_field("Client Phone", "client_phone", selected.client_phone if selected else "", placeholder="+234..."), span=12, md=6),
                Col(floating_field("Company", "company", selected.company if selected else "", placeholder="Client company"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-3",
            ),
            cls="admin-form-section",
        ),

        # ── Group 2: Project Brief ────────────────────────────────
        Div(
            P("Project Brief", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Project Title", "project_title", selected.project_title if selected else "", placeholder="Portal rebuild, SaaS MVP, landing page", required=True), span=12, md=7),
                Col(floating_field("Service Type", "service_type", selected.service_type if selected else "", placeholder="custom-saas, quick-build, retainer"), span=12, md=5, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Div(
                Label("Pipeline Stage", cls="admin-form-label"),
                toggle_pill_group("stage", _stage_options(), selected_value=selected_stage),
                cls="admin-form-group mt-3",
            ),
            cls="admin-form-section",
        ),

        # ── Group 3: Document Settings ────────────────────────────
        Div(
            P("Document Settings", cls="admin-form-section-title"),
            Div(
                Label("Document Type", cls="admin-form-label"),
                toggle_pill_group("document_kind", _document_options(), selected_value=selected_kind),
                cls="admin-form-group",
            ),
            Div(
                Label("Document Status", cls="admin-form-label"),
                toggle_pill_group("document_status", _document_status_options(), selected_value=selected_status),
                cls="admin-form-group mt-3",
            ),
            floating_field("Document Title", "document_title", latest.title if latest else "", placeholder="Proposal for FarmTech Dashboard", required=True),
            Row(
                Col(floating_field("Valid Until", "valid_until", latest.valid_until if latest else "", input_type="date", placeholder=""), span=12, md=6),
                Col(floating_field("Due Date", "due_date", latest.due_date if latest else "", input_type="date", placeholder=""), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-3",
            ),
            Div(
                Label("Invoice Payment Account", cls="admin-form-label"),
                Select(
                    Option("Choose account", value=""),
                    *[
                        Option(
                            f"{account.label} - {account.bank_name} ({account.account_number})",
                            value=account.account_id,
                            selected=bool(latest and account.account_id == latest.payment_account_id),
                        )
                        for account in accounts
                    ],
                    name="payment_account_id",
                    cls="form-select admin-form-control",
                ),
                cls="admin-form-group mt-3",
            ),
            cls="admin-form-section",
        ),

        # ── Group 4: Narrative ────────────────────────────────────
        Div(
            P("Narrative", cls="admin-form-section-title"),
            textarea_field("Professional Summary", "summary", selected.summary if selected else "", rows=4, required=True, placeholder="Client-facing summary of the outcome, scope, and why this engagement matters."),
            textarea_field("Background & Objective", "background_text", selected.background_text if selected else "", rows=5, placeholder="Explain the client context, business need, and why this work matters right now."),
            textarea_field("Scope & Deliverables", "scope_notes", selected.scope_notes if selected else "", rows=5, required=True, placeholder="Describe scope, deliverables, milestones, and assumptions."),
            textarea_field("Options / Pricing Paths", "option_notes_text", selected.option_notes_text if selected else "", rows=5, placeholder="One per line: Option Title | Summary | Cost or note"),
            textarea_field("Timeline", "timeline_text", selected.timeline_text if selected else "", rows=4, placeholder="Outline phases, durations, and review windows."),
            cls="admin-form-section",
        ),

        # ── Group 5: Financials ───────────────────────────────────
        Div(
            P("Financials", cls="admin-form-section-title"),
            textarea_field(
                "Line Items",
                "line_items",
                selected.line_items_text if selected else "",
                rows=5,
                placeholder="One per line: Item | Description | Qty | Amount",
                help_text="Format: Item | Description | Qty | Amount (e.g. Design | Wireframes | 1 | 50000)",
            ),
            textarea_field("Payment Terms", "payment_terms", selected.payment_terms if selected else "", rows=4, placeholder="Deposit expectations, milestone payments, revision rules, and invoice notes."),
            Row(
                Col(floating_field("Amount (NGN)", "amount_ngn", str(selected.amount_ngn) if selected else "", input_type="number", placeholder="850000"), span=12, md=6),
                Col(floating_field("Deposit %", "deposit_percent", str(selected.deposit_percent) if selected else "50", input_type="number", placeholder="50"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            cls="admin-form-section",
        ),

        # ── Group 6: Closing ──────────────────────────────────────
        Div(
            P("Closing", cls="admin-form-section-title"),
            textarea_field("Exclusions / Out of Scope", "exclusions_text", selected.exclusions_text if selected else "", rows=4, placeholder="List items that are not included in this engagement."),
            textarea_field("Closing Note", "closing_note", selected.closing_note if selected else "", rows=4, placeholder="Final closing paragraph, reassurance, or next-step note."),
            floating_field("Tech Stack", "tech_stack", ", ".join(selected.tech_stack) if selected else "", placeholder="FastHTML, Supabase, HTMX"),
            cls="admin-form-section",
        ),

        Div(
            loading_action_button("Save Deal Draft", endpoint="/deals/save", target="#deal-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="deal-save-result", cls="mt-3"),
        action="/deals/save",
        method="post",
        hx_post="/deals/save",
        hx_target="#deal-save-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )


def _quick_document_form() -> Form:
    accounts = list_payment_accounts()
    return Form(
        Div(
            P("Client", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Client Name", "client_name", "", placeholder="Client or friend name", required=True), span=12, md=6),
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
                        toggle_pill_group("document_kind", _document_options(), selected_value="invoice"),
                        cls="admin-form-group",
                    ),
                    span=12,
                    md=7,
                ),
                Col(
                    Div(
                        Label("Status", cls="admin-form-label"),
                        Select(
                            *[Option(label, value=value, selected=value == "draft") for value, label in _document_status_options()],
                            name="document_status",
                            cls="form-select admin-form-control",
                        ),
                        cls="admin-form-group",
                    ),
                    span=12,
                    md=5,
                    cls="mt-3 mt-md-0",
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
            textarea_field(
                "Line Items",
                "line_items",
                "",
                rows=4,
                placeholder="One per line: Item | Description | Qty | Amount",
                help_text="Leave blank and use Amount if this is a simple one-line invoice.",
            ),
            Row(
                Col(floating_field("Amount (NGN)", "amount_ngn", "", input_type="number", placeholder="50000"), span=12, md=6),
                Col(floating_field("Deposit %", "deposit_percent", "100", input_type="number", placeholder="100"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            Row(
                Col(floating_field("Valid Until", "valid_until", "", input_type="date", placeholder=""), span=12, md=6),
                Col(floating_field("Due Date", "due_date", "", input_type="date", placeholder=""), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            Div(
                Label("Payment Account", cls="admin-form-label"),
                Select(
                    Option("Use default / none", value=""),
                    *[
                        Option(
                            f"{account.label} - {account.bank_name} ({account.account_number})",
                            value=account.account_id,
                        )
                        for account in accounts
                    ],
                    name="payment_account_id",
                    cls="form-select admin-form-control",
                ),
                cls="admin-form-group mt-3",
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


def deals_workspace_page(*, deal_id: str = "", stage: str = "all", document_kind: str = "all", search: str = "", from_submission: str = "", from_kind: str = "") -> tuple:
    all_items = list_deals()
    items = list_deals(stage=stage, document_kind=document_kind, search=search)
    selected = get_deal(deal_id)
    if not selected and from_submission:
        selected = _deal_from_submission(from_submission, from_kind)
    if not selected:
        selected = items[0] if items else None
    summary = get_deal_workspace_summary()

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
    )

    list_panel = Card(
        Div(
            Div(
                H2("Pipeline Records", cls="admin-section-title"),
                P("Leads, proposals, quotes, and invoices stay attached to the same deal so you can move a client forward without rewriting the document context.", cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            stage_links,
            document_links,
            search_form,
            Div(
                *[
                    _deal_card(
                        item,
                        selected=bool(selected and item.deal_id == selected.deal_id),
                        stage=stage,
                        document_kind=document_kind,
                        search=search,
                    )
                    for item in items
                ],
                cls="admin-project-list mt-4",
            )
            if items
            else EmptyState(
                icon="briefcase",
                title="No deal matches this view",
                description="Try a different pipeline stage or create a new record from the editor panel.",
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    detail_panel = Card(
        Div(
            Div(
                Div(
                    Span("Selected deal", cls="admin-kicker"),
                    H2(selected.project_title if selected else "New client pipeline record", cls="admin-section-title mb-2"),
                    P(selected.background_text if selected and selected.background_text else (selected.summary if selected else "Use this workspace to manage proposals, quick quotes, and invoices as stages of the same deal."), cls="admin-module-copy mb-0"),
                    cls="admin-detail-copy",
                ),
                Div(
                    Badge(summary.source, cls="text-bg-secondary admin-metric-delta"),
                    Badge("Write enabled" if service_role_is_configured() else "Read-only for now", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                    cls="d-flex flex-wrap gap-2 mt-3 mt-lg-0",
                ),
                cls="d-flex flex-column flex-lg-row justify-content-between gap-3",
            ),
            Div(
                Row(
                    Col(
                        Div(
                            H3("Client Snapshot", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Client", cls="admin-field-label"), Strong(selected.client_name if selected else "New client")),
                                Div(Span("Company", cls="admin-field-label"), Strong(selected.company if selected and selected.company else "Independent / not set")),
                                Div(Span("Email", cls="admin-field-label"), Strong(selected.client_email if selected and selected.client_email else "Not set")),
                                Div(Span("Phone", cls="admin-field-label"), Strong(selected.client_phone if selected and selected.client_phone else "Not set")),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                    ),
                    Col(
                        Div(
                            H3("Delivery Snapshot", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Stage", cls="admin-field-label"), Strong(selected.stage.replace("_", " ").title() if selected else "Lead")),
                                Div(Span("Service", cls="admin-field-label"), Strong(selected.service_type if selected and selected.service_type else "Not set")),
                                Div(Span("Budget", cls="admin-field-label"), Strong(_money(selected.amount_ngn) if selected else "N0")),
                                Div(Span("Deposit", cls="admin-field-label"), Strong(f"{selected.deposit_percent if selected else 50}%")),
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
                H3("Document Stack", cls="admin-subsection-title"),
                P("Each deal can carry a proposal, quote, and invoice trail, making it easy to keep one client history from lead to payment.", cls="admin-module-copy"),
                _document_stack(selected),
                cls="admin-detail-block mt-4",
            ),
            Div(
                H3("Deal Studio", cls="admin-subsection-title"),
                P("This first version gives you the structured pipeline foundation. PDF styling, public acceptance links, staged invoice splitting, and media attachments can layer on top of this model cleanly.", cls="admin-module-copy"),
                _editor_form(selected, stage=stage, document_kind=document_kind, search=search),
                cls="admin-detail-block mt-4",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    # Pipeline progress strip — clickable stage counters
    quick_panel = Card(
        Div(
            Div(
                H2("Quick Document Studio", cls="admin-section-title"),
                P(
                    "Generate a proposal, quote, or invoice directly when you do not need the full lead workflow. Neo Admin still keeps a lightweight record so the link, PDF, and response history remain traceable.",
                    cls="admin-module-copy mb-0",
                ),
                cls="mb-3",
            ),
            _quick_document_form(),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card",
    )

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
                "Deals Workspace",
                Div(
                    Row(
                        Col(quick_panel, span=12),
                        cls="g-4 mb-4",
                    ),
                    pipeline_strip,
                    Row(
                        Col(list_panel, span=12, lg=5),
                        Col(detail_panel, span=12, lg=7, cls="mt-4 mt-lg-0"),
                        cls="g-4",
                    ),
                ),
            ),
            current="/deals",
            title="Deals",
        ),
    )
