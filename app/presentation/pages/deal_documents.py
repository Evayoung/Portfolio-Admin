"""Deal detail documents tab module — document list, status updates, response timelines, line items, and generate-next CTAs."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H4, Input, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Row, SEO, Spinner

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


def _document_card_detail(selected: AdminDeal, document) -> Div:
    """Render a document card for the detail page with full actions and response timeline."""
    status_color = _status_color(document.status)
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
                    "Mark Sent",
                    endpoint="/deals/documents/update",
                    target=f"#doc-status-{document.document_id}",
                    button_cls="btn admin-icon-btn admin-install-btn",
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
                    "Mark Accepted",
                    endpoint="/deals/documents/update",
                    target=f"#doc-status-{document.document_id}",
                    button_cls="btn admin-icon-btn btn-outline-success",
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
                Icon("clipboard", cls="me-1"),
                "Copy Link",
                href="#",
                cls="btn admin-icon-btn admin-install-btn",
                **{"data_copy_target": doc_url, "data_copy_label": "Copy Link"},
            )
        )
        actions.append(
            A(
                Icon("box-arrow-up-right", cls="me-1"),
                "Open Client Link",
                href=f"/documents/{document.public_token}",
                cls="btn admin-icon-btn admin-module-btn",
                target="_blank",
            )
        )
        actions.append(
            Form(
                Input(type="hidden", name="deal_id", value=selected.deal_id),
                Input(type="hidden", name="document_id", value=document.document_id),
                Input(type="hidden", name="document_kind", value=document.kind),
                Input(type="hidden", name="action", value="resend"),
                Button(Icon("send", cls="me-1"), "Resend", type="submit", cls="btn admin-icon-btn admin-install-btn"),
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
                Button(Icon("arrow-repeat", cls="me-1"), "Regenerate", type="submit", cls="btn admin-icon-btn admin-install-btn"),
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
                Button(Icon("slash-circle", cls="me-1"), "Revoke", type="submit", cls="btn admin-icon-btn btn-outline-warning"),
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
                Button(Icon("arrow-repeat", cls="me-1"), "Generate Link", type="submit", cls="btn admin-icon-btn admin-module-btn"),
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
            Icon("download", cls="me-1"),
            "Download PDF",
            href=f"/deals/{selected.deal_id}/documents/{document.kind}/pdf",
            cls="btn admin-icon-btn admin-install-btn",
        )
    )

    actions.append(
        Form(
            Input(type="hidden", name="deal_id", value=selected.deal_id),
            Input(type="hidden", name="document_id", value=document.document_id),
            Button(
                Icon("trash"),
                type="submit",
                cls="btn admin-danger-btn",
                aria_label=f"Delete {document.kind} {document.document_number}",
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
                    "Reset to Sent",
                    endpoint="/admin/document/reset",
                    target=f"#doc-status-{document.document_id}",
                    button_cls="btn admin-icon-btn btn-outline-warning",
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
                        _documents_tab(selected),
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
