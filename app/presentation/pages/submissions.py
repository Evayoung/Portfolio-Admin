"""Submissions workspace for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.infrastructure.submission_repository import (
    get_submission,
    get_submission_workspace_summary,
    list_submissions,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.pages.dashboard import SectionWrap
from app.presentation.page_helpers import loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def submission_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(label, href=href, cls=f"admin-filter-chip{' active' if active else ''}")


def _status_options(kind: str) -> tuple[tuple[str, str], ...]:
    if kind == "booking":
        return (
            ("new", "New"),
            ("reviewing", "Reviewing"),
            ("scheduled", "Scheduled"),
            ("closed", "Closed"),
            ("spam", "Spam"),
        )
    return (
        ("new", "New"),
        ("in_progress", "In Progress"),
        ("closed", "Closed"),
        ("spam", "Spam"),
    )


def _submission_card(item, *, selected: bool, kind: str, status: str, search: str) -> Card:
    href = f"/submissions?entry_id={item.entry_id}&kind={kind}&status={status}&search={search}"
    status_tone = {
        "new": "warning",
        "in_progress": "info",
        "reviewing": "info",
        "scheduled": "success",
        "closed": "secondary",
        "spam": "danger",
    }.get(item.status, "secondary")
    return Card(
        A(
            Div(
                Div(
                    Div(
                        Span(item.kind.title(), cls="admin-project-category"),
                        Badge(item.status.replace("_", " ").title(), cls=f"text-bg-{status_tone} admin-project-flag"),
                        cls="d-flex align-items-center gap-2 flex-wrap",
                    ),
                    Span(item.created_at or "Awaiting timestamp", cls="admin-project-meta"),
                    cls="d-flex justify-content-between align-items-start gap-2",
                ),
                H3(item.name or "Unnamed inquiry", cls="admin-project-title"),
                P(item.message[:160] + ("..." if len(item.message) > 160 else ""), cls="admin-project-copy"),
                Div(
                    Span(item.email, cls="admin-project-meta"),
                    Span(item.service or item.subject or "General inquiry", cls="admin-project-meta"),
                    cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
                ),
                cls="admin-project-card-body",
            ),
            href=href,
            cls=f"admin-project-card-link{' is-selected' if selected else ''}",
        ),
        cls=f"admin-surface-card admin-project-card{' is-new-item' if item.status == 'new' else ''}",
    )


def _notes_field(value: str = "") -> Div:
    return textarea_field(
        "Internal Notes",
        "notes",
        value,
        rows=5,
        placeholder="Add follow-up notes, decisions, or next steps",
    )


def _editor_form(selected, *, kind: str, status: str, search: str) -> Form:
    selected_kind = selected.kind if selected else "contact"
    options = _status_options(selected_kind)
    selected_status = selected.status if selected else options[0][0]
    return Form(
        Input(type="hidden", name="entry_id", value=selected.entry_id if selected else ""),
        Input(type="hidden", name="kind", value=selected_kind),
        Input(type="hidden", name="current_kind", value=kind),
        Input(type="hidden", name="current_status", value=status),
        Input(type="hidden", name="current_search", value=search),
        Div(
            Label("Workflow Status", cls="admin-form-label"),
            toggle_pill_group("status", list(options), selected_value=selected_status),
            cls="admin-form-group",
        ),
        _notes_field(selected.notes if selected else ""),
        Div(
            loading_action_button("Update Submission", endpoint="/submissions/save", target="#submission-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable updates",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="submission-save-result", cls="mt-3"),
        action="/submissions/save",
        method="post",
        hx_post="/submissions/save",
        hx_target="#submission-save-result",
        hx_swap="innerHTML",
        cls="admin-submission-form",
    )


def submissions_workspace_page(*, entry_id: str = "", kind: str = "all", status: str = "all", search: str = "") -> tuple:
    items = list_submissions(kind=kind, status=status, search=search)
    selected = get_submission(entry_id, kind=kind) or (items[0] if items else None)
    summary = get_submission_workspace_summary()

    kind_links = Div(
        _filter_link("All", f"/submissions?kind=all&status={status}&search={search}", active=kind == "all"),
        _filter_link("Contact", f"/submissions?kind=contact&status={status}&search={search}", active=kind == "contact"),
        _filter_link("Booking", f"/submissions?kind=booking&status={status}&search={search}", active=kind == "booking"),
        cls="admin-filter-row",
    )
    status_links = Div(
        _filter_link("Any Status", f"/submissions?kind={kind}&status=all&search={search}", active=status == "all"),
        _filter_link("Open", f"/submissions?kind={kind}&status=new&search={search}", active=status == "new"),
        _filter_link("Active", f"/submissions?kind={kind}&status=in_progress&search={search}", active=status == "in_progress"),
        _filter_link("Reviewing", f"/submissions?kind={kind}&status=reviewing&search={search}", active=status == "reviewing"),
        cls="admin-filter-row mt-3",
    )
    search_form = search_filter_bar(
        endpoint="/submissions",
        placeholder="Search sender, message, email, or status",
        search_value=search,
        hidden_fields={
            "kind": kind,
            "status": status,
        },
        form_cls="admin-search-form admin-filter-bar mt-3",
    )

    list_panel = Card(
        Div(
            Div(
                Div(
                    H2("Inbox Records", cls="admin-section-title"),
                    Span(str(summary.new_items), cls="admin-unread-badge") if summary.new_items else "",
                    cls="admin-inbox-header",
                ),
                P(summary.note, cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            kind_links,
            status_links,
            search_form,
            Div(
                *[
                    _submission_card(
                        item,
                        selected=bool(selected and item.entry_id == selected.entry_id),
                        kind=kind,
                        status=status,
                        search=search,
                    )
                    for item in items
                ],
                cls="admin-project-list mt-4",
            )
            if items
            else EmptyState(
                icon="inbox",
                title="No submission matches this view",
                description=summary.note if summary.total == 0 else "Try a different filter or search term.",
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    detail_panel = (
        Card(
            Div(
                Div(
                    Div(
                        Span("Selected record", cls="admin-kicker"),
                        H2(selected.name or "Inbox record", cls="admin-section-title mb-2"),
                        P(selected.message, cls="admin-module-copy mb-0 admin-message-block"),
                        cls="admin-detail-copy",
                    ),
                    Div(
                        Badge(summary.source, cls="text-bg-secondary admin-metric-delta"),
                        Badge("Live sync on" if service_role_is_configured() else "Setup needed", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                        cls="d-flex flex-wrap gap-2 mt-3 mt-lg-0",
                    ),
                    cls="d-flex flex-column flex-lg-row justify-content-between gap-3",
                ),
                Div(
                    Row(
                        Col(
                            Div(
                                H3("Sender Snapshot", cls="admin-subsection-title"),
                                Div(
                                    Div(Span("Type", cls="admin-field-label"), Strong(selected.kind.title())),
                                    Div(Span("Email", cls="admin-field-label"), Strong(selected.email or "Not provided")),
                                    Div(Span("Phone / WhatsApp", cls="admin-field-label"), Strong(selected.phone or "Not provided")),
                                    Div(Span("Created", cls="admin-field-label"), Strong(selected.created_at or "Unknown")),
                                    cls="admin-field-grid",
                                ),
                                cls="admin-detail-block",
                            ),
                            span=12,
                            md=6,
                        ),
                        Col(
                            Div(
                                H3("Inquiry Metadata", cls="admin-subsection-title"),
                                Div(
                                    Div(Span("Status", cls="admin-field-label"), Strong(selected.status.replace("_", " ").title())),
                                    Div(Span("Subject", cls="admin-field-label"), Strong(selected.subject or "General inquiry")),
                                    Div(Span("Service", cls="admin-field-label"), Strong(selected.service or "Not specified")),
                                    Div(Span("Budget / Timeline", cls="admin-field-label"), Strong(" / ".join(part for part in (selected.budget, selected.timeline) if part) or "Not specified")),
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
                    H3("Inbox Workflow", cls="admin-subsection-title"),
                    P("Use this panel to keep inquiry status, follow-up notes, and response progress in one place.", cls="admin-module-copy"),
                    Div(
                        A(
                            "Convert to Deal",
                            href=f"/deals?from_submission={selected.entry_id}&from_kind={selected.kind}",
                            cls="btn admin-install-btn",
                        ),
                        P("Use this when a serious inquiry is ready to move into proposal, quote, or invoice planning.", cls="admin-module-copy mt-2 mb-0"),
                        cls="admin-detail-block mb-4",
                    ),
                    _editor_form(selected, kind=kind, status=status, search=search),
                    cls="admin-detail-block mt-4",
                ),
                cls="admin-panel-stack",
            ),
            cls="admin-surface-card h-100",
        )
        if selected
        else Card(
            EmptyState(
                icon="inbox",
                title="No submission selected",
                description=summary.note,
                cls="py-5",
            ),
            cls="admin-surface-card h-100",
        )
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Submissions",
            description="Submissions workspace for reviewing contact inquiries and booking requests.",
            url=f"{settings.base_url}/submissions",
        ),
        *page_frame(
            Row(
                summary_card("Inbox Total", str(summary.total), "Combined contact and booking records currently available."),
                summary_card("Open Items", str(summary.new_items), "New and active records that still need attention."),
                summary_card("Booking Requests", str(summary.booking_items), f"Live source: {summary.source}."),
                cls="g-4",
            ),
            SectionWrap(
                "Submissions Workspace",
                Row(
                    Col(list_panel, span=12, lg=5, id="submissions-list-panel"),
                    Col(
                        Button(
                            "Show Detail Panel ↓",
                            type="button",
                            cls="admin-panel-toggle-btn",
                            data_panel_toggle="submissions-detail-panel",
                            id="submissions-panel-toggle",
                        ),
                        detail_panel,
                        id="submissions-detail-panel",
                        span=12,
                        lg=7,
                        cls="mt-4 mt-lg-0",
                    ),
                    cls="g-4",
                ),
            ),
            current="/submissions",
            title="Submissions",
        ),
    )
