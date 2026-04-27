"""Repository boundary for inbox-style submission records."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminSubmission, SubmissionSaveResult, SubmissionWorkspaceSummary
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured


def _rest_headers(*, use_service_role: bool = False, prefer: str | None = None) -> dict[str, str]:
    key = settings.supabase_service_role_key if use_service_role else settings.supabase_anon_key
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _rest_request(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    payload: object | None = None,
    use_service_role: bool = False,
    prefer: str | None = None,
) -> object:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(use_service_role=use_service_role, prefer=prefer))
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    return value.replace("T", " ")[:16]


def _contact_from_row(row: dict) -> AdminSubmission:
    return AdminSubmission(
        entry_id=row["id"],
        kind="contact",
        name=row.get("name") or "",
        email=row.get("email") or "",
        phone="",
        subject=row.get("subject") or "",
        service="",
        budget="",
        timeline="",
        message=row.get("message") or "",
        status=row.get("status") or "new",
        notes=row.get("notes") or "",
        created_at=_format_timestamp(row.get("created_at") or ""),
        source="supabase",
    )


def _booking_from_row(row: dict) -> AdminSubmission:
    return AdminSubmission(
        entry_id=row["id"],
        kind="booking",
        name=row.get("name") or "",
        email=row.get("email") or "",
        phone=row.get("whatsapp") or "",
        subject="",
        service=row.get("service") or "",
        budget=row.get("budget") or "",
        timeline=row.get("timeline") or "",
        message=row.get("message") or "",
        status=row.get("status") or "new",
        notes=row.get("notes") or "",
        created_at=_format_timestamp(row.get("created_at") or ""),
        source="supabase",
    )


def _load_supabase_submissions() -> tuple[AdminSubmission, ...]:
    contact_rows = _rest_request(
        "GET",
        "contact_submissions",
        params={"select": "id,name,email,subject,message,status,notes,created_at", "order": "created_at.desc"},
        use_service_role=True,
    )
    booking_rows = _rest_request(
        "GET",
        "booking_requests",
        params={"select": "id,name,email,whatsapp,service,budget,timeline,message,status,notes,created_at", "order": "created_at.desc"},
        use_service_role=True,
    )
    contacts = tuple(_contact_from_row(row) for row in contact_rows or [])
    bookings = tuple(_booking_from_row(row) for row in booking_rows or [])
    return tuple(sorted(contacts + bookings, key=lambda item: item.created_at, reverse=True))


def _schema_note_from_http_error(exc: HTTPError) -> str:
    details = exc.read().decode("utf-8", errors="ignore")
    if "schema cache" in details or "Could not find the table" in details:
        return "Supabase is connected, but the admin schema is not applied yet. Run 001_initial_schema.sql in the Supabase SQL editor."
    return f"Supabase responded with an error while loading submissions. {details or exc.reason}"


def _load_submissions_with_state() -> tuple[tuple[AdminSubmission, ...], str, str]:
    if not service_role_is_configured():
        if supabase_is_configured():
            return (), "Pending", "Add SUPABASE_SERVICE_ROLE_KEY to load private inbox records in the admin app."
        return (), "Pending", "Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to load the live inbox."
    try:
        return _load_supabase_submissions(), "Supabase", "Live inbox connected."
    except HTTPError as exc:
        return (), "Supabase", _schema_note_from_http_error(exc)
    except (URLError, TimeoutError, ValueError) as exc:
        return (), "Supabase", f"Could not reach Supabase to load inbox records. {exc}"


def list_submissions(*, kind: str = "all", status: str = "all", search: str = "") -> tuple[AdminSubmission, ...]:
    items, _, _ = _load_submissions_with_state()
    if kind != "all":
        items = tuple(item for item in items if item.kind == kind)
    if status != "all":
        items = tuple(item for item in items if item.status == status)
    if search.strip():
        query = search.strip().lower()
        items = tuple(
            item
            for item in items
            if query in item.name.lower()
            or query in item.email.lower()
            or query in item.message.lower()
            or query in item.status.lower()
            or query in item.kind.lower()
        )
    return items


def get_submission(entry_id: str, *, kind: str = "all") -> AdminSubmission | None:
    items = list_submissions(kind=kind)
    for item in items:
        if item.entry_id == entry_id:
            return item
    return None


def get_submission_workspace_summary() -> SubmissionWorkspaceSummary:
    items, source, note = _load_submissions_with_state()
    return SubmissionWorkspaceSummary(
        total=len(items),
        new_items=sum(1 for item in items if item.status in {"new", "in_progress", "reviewing"}),
        booking_items=sum(1 for item in items if item.kind == "booking"),
        contact_items=sum(1 for item in items if item.kind == "contact"),
        source=source,
        note=note,
    )


def update_submission(*, entry_id: str, kind: str, status: str, notes: str) -> SubmissionSaveResult:
    if not entry_id.strip() or kind not in {"contact", "booking"}:
        return SubmissionSaveResult(False, "warning", "A valid submission record is required before saving.", "Validation")

    allowed_statuses = {
        "contact": {"new", "in_progress", "closed", "spam"},
        "booking": {"new", "reviewing", "scheduled", "closed", "spam"},
    }
    if status not in allowed_statuses[kind]:
        return SubmissionSaveResult(False, "warning", "Choose a valid workflow status before saving.", "Validation")

    if not service_role_is_configured():
        return SubmissionSaveResult(
            False,
            "info",
            "Supabase service-role access is not configured yet. Add SUPABASE_SERVICE_ROLE_KEY to enable inbox updates.",
            "Read-only",
        )

    table = "contact_submissions" if kind == "contact" else "booking_requests"
    payload = {"status": status, "notes": notes.strip()}

    try:
        rows = _rest_request(
            "PATCH",
            table,
            params={"id": f"eq.{entry_id}", "select": "id"},
            payload=payload,
            use_service_role=True,
            prefer="return=representation",
        )
        if isinstance(rows, list) and rows:
            return SubmissionSaveResult(True, "success", "Submission record updated in Supabase.", "Supabase")
        return SubmissionSaveResult(False, "danger", "Supabase did not return the updated submission record.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return SubmissionSaveResult(False, "danger", f"Supabase rejected the submission update. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return SubmissionSaveResult(False, "danger", f"Could not reach Supabase to update this submission. {exc}", "Supabase")
