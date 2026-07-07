"""Client pipeline workspace for proposals, quotes, and invoices."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong, Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr
from faststrap import Badge, Button, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import (
    get_deal,
    get_deal_workspace_summary,
    get_document_view_time,
    list_document_responses,
    list_deals,
)
from app.infrastructure.payment_account_repository import list_payment_accounts
from app.infrastructure.submission_repository import get_submission
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, floating_field, loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def deal_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def ai_draft_result_fragment(title: str, message: str, tone: str = "info", draft: str = "") -> Div:
    apply_panel = Div()
    if draft:
        targets = [
            ("summary", "Summary"),
            ("background_text", "Background"),
            ("scope_notes", "Scope"),
            ("timeline_text", "Timeline"),
            ("payment_terms", "Payment Terms"),
            ("exclusions_text", "Exclusions"),
            ("closing_note", "Closing Note"),
        ]
        apply_panel = Div(
            P("Apply draft to a section field:", cls="admin-module-copy mt-3 mb-2"),
            Div(
                *[
                    Button(
                        label,
                        type="button",
                        cls="btn admin-install-btn",
                        data_apply_field=field_id,
                        data_draft_source="ai-draft-content",
                    )
                    for field_id, label in targets
                ],
                cls="d-flex flex-wrap gap-2",
            ),
        )
    return Div(
        status_alert(title, message, tone),
        Div(
            Textarea(draft, rows=12, readonly=True, cls="form-control admin-form-control admin-form-textarea", id="ai-draft-content"),
            Div(
                Button("Copy Draft", type="button", cls="btn admin-module-btn", data_copy_target=draft, data_copy_label="Copy Draft"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            apply_panel,
            P("Review the draft, apply useful sections to the right fields above, then save.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-detail-block mt-3",
        )
        if draft
        else "",
    )


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(label, href=href, cls=f"admin-filter-chip{' active' if active else ''}")


def _money(value: int) -> str:
    return f"N{value:,.0f}"


def _parse_line_items_display(raw: str) -> list[dict]:
    """Parse pipe-delimited line items into display-friendly dicts."""
    rows: list[dict] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        rows.append({
            "label": parts[0] if len(parts) > 0 else "",
            "description": parts[1] if len(parts) > 1 else "",
            "quantity": parts[2] if len(parts) > 2 else "1",
            "unit_price": parts[3] if len(parts) > 3 else "0",
        })
    return rows


def _line_items_editor(current_value: str) -> Div:
    """Table-based line items editor with live totals, add/delete, paste support."""
    items = _parse_line_items_display(current_value)
    if not items:
        items = [{"label": "", "description": "", "quantity": "1", "unit_price": "0"}]

    def _row(item: dict) -> Tr:
        return Tr(
            Td(Input(type="text", cls="form-control form-control-sm li-item", placeholder="Item name", value=item["label"])),
            Td(Input(type="text", cls="form-control form-control-sm li-desc", placeholder="Description", value=item["description"])),
            Td(Input(type="text", cls="form-control form-control-sm li-qty", placeholder="Qty", value=item["quantity"]), style="width:80px"),
            Td(Input(type="text", cls="form-control form-control-sm li-amount", placeholder="Amount", value=item["unit_price"]), style="width:120px"),
            Td(Button("×", type="button", cls="btn btn-outline-danger btn-sm li-delete"), style="width:40px"),
        )

    return Div(
        P("Enter line items below. Use Tab to move between cells. Paste spreadsheet rows with Tab as separator.", cls="admin-module-copy mb-2"),
        Input(type="hidden", name="line_items", id="line_items", value=current_value),
        Table(
            Thead(Tr(Th("Item"), Th("Description"), Th("Qty", style="width:80px"), Th("Amount", style="width:120px"), Th(style="width:40px"))),
            Tbody(*[_row(item) for item in items]),
            Tfoot(
                Tr(
                    Td(Strong("Total"), colspan="3"),
                    Td(Strong("0", cls="li-total-value"), id="li-total-cell"),
                    Td(""),
                )
            ),
            cls="table table-sm table-bordered line-items-table mb-2",
        ),
        Div(
            Button("+ Add Row", type="button", cls="btn btn-sm btn-outline-primary li-add-row"),
            Span("Paste from spreadsheets or copy existing rows", cls="admin-save-note ms-3"),
            cls="d-flex align-items-center",
        ),
        cls="line-items-editor mt-2",
    )




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


def _document_link_action_form(*, deal_id: str, document_id: str, document_kind: str, action: str, label: str, button_cls: str = "btn admin-install-btn mt-3") -> Form:
    target_id = f"deal-document-status-result-{document_id}"
    return Form(
        Input(type="hidden", name="deal_id", value=deal_id),
        Input(type="hidden", name="document_id", value=document_id),
        Input(type="hidden", name="document_kind", value=document_kind),
        Input(type="hidden", name="action", value=action),
        loading_action_button(label, endpoint="/deals/documents/link", target=f"#{target_id}", button_cls=button_cls),
        action="/deals/documents/link",
        method="post",
        hx_post="/deals/documents/link",
        hx_target=f"#{target_id}",
        hx_swap="innerHTML",
        cls="d-inline-flex",
    )


def _deal_card(item, *, selected: bool, stage: str, document_kind: str, search: str) -> Card:
    href = f"/deals?deal_id={item.deal_id}&stage={stage}&document_kind={document_kind}&search={search}"
    latest = item.latest_document
    latest_label = latest.kind.title() if latest else "Draft"
    latest_status = latest.status.replace("_", " ").title() if latest else "No document yet"
    copy_link_btn = ""
    if latest and latest.public_token:
        doc_url = _public_document_url(latest.public_token)
        copy_link_btn = Div(
            Button(
                "Copy Client Link",
                type="button",
                cls="btn admin-install-btn w-100",
                data_copy_target=doc_url,
                data_copy_label="Copy Client Link",
            ),
            cls="px-3 pb-3",
        )
    return Card(
        A(
            Div(
                Div(
                    Span(item.stage.replace("_", " ").title(), cls="admin-project-category"),
                    Badge(latest_label, cls="text-bg-secondary admin-project-flag"),
                    cls="d-flex align-items-center gap-2 flex-wrap",
                ),
                Badge("Published", cls="text-bg-success admin-project-flag") if latest and latest.status == "paid" else Badge(latest_status, cls="text-bg-secondary admin-project-flag"),
                cls="d-flex justify-content-between align-items-start gap-2",
            ),
            Span(_money(item.amount_ngn), cls="admin-project-meta"),
            H3(item.project_title, cls="admin-project-title"),
            P(item.summary, cls="admin-project-copy"),
            Div(
                Span(item.client_name, cls="admin-project-meta"),
                Span(latest_status, cls="admin-project-meta"),
                cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
            ),
            cls="admin-project-card-body",
            href=href,
        ),
        copy_link_btn,
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


def _ai_draft_options() -> list[tuple[str, str]]:
    return [
        ("proposal", "Proposal"),
        ("quote", "Quotation"),
        ("invoice", "Invoice"),
        ("scope", "Scope"),
        ("payment_terms", "Payment Terms"),
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


def _ai_draft_panel(selected_kind: str) -> Div:
    draft_kind = selected_kind if selected_kind in {"proposal", "quote", "invoice"} else "proposal"
    return Div(
        P("AI Draft Assistant", cls="admin-form-section-title"),
        P("Use Groq to draft editable proposal, quotation, invoice, scope, or payment text from the current form values. Nothing is sent to clients automatically.", cls="admin-module-copy"),
        Div(
            Label("Draft Type", cls="admin-form-label"),
            toggle_pill_group("ai_draft_kind", _ai_draft_options(), selected_value=draft_kind),
            cls="admin-form-group",
        ),
        Div(
            loading_action_button("Generate AI Draft", endpoint="/deals/ai-draft", target="#ai-draft-result"),
            Span("Backend-only Groq call. Review before saving.", cls="admin-save-note"),
            cls="admin-form-actions mt-3",
        ),
        Div(id="ai-draft-result", cls="mt-3"),
        cls="admin-form-section",
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
            Div(
                Span("Last Viewed", cls="admin-field-label"),
                Strong(get_document_view_time(document.document_id) or "Not yet"),
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
            _document_link_action_form(
                deal_id=selected.deal_id,
                document_id=document.document_id,
                document_kind=document.kind,
                action="resend",
                label="Resend Link",
            )
            if document.public_token
            else "",
            _document_link_action_form(
                deal_id=selected.deal_id,
                document_id=document.document_id,
                document_kind=document.kind,
                action="regenerate",
                label="New Version Link",
            ),
            _document_link_action_form(
                deal_id=selected.deal_id,
                document_id=document.document_id,
                document_kind=document.kind,
                action="revoke",
                label="Revoke Link",
                button_cls="btn btn-outline-danger mt-3",
            )
            if document.public_token
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
        sections_json="",
        amount_ngn=0,
        deposit_percent=50,
        source="submission",
        documents=(),
        latest_document=None,
    )


def _section_editor(current_sections_json: str) -> Div:
    """Dynamic section editor — add, reorder, edit, delete document sections."""
    return Div(
        P("Document Sections", cls="admin-form-section-title"),
        P("Add custom sections with markdown content. Arrange them in any order using the up/down buttons.", cls="admin-module-copy"),
        Input(type="hidden", name="sections_json", id="sections_json", value=current_sections_json),
        Div(id="deal-sections-container", cls="mt-3"),
        Div(
            Button("+ Add Section", type="button", cls="btn admin-install-btn", id="deal-section-add-btn"),
            cls="mt-3",
        ),
        _section_modal(),
        cls="admin-form-section",
    )


def _section_modal() -> Div:
    """Bootstrap modal for adding/editing a section."""
    return Div(
        Div(
            Div(
                Div(
                    H3("Add Section", cls="modal-title fs-5", id="deal-section-modal-title"),
                    Button(type="button", cls="btn-close", data_bs_dismiss="modal", aria_label="Close"),
                    cls="modal-header",
                ),
                Div(
                    Input(type="text", cls="form-control admin-form-control mb-3", id="deal-section-title-input", placeholder="Section title (e.g. Executive Summary)"),
                    Textarea(cls="form-control admin-form-control admin-form-textarea", id="deal-section-content-input", rows=10, placeholder="## Markdown content\n\nWrite your section content here using markdown..."),
                    P("Supports markdown: headings, lists, tables, code blocks, links.", cls="admin-module-copy mt-2 mb-0"),
                    cls="modal-body",
                ),
                Div(
                    Button("Cancel", type="button", cls="btn admin-module-btn", data_bs_dismiss="modal"),
                    Button("Save Section", type="button", cls="btn admin-install-btn", id="deal-section-save-btn"),
                    cls="modal-footer",
                ),
                cls="modal-content",
            ),
            cls="modal-dialog modal-lg",
        ),
        cls="modal fade",
        id="deal-section-modal",
        tabindex="-1",
        aria_hidden="true",
    )


def _editor_form(selected, *, stage: str, document_kind: str, search: str) -> Form:
    latest = selected.latest_document if selected else None
    selected_stage = selected.stage if selected else "lead"
    selected_kind = latest.kind if latest else "proposal"
    selected_status = latest.status if latest else "draft"
    preview_url = _public_document_url(latest.public_token) if latest and latest.public_token else ""
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

        # ── Group 4: Document Sections (dynamic editor) ──────────
        _section_editor(selected.sections_json if selected else ""),
        # Hidden backward-compat fields for existing deals with fixed narratives
        Input(type="hidden", name="summary", value=selected.summary if selected else ""),
        Input(type="hidden", name="background_text", value=selected.background_text if selected else ""),
        Input(type="hidden", name="scope_notes", value=selected.scope_notes if selected else ""),
        Input(type="hidden", name="option_notes_text", value=selected.option_notes_text if selected else ""),
        Input(type="hidden", name="timeline_text", value=selected.timeline_text if selected else ""),
        Input(type="hidden", name="exclusions_text", value=selected.exclusions_text if selected else ""),
        Input(type="hidden", name="closing_note", value=selected.closing_note if selected else ""),

        # ── Group 5: Financials ───────────────────────────────────
        _ai_draft_panel(selected_kind),
        Div(
            P("Financials", cls="admin-form-section-title"),
            _line_items_editor(selected.line_items_text if selected else ""),
            textarea_field("Payment Terms", "payment_terms", selected.payment_terms if selected else "", rows=4, placeholder="Deposit expectations, milestone payments, revision rules, and invoice notes."),
            Row(
                Col(floating_field("Amount (NGN)", "amount_ngn", str(selected.amount_ngn) if selected else "", input_type="number", placeholder="850000"), span=12, md=6),
                Col(floating_field("Deposit %", "deposit_percent", str(selected.deposit_percent) if selected else "50", input_type="number", placeholder="50"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            cls="admin-form-section",
        ),

        # ── Group 6: Tech Stack ──────────────────────────────────
        Div(
            P("Tech Stack", cls="admin-form-section-title"),
            floating_field("Tech Stack", "tech_stack", ", ".join(selected.tech_stack) if selected else "", placeholder="FastHTML, Supabase, HTMX"),
            cls="admin-form-section",
        ),

        Div(
            A(
                "Preview Client View",
                href=preview_url,
                target="_blank",
                cls="btn admin-install-btn",
            )
            if preview_url
            else Span("Save the deal to generate a preview link", cls="admin-save-note"),
            loading_action_button("Save Deal Draft", endpoint="/deals/save", target="#deal-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Form(
            Input(type="hidden", name="deal_id", value=selected.deal_id if selected else ""),
            Button(
                "Delete Deal",
                type="submit",
                cls="btn btn-outline-danger mt-2",
                onclick="return confirm('Are you sure you want to permanently delete this deal and all its documents? This cannot be undone.')",
            ),
            action="/deals/delete",
            method="post",
            hx_post="/deals/delete",
            hx_target="#deal-save-result",
            hx_swap="innerHTML",
        )
        if selected and selected.deal_id
        else "",
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
            _line_items_editor(""),
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
    items = all_items
    if stage != "all" or document_kind != "all" or search:
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
                    pipeline_strip,
                    Row(
                        Col(list_panel, span=12, lg=5),
                        Col(
                            Button(
                                "Show Editor ↓",
                                type="button",
                                cls="admin-panel-toggle-btn",
                                data_panel_toggle="deals-detail-panel",
                                id="deals-panel-toggle",
                            ),
                            span=12,
                            cls="d-lg-none",
                        ),
                        Col(
                            detail_panel,
                            id="deals-detail-panel",
                            span=12,
                            lg=7,
                            cls="admin-panel-hidden",
                        ),
                        cls="g-4",
                    ),
                    SectionWrap("Quick Document Studio", quick_panel),
                ),
            ),
            current="/deals",
            title="Deals",
        ),
    )
