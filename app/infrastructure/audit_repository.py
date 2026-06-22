"""Best-effort audit logging for production admin actions."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.infrastructure.supabase_client import service_role_is_configured


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def record_audit_event(*, action: str, target_type: str = "", target_id: str = "", actor_email: str = "", detail: str = "") -> None:
    if not service_role_is_configured():
        return
    payload = {
        "action": action.strip()[:120],
        "target_type": target_type.strip()[:80],
        "target_id": target_id.strip()[:160],
        "actor_email": actor_email.strip().lower()[:180],
        "detail": detail.strip()[:1000],
    }
    try:
        request = Request(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/admin_audit_logs",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=_headers(),
        )
        with urlopen(request, timeout=10) as response:
            response.read()
    except (HTTPError, URLError, TimeoutError, ValueError):
        return
