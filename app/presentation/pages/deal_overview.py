"""Deal detail overview tab module — focused on overview metrics, client info, project details, and narrative sections."""

from __future__ import annotations

import json
from fasthtml.common import A, Div, H2, H3, H4, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Row, SEO, Spinner

from app.config import settings
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import get_deal_with_documents
from app.presentation.pages.deal_helpers import (
    _deal_snapshot_card,
    _group_packages,
    _money,
    _package_totals,
    _status_color,
    _workflow_pipeline,
)
from app.presentation.shell import page_frame


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
                        Div(
                            Span("Stage", cls="admin-field-label"),
                            Badge(
                                selected.stage.replace("_", " ").title(),
                                cls=f"bg-{_status_color(selected.stage)} bg-opacity-10 text-{_status_color(selected.stage)}",
                            ),
                        ),
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
        # Sections content from sections_json (proposal/quote body)
        *(
            [
                Card(
                    H3("Document Sections", cls="admin-subsection-title"),
                    *[
                        Div(
                            H4(s.get("title", ""), cls="admin-project-title mb-1"),
                            P(s.get("content", ""), cls="admin-module-copy mb-3"),
                        )
                        for s in sorted(
                            json.loads(selected.sections_json),
                            key=lambda x: x.get("order", 0),
                        )
                        if s.get("title") or s.get("content")
                    ],
                    cls="admin-detail-block mt-4",
                ),
            ]
            if selected.sections_json and selected.sections_json.strip() not in ("", "[]")
            else []
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
                        _overview_tab(selected),
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
