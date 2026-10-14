"""Shared helper functions, formatters, and reusable UI components for deal views."""

from __future__ import annotations

import re
from fasthtml.common import Button, Div, P, Span, Textarea

from app.domain.models import AdminDeal
from app.presentation.page_helpers import status_alert


def deal_generate_result_fragment(
    title: str, message: str, tone: str = "info", draft: str = "", draft_kind: str = "proposal"
) -> Div:
    """Fragment for showing AI draft results or generation feedback."""
    apply_panel = Div()
    if draft:
        apply_panel = Div(
            P("AI-generated draft:", cls="admin-module-copy mt-3 mb-2"),
            Textarea(
                draft,
                rows=12,
                readonly=True,
                cls="form-control admin-form-control admin-form-textarea",
                id="ai-draft-content",
            ),
            Div(
                Button(
                    "Copy Draft",
                    type="button",
                    cls="btn admin-icon-btn admin-module-btn",
                    hx_onclick=(
                        "navigator.clipboard.writeText(document.getElementById('ai-draft-content').value)"
                        ".then(() => this.textContent = 'Copied!')"
                    ),
                ),
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
    items = _parse_line_items(raw)
    groups: dict[str, list[tuple[str, str, str, int]]] = {}
    for label, detail, qty, amount in items:
        group_key = None
        for prefix in ("Package", "Option"):
            match = re.match(rf"^({prefix}\s+\w+)\s*[-:\s]", label, re.IGNORECASE)
            if match:
                group_key = match.group(1).strip()
                label = label[match.end() :].strip()
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
    """Compact, non-interactive progress indicator for the deal lifecycle."""
    stages = [
        ("lead", "Lead"),
        ("proposal", "Proposal"),
        ("quoted", "Quotation"),
        ("invoiced", "Invoice"),
        ("paid", "Paid"),
        ("delivered", "Delivered"),
    ]
    current_stage = selected.stage
    current_idx = next((i for i, (s, _) in enumerate(stages) if s == current_stage), 0)

    items = []
    for i, (stage, label) in enumerate(stages):
        is_completed = i < current_idx
        is_active = i == current_idx
        status_cls = "completed" if is_completed else ("active" if is_active else "upcoming")
        items.append(
            Span(
                Span(label, cls="deal-pipeline-label"),
                cls=f"deal-pipeline-item {status_cls}",
                aria_current="step" if is_active else None,
                aria_label=f"{label}: {'current stage' if is_active else 'complete' if is_completed else 'upcoming'}",
            )
        )
        if i < len(stages) - 1:
            items.append(Span(cls="deal-pipeline-connector"))

    return Div(*items, cls="deal-workflow-pipeline")
