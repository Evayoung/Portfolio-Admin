"""Generic CRUD helpers — auto-generate list, form, and table views from TableConfig.

Pattern: iterate over config.fields to build forms, iterate over config.table_columns
to build table headers. Pagination via HTMX.
"""
from __future__ import annotations

from urllib.parse import quote

from fasthtml.common import (
    A, Button, Div, Form, H2, Input, Label, Nav, Option, P, Select, Span, Table,
    Tbody, Td, Textarea, Th, Thead, Tr, Ul, Li,
)
from faststrap import Card, EmptyState, FormGroup, Icon, Modal

from app.schema import Field, TableConfig


# ── Helpers ───────────────────────────────────────────────────────────────

def _safe_text(val) -> str:
    """Render a value as safe display text."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Yes" if val else "No"
    s = str(val)
    return s[:120] + "…" if len(s) > 120 else s


def _field_value(row: dict | None, field: Field):
    """Extract the display value for a field from a row dict."""
    if row is None:
        return field.default or ""
    return row.get(field.name, field.default or "")


def _encoded_pk(val) -> str:
    """URL-encode a primary key value for use in paths."""
    return quote(str(val), safe="")


def _field_control(field: Field, row: dict | None = None):
    """Render the appropriate HTML control for a field."""
    value = _field_value(row, field)

    if field.hidden:
        return Input(type="hidden", name=field.name, value=str(value))

    if field.kind == "textarea":
        return Textarea(
            str(value or ""),
            name=field.name,
            rows=4,
            cls="form-control",
            required=field.required,
            disabled=field.readonly,
            placeholder=field.placeholder or field.label,
        )

    if field.kind == "checkbox":
        checked = bool(value) if not isinstance(value, str) else value.lower() in ("true", "1", "yes")
        return Div(
            Input(
                type="checkbox",
                name=field.name,
                value="true",
                checked=checked,
                cls="form-check-input me-2",
                disabled=field.readonly,
            ),
            Span(field.label, cls="form-check-label"),
            cls="form-check mt-2",
        )

    if field.kind == "select":
        options = [
            Option(label, value=opt_val, selected=str(opt_val) == str(value))
            for opt_val, label in field.choices
        ] if field.choices else [Option("—", value="")]
        return Select(
            *options,
            name=field.name,
            cls="form-select",
            required=field.required,
            disabled=field.readonly,
        )

    if field.kind == "choice":
        options = [
            Option(label, value=opt_val, selected=str(opt_val) == str(value))
            for opt_val, label in field.choices
        ]
        return Select(
            *options,
            name=field.name,
            cls="form-select",
            required=field.required,
            disabled=field.readonly,
        )

    if field.kind == "image":
        preview = (
            P(str(value), cls="small text-muted mt-1 mb-0 text-truncate", style="max-width:100%;")
            if value
            else P("Paste an image URL above.", cls="small text-muted mt-1 mb-0")
        )
        return Div(
            Input(
                type="url",
                name=field.name,
                value=str(value or ""),
                placeholder="https://... or leave blank",
                cls="form-control",
                disabled=field.readonly,
            ),
            preview,
        )

    input_type = "number" if field.kind == "number" else field.kind
    return Input(
        type=input_type,
        name=field.name,
        value=str(value or ""),
        placeholder=field.placeholder or field.label,
        required=field.required,
        cls="form-control",
        disabled=field.readonly,
    )


# ── Form ──────────────────────────────────────────────────────────────────

def resource_form(
    config: TableConfig,
    row: dict | None = None,
    error: str | None = None,
) -> Div:
    """Auto-generate a create/edit form from a TableConfig."""
    is_edit = bool(row)
    controls = []
    hidden_controls = []

    for fld in config.fields:
        control = _field_control(fld, row)

        if fld.hidden:
            hidden_controls.append(control)
            continue

        # In edit mode, PK is shown as read-only display
        if is_edit and fld.name == config.pk and config.pk_kind == "generated":
            hidden_controls.append(Input(type="hidden", name=fld.name, value=str(row.get(config.pk, ""))))
            controls.append(
                Div(
                    Span(fld.label, cls="form-label fw-semibold"),
                    Div(str(row.get(config.pk, "")), cls="form-control bg-light", style="opacity:0.7;"),
                    cls="admin-field-full" if fld.full else "",
                )
            )
            continue

        controls.append(
            Div(
                FormGroup(control, label=fld.label, required=fld.required),
                cls="admin-field-full" if fld.full else "",
            )
        )

    error_alert = ""
    if error:
        error_alert = Div(error, cls="alert alert-danger mt-3")

    submit_label = "Update" if is_edit else "Create"
    submit_icon = "check2"

    return Card(
        Div(
            Div(
                H2(f"Edit {config.label.rstrip('s')}" if is_edit else f"New {config.label.rstrip('s')}",
                   cls="h5 fw-bold mb-1"),
                P(config.description or f"Manage {config.label.lower()} content.", cls="text-muted mb-0"),
            ),
            error_alert,
            Form(
                *hidden_controls,
                Div(*controls, cls="mt-3"),
                Div(
                    Button(Icon(submit_icon), f" {submit_label}", type="submit",
                           cls="btn btn-primary admin-module-btn me-2"),
                    A("Cancel", href=f"/resource/{config.key}",
                      cls="btn btn-outline-secondary"),
                    cls="mt-4",
                ),
                method="post",
                action=f"/resource/{config.key}/save",
            ),
            cls="p-3 p-md-4",
        ),
        cls="admin-card mb-4",
        body_cls="p-0",
    )


# ── Delete Confirm Modal ─────────────────────────────────────────────────

def delete_confirm_modal(row_pk: str, config: TableConfig) -> Div:
    """Branded delete confirmation modal (replaces native confirm())."""
    modal_id = f"delete-confirm-{config.key}-{row_pk}"
    return Modal(
        P("Are you sure you want to delete this record? This action cannot be undone."),
        title="Confirm Delete",
        footer=Div(
            Button("Cancel", cls="btn btn-secondary", data_bs_dismiss="modal"),
            Button(
                "Delete",
                cls="btn btn-danger",
                data_bs_dismiss="modal",
                hx_post=f"/resource/{config.key}/{row_pk}/delete",
                hx_target=f"#resource-table-{config.key}",
                hx_swap="innerHTML",
            ),
            cls="d-flex justify-content-end gap-2",
        ),
        modal_id=modal_id,
        centered=True,
    )


# ── Table (list view) ────────────────────────────────────────────────────

def resource_table(
    config: TableConfig,
    rows: list[dict],
    page: int = 1,
    total: int = 0,
    per_page: int = 25,
) -> Div:
    """Auto-generate a data table with pagination from a TableConfig."""
    if not rows:
        empty_msg = "No records found." if config.readonly else 'Create the first item with the form above.'
        return Div(
            EmptyState(
                icon=Icon("database-x", style="font-size:2rem;opacity:0.4;"),
                title="No records yet",
                description=empty_msg,
            ),
            id=f"resource-table-{config.key}",
        )

    headings = list(config.table_columns) or [f.name for f in config.fields if not f.hidden][:4]
    total_pages = max(1, (total + per_page - 1) // per_page)

    # ── Pagination ────────────────────────────────────────────────────
    pagination = ""
    if total_pages > 1:
        page_links = []
        if page > 1:
            page_links.append(
                A(Icon("chevron-left"), href="#", cls="page-link",
                  hx_get=f"/resource/{config.key}/table?page={page - 1}",
                  hx_target=f"#resource-table-{config.key}",
                  hx_swap="innerHTML")
            )

        start_p = max(1, page - 2)
        end_p = min(total_pages, page + 2)
        if start_p > 1:
            page_links.append(A("1", href="#", cls="page-link",
                                hx_get=f"/resource/{config.key}/table?page=1",
                                hx_target=f"#resource-table-{config.key}", hx_swap="innerHTML"))
            if start_p > 2:
                page_links.append(Span("…", cls="page-link text-muted"))

        for p in range(start_p, end_p + 1):
            active_cls = " active" if p == page else ""
            page_links.append(
                A(str(p), href="#", cls=f"page-link{active_cls}",
                  hx_get=f"/resource/{config.key}/table?page={p}",
                  hx_target=f"#resource-table-{config.key}", hx_swap="innerHTML")
            )

        if end_p < total_pages:
            if end_p < total_pages - 1:
                page_links.append(Span("…", cls="page-link text-muted"))
            page_links.append(
                A(str(total_pages), href="#", cls="page-link",
                  hx_get=f"/resource/{config.key}/table?page={total_pages}",
                  hx_target=f"#resource-table-{config.key}", hx_swap="innerHTML")
            )

        if page < total_pages:
            page_links.append(
                A(Icon("chevron-right"), href="#", cls="page-link",
                  hx_get=f"/resource/{config.key}/table?page={page + 1}",
                  hx_target=f"#resource-table-{config.key}", hx_swap="innerHTML")
            )

        start_item = (page - 1) * per_page + 1
        end_item = min(page * per_page, total)
        pagination = Div(
            Span(f"Showing {start_item}–{end_item} of {total}", cls="text-muted small"),
            Nav(Ul(*[Li(link, cls="page-item") for link in page_links],
                     cls="pagination pagination-sm mb-0")),
            cls="d-flex align-items-center justify-content-between mt-3",
        )

    # ── Table rows ────────────────────────────────────────────────────
    modals = []
    rows_html = []
    for row in rows:
        pk_val = _encoded_pk(row.get(config.pk, ""))
        modals.append(delete_confirm_modal(pk_val, config))

        # Edit + delete buttons
        action_cell = ""
        if not config.readonly:
            action_cell = Td(
                Div(
                    A("Edit", href=f"/resource/{config.key}/{pk_val}",
                      cls="btn btn-sm btn-outline-primary me-1"),
                    Button("Delete", cls="btn btn-sm btn-outline-danger",
                           data_bs_toggle="modal",
                           data_bs_target=f"#delete-confirm-{config.key}-{pk_val}"),
                    cls="d-flex gap-1",
                )
            )

        rows_html.append(
            Tr(
                *[Td(_safe_text(row.get(col))) for col in headings],
                action_cell,
            )
        )

    return Div(
        Div(
            Table(
                Thead(Tr(*[Th(h.capitalize().replace("_", " "), cls="text-muted small text-uppercase") for h in headings],
                          Th("") if not config.readonly else Th("Actions"))),
                Tbody(*rows_html),
                cls="table align-middle mb-0",
            ),
            cls="table-responsive",
        ),
        pagination,
        # Inject delete modals (hidden, triggered by buttons)
        *modals,
        id=f"resource-table-{config.key}",
    )
