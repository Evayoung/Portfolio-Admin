"""Deal detail page — focused view with tabs for overview, documents, and editing."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, H4, Input, Label, Option, P, Select, Span, Strong, Table, Tbody, Td, Textarea, Tfoot, Th, Thead, Tr
from faststrap import Badge, Card, Col, EmptyState, Row, SEO, Tabs, TabPane

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import (
    get_deal_with_documents,
    get_document_view_time,
    list_document_responses,
)
from app.infrastructure.payment_account_repository import list_payment_accounts
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, floating_field, loading_action_button, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def deal_generate_result_fragment(title: str, message: str, tone: str = "info", draft: str = "", draft_kind: str = "proposal") -> Div:
    """Fragment for showing AI draft results or generation feedback."""
    apply_panel = Div()
    if draft:
        apply_panel = Div(
            P("AI-generated draft:", cls="admin-module-copy mt-3 mb-2"),
            Textarea(draft, rows=12, readonly=True, cls="form-control admin-form-control admin-form-textarea", id="ai-draft-content"),
            Div(
                Button("Copy Draft", type="button", cls="btn admin-module-btn",
                       hx_onclick=f"navigator.clipboard.writeText(document.getElementById('ai-draft-content').value).then(() => this.textContent = 'Copied!')"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            P("Review the draft, then save it to the document.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-detail-block mt-3",
        )
    return Div(
        status_alert(title, message, tone),
        apply_panel,
    )


def _money(value: int) -> str:
    return f"\u20a6{value:,.0f}"


def _parse_line_items(raw: str) -> list[tuple[str, str, str, int]]:
    """Parse pipe-delimited line items text into (label, detail, qty, amount) tuples."""
    items = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        label = parts[0] if len(parts) > 0 else ""
        detail = parts[1] if len(parts) > 1 else ""
        qty_str = parts[2] if len(parts) > 2 else "1"
        price_str = parts[3] if len(parts) > 3 else "0"
        try:
            qty = max(1, int(qty_str or "1"))
        except ValueError:
            qty = 1
        try:
            amount = max(0, int(float(price_str or "0")))
        except ValueError:
            amount = 0
        if label:
            items.append((label, detail, qty, amount))
    return items


def _group_packages(raw: str) -> dict[str, list[tuple[str, str, str, int]]]:
    """Group line items by Package/Option prefix. Returns dict of group_name -> items."""
    import re
    items = _parse_line_items(raw)
    groups: dict[str, list[tuple[str, str, str, int]]] = {}
    for label, detail, qty, amount in items:
        group_key = None
        for prefix in ("Package", "Option"):
            match = re.match(rf"^({prefix}\s+\w+)\s*[-:\s]", label, re.IGNORECASE)
            if match:
                group_key = match.group(1).strip()
                label = label[match.end():].strip()
                break
        if not group_key:
            group_key = "Standard"
        groups.setdefault(group_key, []).append((label, detail, qty, amount))
    return groups


def _package_totals(groups: dict[str, list[tuple[str, str, str, int]]]) -> dict[str, int]:
    """Calculate total for each package group."""
    totals = {}
    for pkg_name, items in groups.items():
        totals[pkg_name] = sum(amount * qty for _, _, qty, amount in items)
    return totals


def _status_color(status: str) -> str:
    return {
        "draft": "secondary",
        "sent": "primary",
        "accepted": "success",
        "paid": "success",
        "rejected": "danger",
        "expired": "warning",
    }.get(status, "secondary")


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
    return [("proposal", "Proposal"), ("quote", "Quote"), ("invoice", "Invoice")]


def _document_status_options() -> list[tuple[str, str]]:
    return [("draft", "Draft"), ("sent", "Sent"), ("accepted", "Accepted"), ("paid", "Paid"), ("expired", "Expired")]


def _workflow_pipeline(selected: AdminDeal) -> Div:
    """Visual pipeline showing the deal's progression."""
    stages = [
        ("lead", "Lead", "file-earmark"),
        ("proposal", "Proposal", "file-earmark-text"),
        ("quoted", "Quotation", "receipt"),
        ("invoiced", "Invoice", "credit-card"),
        ("paid", "Paid", "check-circle"),
    ]
    current_stage = selected.stage
    current_idx = next((i for i, (s, _, _) in enumerate(stages) if s == current_stage), 0)

    items = []
    for i, (stage, label, icon) in enumerate(stages):
        is_completed = i < current_idx
        is_active = i == current_idx
        status_cls = "completed" if is_completed else ("active" if is_active else "upcoming")
        items.append(
            A(
                Span(label, cls="deal-pipeline-label"),
                href=f"/deals/{selected.deal_id}?tab=documents",
                cls=f"deal-pipeline-item {status_cls}",
            )
        )
        if i < len(stages) - 1:
            items.append(Span(cls="deal-pipeline-connector"))

    return Div(*items, cls="deal-workflow-pipeline")


def _overview_tab(selected: AdminDeal) -> Div:
    """Overview tab — client info, project summary, document summary."""
    docs = selected.documents
    doc_counts = {"proposal": 0, "quote": 0, "invoice": 0}
    for doc in docs:
        doc_counts[doc.kind] = doc_counts.get(doc.kind, 0) + 1

    # Check for multi-package from proposal or quote
    source_doc = next((d for d in docs if d.kind in ("proposal", "quote")), None)
    groups = _group_packages(source_doc.line_items_text if source_doc else "") if source_doc else {}
    multi_package = len(groups) > 1
    pkg_totals = _package_totals(groups) if multi_package else {}

    # Amount display — show per-package if multi-package
    if multi_package:
        amount_display = Div(
            Span("Packages", cls="admin-field-label"),
            *[
                Div(
                    Span(pkg_name, cls="admin-module-copy"),
                    Span(_money(total), cls="fw-bold"),
                    cls="d-flex justify-content-between",
                )
                for pkg_name, total in pkg_totals.items()
            ],
            Div(
                Span("Total", cls="admin-field-label fw-bold mt-1 pt-1 border-top"),
                Span(_money(selected.amount_ngn), cls="fw-bold mt-1 pt-1 border-top"),
                cls="d-flex justify-content-between",
            ),
        )
    else:
        amount_display = Div(Span("Amount", cls="admin-field-label"), Strong(_money(selected.amount_ngn)))

    return Div(
        Row(
            Col(
                Card(
                    H3("Client Info", cls="admin-subsection-title"),
                    Div(
                        Div(Span("Client", cls="admin-field-label"), Strong(selected.client_name)),
                        Div(Span("Email", cls="admin-field-label"), Strong(selected.client_email or "Not set")),
                        Div(Span("Phone", cls="admin-field-label"), Strong(selected.client_phone or "Not set")),
                        Div(Span("Company", cls="admin-field-label"), Strong(selected.company or "Independent")),
                        cls="admin-field-grid",
                    ),
                    cls="admin-detail-block",
                ),
                span=12, md=6,
            ),
            Col(
                Card(
                    H3("Project Details", cls="admin-subsection-title"),
                    Div(
                        Div(Span("Stage", cls="admin-field-label"), Badge(selected.stage.replace("_", " ").title(), cls=f"bg-{_status_color(selected.stage)} bg-opacity-10 text-{_status_color(selected.stage)}")),
                        Div(Span("Service", cls="admin-field-label"), Strong(selected.service_type or "Not set")),
                        amount_display,
                        Div(Span("Deposit", cls="admin-field-label"), Strong(f"{selected.deposit_percent}%")),
                        cls="admin-field-grid",
                    ),
                    cls="admin-detail-block",
                ),
                span=12, md=6, cls="mt-4 mt-md-0",
            ),
            cls="g-4",
        ),
        Row(
            Col(
                Card(
                    H3("Document Summary", cls="admin-subsection-title"),
                    Div(
                        Div(
                            Span("Proposals", cls="admin-field-label"),
                            Strong(str(doc_counts["proposal"])),
                            cls="d-flex justify-content-between",
                        ),
                        Div(
                            Span("Quotations", cls="admin-field-label"),
                            Strong(str(doc_counts["quote"])),
                            cls="d-flex justify-content-between",
                        ),
                        Div(
                            Span("Invoices", cls="admin-field-label"),
                            Strong(str(doc_counts["invoice"])),
                            cls="d-flex justify-content-between",
                        ),
                        Div(
                            Span("Total Documents", cls="admin-field-label"),
                            Strong(str(len(docs))),
                            cls="d-flex justify-content-between mt-2 pt-2 border-top",
                        ),
                        cls="admin-field-grid",
                    ),
                    cls="admin-detail-block",
                ),
                span=12, md=6,
            ),
            Col(
                Card(
                    H3("Project Brief", cls="admin-subsection-title"),
                    P(selected.summary or "No summary available.", cls="admin-module-copy"),
                    P(selected.background_text or "", cls="admin-module-copy mt-2") if selected.background_text else "",
                    cls="admin-detail-block",
                ),
                span=12, md=6, cls="mt-4 mt-md-0",
            ),
            cls="g-4 mt-4",
        ),
        cls="mt-4",
    )


def _response_timeline(document_id: str) -> Div:
    """Render a chronological timeline of client responses for a document."""
    responses = list_document_responses(document_id)
    if not responses:
        return P("No client responses yet.", cls="admin-module-copy mt-2 mb-0")

    items = []
    for resp in responses:
        action_color = {
            "accepted": "success",
            "rejected": "danger",
            "commented": "info",
            "payment_submitted": "primary",
        }.get(resp.action, "secondary")

        comment_block = ""
        if resp.comment:
            comment_block = P(resp.comment, cls="deal-response-comment mt-1")

        items.append(
            Div(
                Div(
                    Badge(resp.action.replace("_", " ").title(), cls=f"bg-{action_color} bg-opacity-10 text-{action_color}"),
                    Span(resp.responder_name or "Client", cls="admin-project-meta ms-2"),
                    Span(resp.created_at, cls="admin-project-meta ms-2"),
                    cls="d-flex align-items-center flex-wrap gap-2",
                ),
                comment_block,
                cls="deal-response-item",
            )
        )

    return Div(
        P(f"Responses ({len(responses)})", cls="admin-form-section-title mt-3 mb-2"),
        Div(*items, cls="deal-response-timeline"),
    )


def _document_card_detail(selected: AdminDeal, document) -> Div:
    """Render a document card for the detail page with full actions and response timeline."""
    from app.config import settings as _s

    status_color = _status_color(document.status)
    doc_url = f"{_s.base_url.rstrip('/')}/documents/{document.public_token}" if document.public_token else ""
    view_time = get_document_view_time(document.document_id)

    # Action buttons
    actions = []

    if document.status == "draft":
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="status", value="sent"),
                loading_action_button("Mark Sent", endpoint="/deals/documents/update",
                                     target=f"#doc-status-{document.document_id}",
                                     button_cls="btn admin-install-btn"),
                action="/deals/documents/update", method="post",
                hx_post="/deals/documents/update",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                cls="d-inline-flex",
            )
        )

    if document.public_token:
        actions.append(A("Copy Link", href="#", cls="btn admin-install-btn",
                         **{"data_copy_target": doc_url, "data_copy_label": "Copy Link"}))
        actions.append(A("Open Client Link", href=f"/documents/{document.public_token}",
                         cls="btn admin-module-btn", target="_blank"))

    actions.append(A("Download PDF", href=f"/deals/{selected.deal_id}/documents/{document.kind}/pdf",
                     cls="btn admin-install-btn"))

    if document.status in {"accepted", "rejected", "paid"}:
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                loading_action_button("Reset to Sent", endpoint="/admin/document/reset",
                                     target=f"#doc-status-{document.document_id}",
                                     button_cls="btn btn-outline-warning"),
                action="/admin/document/reset", method="post",
                hx_post="/admin/document/reset",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                hx_confirm="Reset this document? This will clear all client responses.",
                cls="d-inline-flex",
            )
        )

    # Package-aware line items display
    line_items_raw = document.line_items_text or ""
    groups = _group_packages(line_items_raw)
    has_packages = len(groups) > 1 or ("Standard" not in groups and len(groups) == 1)
    multi_package = len(groups) > 1

    line_items_section = ""
    if multi_package:
        pkg_cards = []
        for pkg_name, pkg_items in groups.items():
            pkg_total = sum(amt * qty for _, _, qty, amt in pkg_items)
            rows = []
            for label, detail, qty, amount in pkg_items:
                rows.append(
                    Div(
                        Span(label, cls="admin-field-label"),
                        Span(detail, cls="admin-module-copy") if detail else "",
                        Span(f"×{qty}" if qty > 1 else "", cls="admin-project-meta"),
                        Span(_money(amount * qty), cls="fw-semibold"),
                        cls="d-flex justify-content-between align-items-baseline gap-2",
                    )
                )
            pkg_cards.append(
                Div(
                    Div(
                        Span(pkg_name, cls="fw-bold"),
                        Span(_money(pkg_total), cls="fw-bold ms-auto"),
                        cls="d-flex justify-content-between align-items-center",
                    ),
                    Div(*rows, cls="mt-1"),
                    cls="admin-pkg-group",
                )
            )
        line_items_section = Div(
            Div("Packages", cls="admin-form-section-title mt-3 mb-2"),
            *pkg_cards,
            cls="admin-pkg-breakdown",
        )
    elif groups and line_items_raw:
        # Single standard group — show compact line items
        items = list(groups.values())[0] if groups else []
        rows = []
        for label, detail, qty, amount in items:
            rows.append(
                Div(
                    Span(label, cls="admin-field-label"),
                    Span(detail, cls="admin-module-copy") if detail else "",
                    Span(f"×{qty}" if qty > 1 else "", cls="admin-project-meta"),
                    Span(_money(amount * qty), cls="fw-semibold"),
                    cls="d-flex justify-content-between align-items-baseline gap-2",
                )
            )
        if rows:
            line_items_section = Div(
                Div("Line Items", cls="admin-form-section-title mt-3 mb-2"),
                *rows,
                cls="admin-pkg-breakdown",
            )

    return Div(
        Div(
            Div(
                Span(document.kind.title(), cls="admin-project-category"),
                Badge(document.status.replace("_", " ").title(), cls=f"bg-{status_color} bg-opacity-10 text-{status_color}"),
                Span(document.document_number, cls="admin-project-meta ms-2"),
                cls="d-flex align-items-center gap-2 flex-wrap",
            ),
            cls="d-flex justify-content-between align-items-start",
        ),
        H4(document.title, cls="admin-project-title mt-2"),
        Div(
            Div(Span("Total", cls="admin-field-label"), Strong(_money(document.total_amount))),
            Div(Span("Valid Until", cls="admin-field-label"), Strong(document.valid_until or "Not set")),
            Div(Span("Due Date", cls="admin-field-label"), Strong(document.due_date or "Not set")),
            cls="admin-field-grid mt-3",
        ),
        line_items_section,
        P(f"Last viewed: {view_time}" if view_time else "", cls="admin-project-meta mt-2 mb-0"),
        Div(*actions, cls="d-flex flex-wrap gap-2 mt-3"),
        Div(id=f"doc-status-{document.document_id}", cls="mt-2"),
        _response_timeline(document.document_id),
        cls="deal-document-card",
    )


def _generate_next_cta(selected: AdminDeal, source_doc) -> Div | None:
    """Show a 'Generate Next' CTA when a document is accepted."""
    if source_doc.status not in {"accepted", "paid"}:
        return None

    next_kind = {"proposal": "quote", "quote": "invoice"}.get(source_doc.kind)
    if not next_kind:
        return None

    next_label = {"quote": "Quotation", "invoice": "Invoice"}.get(next_kind, next_kind.title())

    # Package-aware amount for the CTA
    groups = _group_packages(source_doc.line_items_text or "")
    pkg_totals = _package_totals(groups)
    multi_package = len(groups) > 1

    if multi_package:
        # Show each package as a separate generate option
        pkg_options = []
        for pkg_name, pkg_total in pkg_totals.items():
            if next_kind == "invoice":
                pkg_total = int(pkg_total * selected.deposit_percent / 100)
            pkg_options.append(
                Form(
                    Input(type="hidden", name="from_kind", value=source_doc.kind),
                    Input(type="hidden", name="to_kind", value=next_kind),
                    Input(type="hidden", name="package_name", value=pkg_name),
                    Input(type="hidden", name="package_amount", value=str(pkg_total)),
                    loading_action_button(
                        f"\u2728 {pkg_name} \u2014 {_money(pkg_total)}",
                        endpoint=f"/deals/{selected.deal_id}/generate",
                        target="#generate-result",
                        button_cls="btn admin-module-btn",
                    ),
                    action=f"/deals/{selected.deal_id}/generate",
                    method="post",
                    hx_post=f"/deals/{selected.deal_id}/generate",
                    hx_target="#generate-result",
                    hx_swap="innerHTML",
                    cls="d-inline-flex",
                )
            )
        return Div(
            Div(
                Span(f"Generate {next_label}", cls="deal-generate-label"),
                P(f"AI will use the accepted {source_doc.kind} to draft a {next_label}. Select a package:",
                  cls="admin-module-copy mb-2"),
                Div(*pkg_options, cls="d-flex flex-wrap gap-2"),
                Div(id="generate-result", cls="mt-2"),
                cls="deal-generate-next-inner",
            ),
            cls="deal-generate-next",
        )
    else:
        # Single package — use deal total or source doc total
        amount = source_doc.total_amount or selected.amount_ngn
        if next_kind == "invoice":
            amount = int(amount * selected.deposit_percent / 100)

        return Div(
            Div(
                Span(f"Generate {next_label}", cls="deal-generate-label"),
                P(f"AI will use the accepted {source_doc.kind} to draft a {next_label} for {_money(amount)}.",
                  cls="admin-module-copy mb-2"),
                Div(
                    Form(
                        Input(type="hidden", name="from_kind", value=source_doc.kind),
                        Input(type="hidden", name="to_kind", value=next_kind),
                        loading_action_button(
                            f"\u2728 AI Generate {next_label}",
                            endpoint=f"/deals/{selected.deal_id}/generate",
                            target="#generate-result",
                            button_cls="btn admin-module-btn",
                        ),
                        action=f"/deals/{selected.deal_id}/generate",
                        method="post",
                        hx_post=f"/deals/{selected.deal_id}/generate",
                        hx_target="#generate-result",
                        hx_swap="innerHTML",
                        cls="d-inline-flex",
                    ),
                ),
                Div(id="generate-result", cls="mt-2"),
                cls="deal-generate-next-inner",
            ),
            cls="deal-generate-next",
        )


def _documents_tab(selected: AdminDeal) -> Div:
    """Documents tab — each document with timeline and generate-next CTAs."""
    docs = selected.documents
    if not docs:
        return EmptyState(
            icon="file-earmark-text",
            title="No documents yet",
            description="Create the first document for this deal from the Edit tab or use Quick Document.",
            cls="py-4",
        )

    # Sort documents chronologically (oldest first for workflow display)
    sorted_docs = sorted(docs, key=lambda d: d.updated_at)

    cards = []
    for doc in sorted_docs:
        cards.append(_document_card_detail(selected, doc))
        cta = _generate_next_cta(selected, doc)
        if cta:
            cards.append(cta)

    return Div(*cards, cls="deal-documents-list")


def _public_document_url(token: str) -> str:
    return f"{settings.base_url.rstrip('/')}/documents/{token}"


def _line_items_to_text(items: list[dict]) -> str:
    lines = []
    for item in items:
        label = str(item.get("label") or "").strip()
        description = str(item.get("description") or "").strip()
        quantity = str(item.get("quantity") or "1").strip()
        unit_price = str(item.get("unit_price") or "0").strip()
        if label:
            lines.append(" | ".join((label, description, quantity, unit_price)))
    return "\n".join(lines)


def _edit_tab(selected: AdminDeal) -> Div:
    """Edit tab — deal settings form refactored from the old editor."""
    accounts = list_payment_accounts()
    return Form(
        Input(type="hidden", name="deal_id", value=selected.deal_id),

        # Client Info
        Div(
            P("Client Info", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Client Name", "client_name", selected.client_name, placeholder="Client name", required=True), span=12, md=6),
                Col(floating_field("Client Email", "client_email", selected.client_email, input_type="email", placeholder="client@example.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Row(
                Col(floating_field("Client Phone", "client_phone", selected.client_phone, placeholder="+234..."), span=12, md=6),
                Col(floating_field("Company", "company", selected.company, placeholder="Client company"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-3",
            ),
            cls="admin-form-section",
        ),

        # Project Brief
        Div(
            P("Project Brief", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Project Title", "project_title", selected.project_title, placeholder="Project title", required=True), span=12, md=7),
                Col(floating_field("Service Type", "service_type", selected.service_type, placeholder="custom-saas, quick-build"), span=12, md=5, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Div(
                Label("Pipeline Stage", cls="admin-form-label"),
                toggle_pill_group("stage", _stage_options(), selected_value=selected.stage),
                cls="admin-form-group mt-3",
            ),
            cls="admin-form-section",
        ),

        # Document Settings
        Div(
            P("Document Settings", cls="admin-form-section-title"),
            Div(
                Label("Document Type", cls="admin-form-label"),
                toggle_pill_group("document_kind", _document_options(), selected_value=selected.latest_document.kind if selected.latest_document else "proposal"),
                cls="admin-form-group",
            ),
            Div(
                Label("Document Status", cls="admin-form-label"),
                toggle_pill_group("document_status", _document_status_options(), selected_value=selected.latest_document.status if selected.latest_document else "draft"),
                cls="admin-form-group mt-3",
            ),
            floating_field("Document Title", "document_title",
                          selected.latest_document.title if selected.latest_document else "",
                          placeholder="Proposal for Project X", required=True),
            Row(
                Col(floating_field("Valid Until", "valid_until",
                                  selected.latest_document.valid_until if selected.latest_document else "",
                                  input_type="date"), span=12, md=6),
                Col(floating_field("Due Date", "due_date",
                                  selected.latest_document.due_date if selected.latest_document else "",
                                  input_type="date"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-3",
            ),
            cls="admin-form-section",
        ),

        # Financials
        Div(
            P("Financials", cls="admin-form-section-title"),
            textarea_field("Payment Terms", "payment_terms", selected.payment_terms, rows=4,
                          placeholder="Deposit expectations, milestone payments..."),
            Row(
                Col(floating_field("Amount (\u20a6)", "amount_ngn", str(selected.amount_ngn), input_type="number", placeholder="850000"), span=12, md=6),
                Col(floating_field("Deposit %", "deposit_percent", str(selected.deposit_percent), input_type="number", placeholder="50"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            cls="admin-form-section",
        ),

        # Hidden fields for backward compat
        Input(type="hidden", name="summary", value=selected.summary),
        Input(type="hidden", name="background_text", value=selected.background_text),
        Input(type="hidden", name="scope_notes", value=selected.scope_notes),
        Input(type="hidden", name="option_notes_text", value=selected.option_notes_text),
        Input(type="hidden", name="tech_stack", value=", ".join(selected.tech_stack)),
        Input(type="hidden", name="timeline_text", value=selected.timeline_text),
        Input(type="hidden", name="exclusions_text", value=selected.exclusions_text),
        Input(type="hidden", name="closing_note", value=selected.closing_note),
        Input(type="hidden", name="sections_json", value=selected.sections_json),
        Input(type="hidden", name="line_items", value=selected.line_items_text),

        Div(
            loading_action_button("Save Changes", endpoint="/deals/save", target="#deal-edit-result"),
            cls="admin-form-actions mt-4",
        ),
        Button(
            "Delete Deal", type="button",
            cls="btn btn-outline-danger mt-2",
            hx_post="/deals/delete",
            hx_vals=f'{{"deal_id": "{selected.deal_id}"}}',
            hx_target="#deal-edit-result",
            hx_swap="innerHTML",
            hx_confirm="Are you sure you want to permanently delete this deal and all its documents?",
        ),
        Div(id="deal-edit-result", cls="mt-3"),
        action="/deals/save",
        method="post",
        hx_post="/deals/save",
        hx_target="#deal-edit-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )


def deal_detail_page(*, deal_id: str = "", tab: str = "documents") -> tuple:
    """Deal detail page with tabbed layout."""
    selected = get_deal_with_documents(deal_id) if deal_id else None
    if not selected:
        return (
            *SEO(title=f"{settings.app_name} | Deal Not Found", description="Deal not found.", url=f"{settings.base_url}/deals"),
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

    # Tabs — Tabs() builds the nav bar, TabPane() builds content panels
    tabs_nav = Tabs(
        ("tab-overview", "Overview", tab == "overview"),
        ("tab-documents", "Documents", tab == "documents"),
        ("tab-edit", "Edit", tab == "edit"),
        cls="deal-detail-tabs",
    )

    tab_content = Div(
        TabPane(_overview_tab(selected), tab_id="tab-overview", active=(tab == "overview")),
        TabPane(_documents_tab(selected), tab_id="tab-documents", active=(tab == "documents")),
        TabPane(_edit_tab(selected), tab_id="tab-edit", active=(tab == "edit")),
        cls="tab-content",
    )

    tabs_component = Div(tabs_nav, tab_content)

    return (
        *SEO(
            title=f"{settings.app_name} | {selected.project_title}",
            description=f"Deal details for {selected.project_title}",
            url=f"{settings.base_url}/deals/{deal_id}",
        ),
        *page_frame(
            # Header with back link and deal summary
            Div(
                A(
                    "\u2190 Back to Pipeline",
                    href="/deals",
                    hx_get="/deals",
                    hx_target="body",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    cls="admin-back-link",
                ),
                Div(
                    Div(
                        H2(selected.project_title, cls="admin-section-title mb-1"),
                        Div(
                            Span(selected.client_name, cls="admin-project-meta"),
                            Badge(selected.stage.replace("_", " ").title(),
                                  cls=f"bg-{_status_color(selected.stage)} bg-opacity-10 text-{_status_color(selected.stage)} ms-2"),
                            Span(_money(selected.amount_ngn), cls="admin-project-meta ms-2"),
                            cls="d-flex align-items-center gap-2 flex-wrap",
                        ),
                        cls="",
                    ),
                    cls="d-flex flex-column flex-lg-row justify-content-between gap-3",
                ),
                _workflow_pipeline(selected),
                cls="mb-4",
            ),
            # Tabs content
            tabs_component,
            current="/deals",
            title=selected.project_title,
        ),
    )
