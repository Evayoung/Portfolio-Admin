"""Deal detail documents tab module — document list, status updates, response timelines, line items, and generate-next CTAs."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, Input, P, Span, Strong
from faststrap import Accordion, AccordionItem, Badge, Button, Card, Col, EmptyState, Fx, Icon, Row, SEO, Spinner

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import (
    get_deal_with_documents,
    get_document_view_time,
    list_document_responses,
)
from app.presentation.page_helpers import loading_action_button
from app.presentation.pages.deal_helpers import (
    _deal_snapshot_card,
    _group_packages,
    _money,
    _package_totals,
    _status_color,
    _workflow_pipeline,
)
from app.presentation.shell import page_frame


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


def _document_card_detail(selected: AdminDeal, document, *, next_step=None) -> AccordionItem:
    """Render one collapsed-by-default document with details and actions inside."""
    doc_url = f"{settings.base_url.rstrip('/')}/documents/{document.public_token}" if document.public_token else ""
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
                loading_action_button(
                    Icon("send"),
                    endpoint="/deals/documents/update",
                    target=f"#doc-status-{document.document_id}",
                    button_cls="btn admin-icon-btn admin-icon-btn-only admin-install-btn",
                    aria_label="Mark document as sent",
                    title="Mark document as sent",
                ),
                action="/deals/documents/update",
                method="post",
                hx_post="/deals/documents/update",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                cls="d-inline-flex",
            )
        )

    if document.status == "sent":
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="status", value="accepted"),
                loading_action_button(
                    Icon("check2-circle"),
                    endpoint="/deals/documents/update",
                    target=f"#doc-status-{document.document_id}",
                    button_cls="btn admin-icon-btn admin-icon-btn-only btn-outline-success",
                    aria_label="Mark document as accepted",
                    title="Mark document as accepted",
                ),
                action="/deals/documents/update",
                method="post",
                hx_post="/deals/documents/update",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                hx_confirm="Mark this document as accepted?",
                cls="d-inline-flex",
            )
        )

    if document.public_token:
        actions.append(
            A(
                Icon("clipboard"),
                href="#",
                cls="btn admin-icon-btn admin-icon-btn-only admin-install-btn",
                aria_label="Copy public link",
                title="Copy public link",
                **{"data_copy_target": doc_url, "data_copy_label": "Copy public link"},
            )
        )
        actions.append(
            A(
                Icon("box-arrow-up-right"),
                href=f"/documents/{document.public_token}",
                cls="btn admin-icon-btn admin-icon-btn-only admin-module-btn",
                aria_label="Open client link",
                title="Open client link",
                target="_blank",
            )
        )
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="action", value="resend"),
                Button(Icon("send"), type="submit", cls="btn admin-icon-btn admin-icon-btn-only admin-install-btn", aria_label="Resend document", title="Resend document"),
                action="/deals/documents/link",
                method="post",
                hx_post="/deals/documents/link",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                cls="d-inline-flex",
            )
        )
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="action", value="regenerate"),
                Button(Icon("arrow-repeat"), type="submit", cls="btn admin-icon-btn admin-icon-btn-only admin-install-btn", aria_label="Regenerate public link", title="Regenerate public link"),
                action="/deals/documents/link",
                method="post",
                hx_post="/deals/documents/link",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                hx_confirm="Generate a new public link for this document?",
                cls="d-inline-flex",
            )
        )
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="action", value="revoke"),
                Button(Icon("slash-circle"), type="submit", cls="btn admin-icon-btn admin-icon-btn-only btn-outline-warning", aria_label="Revoke public link", title="Revoke public link"),
                action="/deals/documents/link",
                method="post",
                hx_post="/deals/documents/link",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                hx_confirm="Revoke this public client link?",
                cls="d-inline-flex",
            )
        )
    else:
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="action", value="regenerate"),
                Button(Icon("link-45deg"), type="submit", cls="btn admin-icon-btn admin-icon-btn-only admin-module-btn", aria_label="Generate public link", title="Generate public link"),
                action="/deals/documents/link",
                method="post",
                hx_post="/deals/documents/link",
                hx_target=f"#doc-status-{document.document_id}",
                hx_swap="innerHTML",
                cls="d-inline-flex",
            )
        )

    actions.append(
        A(
            Icon("download"),
            href=f"/deals/{selected.deal_id}/documents/{document.kind}/pdf",
            cls="btn admin-icon-btn admin-icon-btn-only admin-install-btn",
            aria_label="Download PDF",
            title="Download PDF",
        )
    )

    actions.append(
        Form(
            Input(type="hidden", name="deal_id", value=selected.deal_id),
            Input(type="hidden", name="document_id", value=document.document_id),
            Button(
                Icon("trash"),
                type="submit",
                cls="btn admin-danger-btn admin-icon-btn admin-icon-btn-only",
                aria_label=f"Delete {document.kind} {document.document_number}",
                title="Delete document",
            ),
            action="/deals/documents/delete",
            method="post",
            hx_post="/deals/documents/delete",
            hx_target=f"#doc-status-{document.document_id}",
            hx_swap="innerHTML",
            hx_confirm="Permanently delete this document? This will not delete the project workspace.",
            cls="d-inline-flex ms-auto",
        )
    )

    if document.status in {"accepted", "rejected", "paid"}:
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                loading_action_button(
                    Icon("arrow-counterclockwise"),
                    endpoint="/admin/document/reset",
                    target=f"#doc-status-{document.document_id}",
                    button_cls="btn admin-icon-btn admin-icon-btn-only btn-outline-warning",
                    aria_label="Reset document to sent",
                    title="Reset document to sent",
                ),
                action="/admin/document/reset",
                method="post",
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

    details = Div(
        Div(
            Span(document.document_number, cls="admin-project-meta"),
            Span(f"Updated {document.updated_at}" if document.updated_at else "", cls="admin-project-meta"),
            cls="d-flex flex-wrap align-items-center gap-2 mb-2",
        ),
        Div(
            Div(Span("Total", cls="admin-field-label"), Strong(_money(document.total_amount))),
            Div(Span("Valid Until", cls="admin-field-label"), Strong(document.valid_until or "Not set")),
            Div(Span("Due Date", cls="admin-field-label"), Strong(document.due_date or "Not set")),
            cls="admin-field-grid deal-document-meta-grid",
        ),
        line_items_section,
        Div(*actions, cls="admin-action-row deal-document-actions mt-3"),
        Div(id=f"doc-status-{document.document_id}", cls="mt-2"),
        _response_timeline(document.document_id),
        P(f"Last viewed: {view_time}" if view_time else "", cls="admin-project-meta mt-2 mb-0"),
        next_step or "",
    )
    header_title = f"{document.kind.title()} | {document.title} | {document.status.replace('_', ' ').title()} | {_money(document.total_amount)}"
    return AccordionItem(
        details,
        title=header_title,
        expanded=False,
        header_cls="deal-document-accordion-header",
        button_cls="deal-document-accordion-toggle",
        body_cls="deal-document-accordion-body",
        cls="deal-document-accordion-item",
        data_document_kind=document.kind,
        data_document_status=document.status,
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
                        button_cls="btn admin-icon-btn admin-module-btn",
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
                P(
                    f"AI will use the accepted {source_doc.kind} to draft a {next_label}. Select a package:",
                    cls="admin-module-copy mb-2",
                ),
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
                P(
                    f"AI will use the accepted {source_doc.kind} to draft a {next_label} for {_money(amount)}.",
                    cls="admin-module-copy mb-2",
                ),
                Div(
                    Form(
                        Input(type="hidden", name="from_kind", value=source_doc.kind),
                        Input(type="hidden", name="to_kind", value=next_kind),
                        loading_action_button(
                            f"\u2728 AI Generate {next_label}",
                            endpoint=f"/deals/{selected.deal_id}/generate",
                            target="#generate-result",
                            button_cls="btn admin-icon-btn admin-module-btn",
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


def documents_tab(selected: AdminDeal, *, newest_first: bool = False) -> Div:
    """Documents tab — each document with timeline and generate-next CTAs."""
    docs = selected.documents
    if not docs:
        return EmptyState(
            icon="file-earmark-text",
            title="No documents yet",
            description="Create the first document for this deal from the Edit tab or use Quick Document.",
            cls="py-4",
        )

    # Keep workflow pages chronological while allowing collection previews to show recent work first.
    sorted_docs = sorted(docs, key=lambda d: d.updated_at, reverse=newest_first)

    cards = []
    for doc in sorted_docs:
        cta = _generate_next_cta(selected, doc)
        cards.append(_document_card_detail(selected, doc, next_step=cta))

    return Accordion(
        *cards,
        accordion_id=f"deal-documents-{selected.deal_id}",
        always_open=True,
        flush=True,
        cls="deal-documents-accordion",
    )


def deal_documents_page(*, deal_id: str = "", view: str = "documents") -> tuple:
    """Deal documents tab page layout."""
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
            title=f"{settings.app_name} | {selected.project_title} - Documents",
            description=f"Documents for {selected.project_title}",
            url=f"{settings.base_url}/deals/{deal_id}",
        ),
        *page_frame(
            back_link,
            Div(
                Div(
                    H2(selected.project_title, cls="admin-section-title mb-1"),
                    Div(
                        Span(selected.client_name, cls="admin-project-meta"),
                        Badge(
                            selected.stage.replace("_", " ").title(),
                            cls=f"bg-{_status_color(selected.stage)} bg-opacity-10 text-{_status_color(selected.stage)} ms-2",
                        ),
                        Span(_money(selected.amount_ngn), cls="admin-project-meta ms-2"),
                        cls="d-flex align-items-center gap-2 flex-wrap",
                    ),
                ),
                _workflow_pipeline(selected),
                cls="mb-4",
            ),
            nav_pills,
            Row(
                Col(_deal_snapshot_card(selected), span=12, lg=4),
                Col(
                    Card(
                        documents_tab(selected),
                        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
                    ),
                    span=12, lg=8, cls="mt-4 mt-lg-0",
                ),
                cls="g-4",
            ),
            current="/deals",
            title=selected.project_title,
        ),
    )
