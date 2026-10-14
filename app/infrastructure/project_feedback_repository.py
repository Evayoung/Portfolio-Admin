"""Private client project closeout feedback and one-time share links."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.infrastructure.audit_repository import record_audit_event
from app.infrastructure.supabase_client import service_role_is_configured


def _request(method: str, table: str, *, params=None, payload=None, prefer="return=representation"):
    query = f"?{urlencode(params)}" if params else ""
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        method=method,
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
    )
    with urlopen(req, timeout=20) as response:
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else None


def _feedback_url(token: str) -> str:
    return f"{settings.base_url.rstrip('/')}/project-feedback/{token}"


def create_or_get_feedback_link(deal_id: str) -> tuple[bool, str, str]:
    """Create a pending closeout link for a delivered deal, idempotently."""
    if not service_role_is_configured():
        return False, "Add the Supabase service role configuration before creating a client feedback link.", ""
    try:
        deals = _request("GET", "client_deals", params={"select": "id,stage,project_title", "id": f"eq.{deal_id}", "limit": "1"})
        if not deals or deals[0].get("stage") != "delivered":
            return False, "Feedback links are available after a deal is marked Delivered.", ""

        rows = _request("GET", "client_project_feedback", params={"select": "id,public_token,submitted_at", "deal_id": f"eq.{deal_id}", "limit": "1"})
        existing = rows[0] if rows else None
        if existing and existing.get("submitted_at"):
            return False, "Feedback has already been submitted for this project.", ""
        if existing and existing.get("public_token"):
            return True, "An active client feedback link is ready.", _feedback_url(str(existing["public_token"]))

        token = secrets.token_urlsafe(36)
        if existing:
            _request("PATCH", "client_project_feedback", params={"id": f"eq.{existing['id']}", "submitted_at": "is.null"}, payload={"public_token": token})
        else:
            _request("POST", "client_project_feedback", payload={"deal_id": deal_id, "public_token": token})
        record_audit_event(action="client_feedback_link_created", target_type="client_deal", target_id=deal_id)
        return True, "Client feedback link created.", _feedback_url(token)
    except HTTPError as exc:
        return False, f"Supabase rejected the feedback link request. {exc.read().decode('utf-8', errors='ignore') or exc.reason}", ""
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return False, f"Could not create the client feedback link. {exc}", ""


def get_feedback_by_token(token: str) -> dict | None:
    if not token or not service_role_is_configured():
        return None
    try:
        rows = _request(
            "GET", "client_project_feedback",
            params={
                "select": "id,deal_id,submitted_at,client_deals(project_title)",
                "public_token": f"eq.{token}", "limit": "1",
            },
        )
        return rows[0] if rows else None
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
        return None


def submit_project_feedback(*, token: str, reviewer_name: str, reviewer_email: str, rating: str, comments: str, testimonial_consent: bool, testimonial_quote: str) -> tuple[bool, str]:
    row = get_feedback_by_token(token)
    if not row:
        return False, "This feedback link is invalid or has been withdrawn."
    if row.get("submitted_at"):
        return False, "Feedback has already been received for this project."
    clean_name = reviewer_name.strip()[:120]
    clean_email = reviewer_email.strip()[:180]
    clean_comments = comments.strip()[:4000]
    clean_quote = testimonial_quote.strip()[:1000] if testimonial_consent else ""
    try:
        rating_value = int(rating)
    except (TypeError, ValueError):
        return False, "Choose a rating from 1 to 5."
    if not 1 <= rating_value <= 5:
        return False, "Choose a rating from 1 to 5."
    if not clean_comments:
        return False, "Please add a short comment about your experience."
    try:
        rows = _request(
            "PATCH", "client_project_feedback",
            params={"id": f"eq.{row['id']}", "submitted_at": "is.null"},
            payload={
                "reviewer_name": clean_name,
                "reviewer_email": clean_email,
                "rating": rating_value,
                "comments": clean_comments,
                "testimonial_consent": bool(testimonial_consent),
                "testimonial_quote": clean_quote,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if not rows:
            return False, "Feedback has already been received for this project."
        record_audit_event(action="client_project_feedback_submitted", target_type="client_deal", target_id=str(row.get("deal_id") or ""))
        return True, "Thank you. Your private project feedback has been received."
    except HTTPError as exc:
        return False, f"Supabase rejected the feedback submission. {exc.read().decode('utf-8', errors='ignore') or exc.reason}"
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return False, f"Could not submit your feedback. Please try again. {exc}"


def list_project_feedback() -> tuple[dict, ...]:
    if not service_role_is_configured():
        return ()
    try:
        rows = _request(
            "GET", "client_project_feedback",
            params={
                "select": "id,deal_id,public_token,reviewer_name,reviewer_email,rating,comments,testimonial_consent,testimonial_quote,review_status,submitted_at,created_at,client_deals(client_name,project_title,stage)",
                "order": "created_at.desc",
            },
        )
        return tuple(rows or ())
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
        return ()


def update_feedback_review_status(feedback_id: str, status: str) -> tuple[bool, str]:
    if status not in {"new", "reviewed", "archived"}:
        return False, "Choose a valid feedback status."
    if not service_role_is_configured():
        return False, "Supabase service role configuration is required."
    try:
        rows = _request(
            "PATCH", "client_project_feedback",
            params={"id": f"eq.{feedback_id}", "submitted_at": "not.is.null"},
            payload={"review_status": status},
        )
        if not rows:
            return False, "Submitted feedback could not be found."
        record_audit_event(action="client_feedback_review_status_updated", target_type="client_project_feedback", target_id=feedback_id, detail=status)
        return True, "Feedback review status updated."
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return False, f"Could not update feedback status. {exc}"
