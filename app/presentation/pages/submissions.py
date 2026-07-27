"""Submissions workspace for Neo Admin — split into list workspace and dedicated detail views."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, H4, Input, Label, P, Span, Strong
from faststrap import Badge, Card, Col, ConfirmDialog, EmptyState, Fx, Icon, Modal, Row, SEO, Spinner, StatusBadge, Timeline, TimelineItem, ToggleGroup

from app.config import settings
from app.infrastructure.submission_repository import (
    get_submission,
    get_submission_workspace_summary,
    list_submissions,
    update_submission,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def submission_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _status_tone(status: str) -> str:
    return {
        "new": "warning",
        "in_progress": "info",
        "reviewing": "info",
        "scheduled": "success",
        "closed": "secondary",
        "spam": "danger",
    }.get(status, "secondary")


def _status_options(kind: str) -> tuple[tuple[str, str, str, str], ...]:
    if kind == "booking":
        return (
            ("new", "New", "dot", "warning"),
            ("reviewing", "Reviewing", "clock-history", "info"),
            ("scheduled", "Scheduled", "calendar-check", "success"),
            ("closed", "Closed", "check2-circle", "secondary"),
            ("spam", "Spam", "slash-circle", "danger"),
        )
    return (
        ("new", "New", "dot", "warning"),
        ("in_progress", "In Progress", "clock-history", "info"),
        ("closed", "Closed", "check2-circle", "secondary"),
        ("spam", "Spam", "slash-circle", "danger"),
    )



def _submission_card(item, *, kind: str, status: str, search: str) -> Card:
    """Render a single inbox record card with Pattern 3 HTMX loading spinner, Quick Preview, and Delete action."""
    detail_href = f"/submissions/detail?entry_id={item.entry_id}&kind={item.kind}&status={status}&search={search}"
    card_id = f"sub-card-{item.entry_id}"
    status_tone = _status_tone(item.status)

    return Card(
        Div(
            A(
                Div(
                    Div(
                        Div(
                            StatusBadge(item.kind.title(), status="info", pill=True, cls="admin-badge-sm me-2"),
                            StatusBadge(item.status.replace("_", " ").title(), status=status_tone, show_dot=True, pill=True, cls="admin-badge-sm"),
                            cls="d-flex align-items-center gap-2 flex-wrap",
                        ),
                        Span(item.created_at or "Awaiting timestamp", cls="admin-project-meta"),
                        cls="d-flex justify-content-between align-items-start gap-2",
                    ),
                    H3(
                        item.name or "Unnamed inquiry",
                        Span(cls="admin-card-loading-spinner"),
                        cls="admin-project-title d-flex justify-content-between align-items-center mt-2",
                    ),
                    P(item.message[:160] + ("..." if len(item.message) > 160 else ""), cls="admin-project-copy"),
                    Div(
                        Span(item.email, cls="admin-project-meta"),
                        Span(item.service or item.subject or "General inquiry", cls="admin-project-meta"),
                        cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
                    ),
                    cls="admin-project-card-body",
                ),
                href=detail_href,
                hx_get=detail_href,
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                hx_indicator=f"#{card_id}",
                cls="admin-project-card-link",
            ),
            Div(
                Button(
                    Icon("trash"),
                    type="button",
                    cls="btn admin-danger-btn btn-sm me-auto",
                    data_bs_toggle="modal",
                    data_bs_target=f"#delete-confirm-modal-{item.entry_id}",
                    aria_label=f"Delete submission {item.entry_id}",
                ),
                Button(
                    Icon("eye", cls="me-1"),
                    "Quick Preview",
                    type="button",
                    cls="btn admin-muted-btn btn-sm me-2",
                    data_bs_toggle="modal",
                    data_bs_target=f"#preview-modal-{item.entry_id}",
                ),
                A(
                    Icon("arrow-right", cls="me-1"),
                    "Open Detail",
                    href=detail_href,
                    hx_get=detail_href,
                    hx_target="body",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    hx_indicator=f"#{card_id}",
                    cls="btn admin-module-btn btn-sm",
                ),
                cls="d-flex justify-content-between align-items-center pt-3 border-top border-secondary border-opacity-10 mt-3",
            ),
        ),
        id=card_id,
        cls=[Fx.base, Fx.fade_in, f"admin-surface-card admin-project-card h-100{' admin-is-new-item' if item.status == 'new' else ''}"],
    )


def _delete_confirm_modal(item, *, kind: str, status: str, search: str) -> ConfirmDialog:
    """Render a root-level Faststrap confirm dialog for deleting a submission record."""
    delete_url = f"/submissions/delete?entry_id={item.entry_id}&kind={item.kind}&current_kind={kind}&current_status={status}&current_search={search}"
    return ConfirmDialog(
        f"Are you sure you want to delete the submission record from '{item.name or 'Unnamed inquiry'}' ({item.email})? This action cannot be undone.",
        title="Delete Submission Record?",
        confirm_text="Delete Submission",
        cancel_text="Cancel",
        variant="danger",
        dialog_id=f"delete-confirm-modal-{item.entry_id}",
        hx_confirm_method="delete",
        hx_confirm_url=delete_url,
        hx_target="#submissions-list-panel",
        hx_swap="outerHTML",
    )



def _quick_preview_modal(item) -> Modal:
    """Render a root-level Faststrap preview modal for a submission record."""
    status_tone = _status_tone(item.status)
    detail_href = f"/submissions/detail?entry_id={item.entry_id}&kind={item.kind}"

    return Modal(
        Div(
            Div(
                Div(
                    StatusBadge(item.kind.title(), status="info", pill=True, cls="admin-badge-sm me-2"),
                    StatusBadge(item.status.replace("_", " ").title(), status=status_tone, show_dot=True, pill=True, cls="admin-badge-sm"),
                    cls="d-flex align-items-center mb-3",
                ),
                H3(item.name or "Unnamed inquiry", cls="admin-section-title mb-1"),
                P(f"Submitted on {item.created_at or 'Unknown timestamp'}", cls="small text-muted mb-3"),
                cls="mb-3",
            ),
            Div(
                H4("Sender & Contact Details", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("Email", cls="admin-field-label"), Strong(item.email or "Not provided")),
                    Div(Span("Phone / WhatsApp", cls="admin-field-label"), Strong(item.phone or "Not provided")),
                    Div(Span("Subject / Service", cls="admin-field-label"), Strong(item.subject or item.service or "General inquiry")),
                    Div(Span("Budget / Timeline", cls="admin-field-label"), Strong(" / ".join(p for p in (item.budget, item.timeline) if p) or "Not specified")),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
                cls="mb-4",
            ),
            Div(
                H4("Inquiry Message", cls="admin-subsection-title mb-2"),
                Div(item.message, cls="admin-message-block admin-detail-block p-3"),
                cls="mb-4",
            ),
            Div(
                A(
                    Icon("arrow-right", cls="me-2"),
                    "Open Full Detail Page",
                    href=detail_href,
                    hx_get=detail_href,
                    hx_target="body",
                    hx_swap="innerHTML",
                    hx_push_url="true",
                    cls="btn admin-module-btn me-2",
                    data_bs_dismiss="modal",
                ),
                Button("Close", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
                cls="d-flex justify-content-end gap-2 mt-4",
            ),
        ),
        modal_id=f"preview-modal-{item.entry_id}",
        title=f"Preview: {item.name or 'Inquiry'}",
        size="lg",
        scrollable=True,
        centered=True,
    )


def _notes_field(value: str = "") -> Div:
    return textarea_field(
        "Internal Notes",
        "notes",
        value,
        rows=5,
        placeholder="Add follow-up notes, decisions, or next steps",
    )


def _notes_history_timeline(notes_text: str) -> Div:
    """Render a Faststrap Timeline showing history of internal notes and status updates."""
    clean_notes = (notes_text or "").strip()
    if not clean_notes:
        return Div(
            EmptyState(
                icon="journal-text",
                title="No internal notes recorded yet",
                description="Use the form below to post workflow updates, decision notes, or next steps.",
                cls="py-4 border rounded border-secondary border-opacity-10 bg-black bg-opacity-10",
            ),
            cls="admin-detail-block p-3",
        )

    entries = [line.strip() for line in clean_notes.split("\n") if line.strip()]
    timeline_items = []

    for index, entry in enumerate(entries):
        is_latest = (index == 0)
        time_str = "Note History Entry"
        desc = entry
        if entry.startswith("[") and "]" in entry:
            parts = entry.split("]", 1)
            time_str = parts[0].lstrip("[")
            desc = parts[1].strip()

        timeline_items.append(
            TimelineItem(
                title=f"Note Entry #{len(entries) - index}",
                description=desc,
                time=time_str,
                icon="chat-square-text",
                variant="info" if is_latest else "secondary",
                active=is_latest,
            )
        )

    return Div(
        Timeline(*timeline_items, density="compact"),
        cls="admin-detail-block p-3",
    )


def _editor_form(selected, *, kind: str, status: str, search: str) -> Form:
    selected_kind = selected.kind if selected else "contact"
    options = _status_options(selected_kind)
    selected_status = selected.status if selected else options[0][0]

    status_buttons = []
    values = []
    active_idx = 0
    for idx, (val, label, icon, tone) in enumerate(options):
        values.append(val)
        is_active = (val == selected_status)
        if is_active:
            active_idx = idx

        status_buttons.append(
            Button(
                Icon(icon, cls="me-1"),
                label,
                type="button",
                variant="link",
                cls=f"admin-status-pill admin-status-pill-{tone}{' active' if is_active else ''}",
            )
        )

    status_selector = ToggleGroup(
        *status_buttons,
        name="status",
        values=values,
        active_index=active_idx,
        cls="admin-filter-toggle-group flex-wrap",
    )

    return Form(
        Input(type="hidden", name="entry_id", value=selected.entry_id if selected else ""),
        Input(type="hidden", name="kind", value=selected_kind),
        Input(type="hidden", name="current_kind", value=kind),
        Input(type="hidden", name="current_status", value=status),
        Input(type="hidden", name="current_search", value=search),
        Div(
            Label("Workflow Status", cls="admin-form-label mb-2 d-block"),
            status_selector,
            cls="admin-form-group mb-4",
        ),
        _notes_field(selected.notes if selected else ""),
        Div(
            loading_action_button("Update Submission & Save Notes", endpoint="/submissions/save", target="#submission-save-result"),
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



def _filter_toggle_buttons(kind: str, status: str, search: str) -> Row:
    """Render Faststrap segmented toggle buttons for Kind and Status filtering in a horizontal row."""
    kind_btns = [
        A("All", href=f"/submissions?kind=all&status={status}&search={search}", cls=f"btn admin-toggle-btn{' active' if kind == 'all' else ''}"),
        A("Contact", href=f"/submissions?kind=contact&status={status}&search={search}", cls=f"btn admin-toggle-btn{' active' if kind == 'contact' else ''}"),
        A("Booking", href=f"/submissions?kind=booking&status={status}&search={search}", cls=f"btn admin-toggle-btn{' active' if kind == 'booking' else ''}"),
    ]
    status_btns = [
        A("Any Status", href=f"/submissions?kind={kind}&status=all&search={search}", cls=f"btn admin-toggle-btn{' active' if status == 'all' else ''}"),
        A("Open", href=f"/submissions?kind={kind}&status=new&search={search}", cls=f"btn admin-toggle-btn{' active' if status == 'new' else ''}"),
        A("Active", href=f"/submissions?kind={kind}&status=in_progress&search={search}", cls=f"btn admin-toggle-btn{' active' if status == 'in_progress' else ''}"),
        A("Reviewing", href=f"/submissions?kind={kind}&status=reviewing&search={search}", cls=f"btn admin-toggle-btn{' active' if status == 'reviewing' else ''}"),
    ]
    return Row(
        Col(
            Div(Span("Filter Kind:", cls="admin-field-label mb-1 d-block"), Div(*kind_btns, cls="admin-filter-toggle-group flex-wrap")),
            span=12,
            lg=6,
        ),
        Col(
            Div(Span("Filter Status:", cls="admin-field-label mb-1 d-block"), Div(*status_btns, cls="admin-filter-toggle-group flex-wrap")),
            span=12,
            lg=6,
            cls="mt-3 mt-lg-0",
        ),
        cls="g-3 mb-3",
    )


def _submissions_list_panel(items, *, kind: str, status: str, search: str, summary) -> Card:
    """Render the submissions list panel — reusable for full page and live search."""
    search_form = search_filter_bar(
        endpoint="/submissions/search",
        placeholder="Search sender, message, email, or status (live)",
        search_value=search,
        hidden_fields={
            "kind": kind,
            "status": status,
        },
        form_cls="admin-search-form admin-filter-bar mb-4",
        hx_target="#submissions-list-panel",
        hx_swap="outerHTML",
        mode="auto",
    )
    return Card(
        Div(
            Div(
                Div(
                    H2("Inbox Records", cls="admin-section-title"),
                    Span(str(summary.new_items), cls="admin-unread-badge") if summary.new_items else "",
                    cls="admin-inbox-header",
                ),
                P(summary.note, cls="admin-module-copy mb-3"),
                cls="mb-3",
            ),
            _filter_toggle_buttons(kind, status, search),
            search_form,
            Row(
                *[
                    Col(
                        _submission_card(
                            item,
                            kind=kind,
                            status=status,
                            search=search,
                        ),
                        span=12,
                        md=6,
                    )
                    for item in items
                ],
                cls="g-4 mt-2",
            )
            if items
            else EmptyState(
                icon="inbox",
                title="Inbox is empty" if summary.total == 0 else "No submission matches this view",
                description="Submissions will appear here when visitors use the contact or booking form on your public site." if summary.total == 0 else "Try a different filter or search term.",
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
        id="submissions-list-panel",
        cls="admin-surface-card h-100",
    )


def submissions_workspace_page(*, kind: str = "all", status: str = "all", search: str = "") -> tuple:
    """Submissions Workspace List Page (GET /submissions)."""
    items = list_submissions(kind=kind, status=status, search=search)
    summary = get_submission_workspace_summary()

    list_panel = _submissions_list_panel(items, kind=kind, status=status, search=search, summary=summary)
    preview_modals = [_quick_preview_modal(item) for item in items]
    delete_modals = [_delete_confirm_modal(item, kind=kind, status=status, search=search) for item in items]

    return (
        *SEO(
            title=f"{settings.app_name} | Submissions Workspace",
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
                list_panel,
            ),
            *preview_modals,
            *delete_modals,
            current="/submissions",
            title="Submissions Workspace",
        ),
    )


def submission_detail_page(*, entry_id: str = "", kind: str = "all", status: str = "all", search: str = "") -> tuple:
    """Dedicated Submission Record Detail Page (GET /submissions/detail)."""
    items = list_submissions(kind=kind, status=status, search=search)
    selected = get_submission(entry_id, kind=kind) or (items[0] if items else None)

    # Auto Mark-As-Read: remove 'new' status tag when record is opened/viewed
    if selected and selected.status == "new":
        next_status = "reviewing" if selected.kind == "booking" else "in_progress"
        update_submission(entry_id=selected.entry_id, kind=selected.kind, status=next_status, notes=selected.notes)
        selected = get_submission(selected.entry_id, kind=selected.kind) or selected

    summary = get_submission_workspace_summary()

    # Pattern 2 — HTMX Back-link with Faststrap Spinner
    back_link = A(
        Icon("arrow-left", cls="me-2"),
        "Back to Submissions Workspace",
        Spinner(size="sm", cls="admin-back-spinner ms-2"),
        href=f"/submissions?kind={kind}&status={status}&search={search}",
        hx_get=f"/submissions?kind={kind}&status={status}&search={search}",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        hx_indicator="#submission-back-link",
        id="submission-back-link",
        cls="admin-back-link mb-3",
    )

    if not selected:
        return (
            *SEO(
                title=f"{settings.app_name} | Submission Detail",
                description="View submission details.",
                url=f"{settings.base_url}/submissions/detail",
            ),
            *page_frame(
                back_link,
                Card(
                    EmptyState(
                        icon="inbox",
                        title="No submission found",
                        description="The requested submission record could not be found.",
                        cls="py-5",
                    ),
                    cls="admin-surface-card h-100",
                ),
                current="/submissions",
                title="Submission Detail",
            ),
        )

    status_tone = _status_tone(selected.status)
    convert_modal_id = f"convert-modal-{selected.entry_id}"

    # Left Column (lg=5) — Sender Snapshot Hero Card (Pattern 7)
    snapshot_card = Card(
        Div(
            Div(
                StatusBadge(selected.kind.title(), status="info", pill=True, cls="admin-badge-sm me-2"),
                StatusBadge(selected.status.replace("_", " ").title(), status=status_tone, show_dot=True, pill=True, cls="admin-badge-sm"),
                cls="d-flex align-items-center mb-3",
            ),
            H3(selected.name or "Unnamed inquiry", cls="admin-section-title mb-1"),
            P(f"Submitted on {selected.created_at or 'Unknown timestamp'}", cls="admin-module-copy text-muted mb-4"),

            # Contact Information Block
            Div(
                H4("Sender Contact", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("Email", cls="admin-field-label"), Strong(selected.email or "Not provided")),
                    Div(Span("Phone / WhatsApp", cls="admin-field-label"), Strong(selected.phone or "Not provided")),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
                cls="mb-4",
            ),

            # Inquiry Details Block
            Div(
                H4("Inquiry Specs", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("Subject", cls="admin-field-label"), Strong(selected.subject or "General inquiry")),
                    Div(Span("Service", cls="admin-field-label"), Strong(selected.service or "Not specified")),
                    Div(Span("Budget / Timeline", cls="admin-field-label"), Strong(" / ".join(p for p in (selected.budget, selected.timeline) if p) or "Not specified")),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
                cls="mb-4",
            ),

            # System Sync & Source Block
            Div(
                H4("Record Metadata", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("Source", cls="admin-field-label"), Strong(summary.source)),
                    Div(
                        Span("Sync Status", cls="admin-field-label"),
                        StatusBadge(
                            "Live sync on" if service_role_is_configured() else "Setup needed",
                            status="success" if service_role_is_configured() else "warning",
                            show_dot=True,
                            pill=True,
                            cls="admin-badge-sm ms-2",
                        ),
                    ),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
            ),
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    # Right Column (lg=7) — Message Block & Workflow Form Panel
    detail_panel = Card(
        Div(
            H3("Inquiry Message", cls="admin-subsection-title mb-3"),
            Div(selected.message, cls="admin-message-block admin-detail-block p-3 mb-4"),

            # Deal Conversion Callout
            Div(
                H3("Workflow Actions", cls="admin-subsection-title mb-2"),
                Div(
                    Button(
                        Icon("briefcase", cls="me-2"),
                        "Convert to Deal",
                        type="button",
                        cls="btn admin-icon-btn admin-install-btn",
                        data_bs_toggle="modal",
                        data_bs_target=f"#{convert_modal_id}",
                    ),
                    P("Move a serious inquiry into proposal, quote, or invoice planning.", cls="admin-module-copy mt-2 mb-0"),
                    cls="admin-detail-block p-3 mb-4",
                ),
            ),

            # Activity & Notes History Timeline
            Div(
                H3("Activity & Notes History", cls="admin-subsection-title mb-3"),
                _notes_history_timeline(selected.notes if selected else ""),
                cls="mb-4",
            ),

            # Workflow Status & Notes Form
            Div(
                H3("Update Workflow & Notes", cls="admin-subsection-title mb-3"),
                _editor_form(selected, kind=kind, status=status, search=search),
            ),
            cls="admin-panel-stack",
        ),

        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    # Convert-to-Deal Confirmation Modal (Root-Level)
    convert_modal = Modal(
        Div(
            P(f"You are about to convert {selected.name or 'this inquiry'} into a deal. This will open the Deals workspace pre-filled with sender details.", cls="admin-module-copy mb-3"),
            Div(
                Div(Span("Name", cls="admin-field-label"), Strong(selected.name or "Unknown"), cls="d-flex gap-2 mb-1"),
                Div(Span("Email", cls="admin-field-label"), Strong(selected.email or "Unknown"), cls="d-flex gap-2 mb-1"),
                Div(Span("Subject", cls="admin-field-label"), Strong(selected.subject or "General inquiry"), cls="d-flex gap-2 mb-1"),
                Div(Span("Service", cls="admin-field-label"), Strong(selected.service or "Not specified"), cls="d-flex gap-2"),
                cls="admin-field-grid admin-detail-block p-3 mb-4",
            ),
            Div(
                A(
                    Icon("arrow-right", cls="me-2"),
                    "Proceed to Deals",
                    href=f"/deals?from_submission={selected.entry_id}&from_kind={selected.kind}",
                    cls="btn admin-module-btn me-2",
                ),
                Button("Cancel", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
                cls="d-flex justify-content-end gap-2 mt-4",
            ),
        ),
        modal_id=convert_modal_id,
        title="Convert to Deal",
        size="md",
        centered=True,
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Submission: {selected.name or 'Inquiry'}",
            description=f"Detail view for submission from {selected.name or 'inquiry'}.",
            url=f"{settings.base_url}/submissions/detail",
        ),
        *page_frame(
            back_link,
            Row(
                Col(snapshot_card, span=12, lg=5),
                Col(detail_panel, span=12, lg=7, cls="mt-4 mt-lg-0"),
                cls="g-4",
            ),
            convert_modal,
            current="/submissions",
            title="Submission Detail",
        ),
    )
