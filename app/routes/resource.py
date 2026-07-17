"""Dynamic CRUD routes for schema-driven resources.

Provides list/create/edit/save/delete endpoints driven by TableConfig.
HTMX-powered pagination and live search.
"""
from __future__ import annotations

from fasthtml.common import Div
from faststrap import Icon
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.presentation.crud_helpers import (
    delete_confirm_modal,
    resource_form,
    resource_table,
)
from app.presentation.shell import page_frame
from app.schema import TABLES, TableConfig


# ── Supabase REST helpers (local to this module) ──────────────────────────

def _rest_request(method: str, path: str, *, payload=None, prefer=None, query="", use_service_role=False):
    """Generic Supabase REST request."""
    import json
    import ssl
    from urllib.request import Request as UrllibRequest, urlopen
    from app.config import settings
    from app.infrastructure.supabase_client import service_role_is_configured

    if not settings.supabase_url:
        return []

    headers = {
        "Content-Type": "application/json",
    }
    if use_service_role and service_role_is_configured():
        headers["apikey"] = settings.supabase_service_role_key
        headers["Authorization"] = f"Bearer {settings.supabase_service_role_key}"
    else:
        headers["apikey"] = settings.supabase_anon_key
        headers["Authorization"] = f"Bearer {settings.supabase_anon_key}"

    if prefer:
        headers["Prefer"] = prefer

    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = UrllibRequest(url, data=body, method=method, headers=headers)
    # Create a fresh SSL context to avoid stale session issues
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=20, context=ctx) as resp:
        raw = resp.read()
        if not raw:
            return None
        return json.loads(raw.decode())


def _list_rows(table: str, *, page: int = 1, per_page: int = 25, order: str = "created_at.desc",
               search_col: str = "", search_q: str = "") -> tuple[list[dict], int]:
    """Fetch rows with pagination. Returns (rows, total_count)."""
    # Fetch page
    offset = (page - 1) * per_page
    query = f"?select=*&order={order}&limit={per_page}&offset={offset}"
    if search_col and search_q:
        query += f"&{search_col}=ilike.*{search_q}*"
    try:
        rows = _rest_request("GET", table, query=query)
        if not isinstance(rows, list):
            rows = []
    except Exception as exc:
        print(f"[resource] Error fetching {table}: {exc}")
        rows = []

    # Use len(rows) as total (simple approach; full count requires separate query)
    total = len(rows)
    return rows, total


def _get_row(table: str, pk: str, pk_value: str) -> dict | None:
    """Fetch a single row by primary key."""
    query = f"?select=*&{pk}=eq.{pk_value}&limit=1"
    try:
        rows = _rest_request("GET", table, query=query)
        if isinstance(rows, list) and rows:
            return rows[0]
    except Exception:
        pass
    return None


def _upsert_row(table: str, payload: dict) -> None:
    """Insert or update a row."""
    _rest_request("POST", table, payload=payload, prefer="resolution=merge-duplicates")


def _delete_row(table: str, pk: str, pk_value: str) -> None:
    """Delete a row by primary key."""
    _rest_request("DELETE", table, query=f"?{pk}=eq.{pk_value}")


# ── Auth check ────────────────────────────────────────────────────────────

def _require_admin(request: Request):
    """Return redirect to /login if not authenticated."""
    if not request.session.get("admin_authenticated"):
        return RedirectResponse("/login", status_code=303)
    return None


# ── Page builder ──────────────────────────────────────────────────────────

def _resource_page_content(config: TableConfig, rows: list[dict], total: int,
                           page: int = 1, status: str = "") -> list:
    """Build the page content for a resource list view."""
    status_alert = ""
    if status == "saved":
        status_alert = Div("Record saved successfully.", cls="alert alert-success")
    elif status == "deleted":
        status_alert = Div("Record deleted.", cls="alert alert-warning")
    elif status == "error":
        status_alert = Div("An error occurred. Please try again.", cls="alert alert-danger")

    content = [
        status_alert,
    ]

    # Summary cards
    content.append(
        Div(
            Div(
                Div(Icon(config.icon, cls="me-2"), config.label, cls="h5 fw-bold mb-1"),
                P(config.description or f"Manage {config.label.lower()} records.", cls="text-muted mb-0 small"),
                cls="col",
            ),
            Div(
                Div(total, cls="h3 fw-bold mb-0"),
                Span("Total Records", cls="text-muted small"),
                cls="text-end",
            ) if total else "",
            cls="row align-items-center mb-4",
        )
    )

    # Create form (non-readonly only)
    if not config.readonly:
        content.append(resource_form(config))

    # Data table
    content.append(resource_table(config, rows, page=page, total=total))

    return content


# ── Route handlers ────────────────────────────────────────────────────────

def register_resource_routes(app):
    """Register all dynamic CRUD routes on the FastHTML app."""

    @app.get("/resource/{key}")
    def resource_list(request: Request, key: str, status: str = "", page: int = 1):
        redirect = _require_admin(request)
        if redirect:
            return redirect

        config = TABLES.get(key)
        if not config:
            return RedirectResponse("/")

        try:
            rows, total = _list_rows(config.table, page=page, order=config.order)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            rows, total = [], 0
            status = f"Error loading data: {exc}"

        try:
            content = _resource_page_content(config, rows, total, page=page, status=status)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            content = [Div(f"Error rendering page: {exc}", cls="alert alert-danger")]

        return page_frame(
            *content,
            current=f"/resource/{key}",
            title=config.label,
        )

    @app.get("/resource/{key}/table")
    def resource_table_htmx(request: Request, key: str, page: int = 1):
        """HTMX endpoint for paginated table content."""
        redirect = _require_admin(request)
        if redirect:
            return redirect

        config = TABLES.get(key)
        if not config:
            return ""

        rows, total = _list_rows(config.table, page=page, order=config.order)
        return resource_table(config, rows, page=page, total=total)

    @app.get("/resource/{key}/{pk_value:path}")
    def resource_edit(request: Request, key: str, pk_value: str):
        redirect = _require_admin(request)
        if redirect:
            return redirect

        config = TABLES.get(key)
        if not config:
            return RedirectResponse("/")

        row = _get_row(config.table, config.pk, pk_value)
        if not row:
            return RedirectResponse(f"/resource/{key}?status=error")

        content = _resource_page_content(config, [], 0)
        # Replace the form with an edit form
        if not config.readonly:
            content[1:2] = [resource_form(config, row=row)]

        return page_frame(
            *content,
            current=f"/resource/{key}",
            title=f"Edit {config.label.rstrip('s')}",
        )

    @app.post("/resource/{key}/save")
    async def resource_save(request: Request, key: str):
        redirect = _require_admin(request)
        if redirect:
            return redirect

        config = TABLES.get(key)
        if not config or config.readonly:
            return RedirectResponse("/")

        form = await request.form()
        payload = {}
        for fld in config.fields:
            if fld.name == config.pk and config.pk_kind == "generated":
                continue  # Skip PK for auto-generated
            val = form.get(fld.name, "")
            if fld.kind == "checkbox":
                payload[fld.name] = val == "true" or val is True
            elif fld.kind == "number":
                try:
                    payload[fld.name] = int(val) if val else (fld.default or 0)
                except (ValueError, TypeError):
                    payload[fld.name] = fld.default or 0
            else:
                payload[fld.name] = str(val).strip() if val else ""

        pk_value = str(form.get(config.pk, "")).strip()

        try:
            if pk_value and config.pk_kind != "generated":
                payload[config.pk] = pk_value
                _upsert_row(config.table, payload)
            elif pk_value:
                payload[config.pk] = pk_value
                _upsert_row(config.table, payload)
            else:
                _upsert_row(config.table, payload)
        except Exception as exc:
            return RedirectResponse(f"/resource/{key}?status=error: {exc}")

        return RedirectResponse(f"/resource/{key}?status=saved", status_code=303)

    @app.post("/resource/{key}/{pk_value:path}/delete")
    async def resource_delete(request: Request, key: str, pk_value: str):
        redirect = _require_admin(request)
        if redirect:
            return redirect

        config = TABLES.get(key)
        if not config or config.readonly:
            return RedirectResponse("/")

        try:
            _delete_row(config.table, config.pk, pk_value)
        except Exception:
            pass

        # Return the updated table via HTMX
        rows, total = _list_rows(config.table, order=config.order)
        return resource_table(config, rows, total=total)
