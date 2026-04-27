"""Repository boundary for CV workspace data."""

from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminCvMeta, CvSaveResult, CvWorkspaceSummary
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
    payload: object | None = None,
    use_service_role: bool = False,
    prefer: str | None = None,
    query: str = "",
) -> object:
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(use_service_role=use_service_role, prefer=prefer))
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


@lru_cache(maxsize=1)
def _cv_module():
    content_path = Path(__file__).resolve().parents[3] / "neoportfolio" / "cv_content.py"
    spec = importlib.util.spec_from_file_location("neoportfolio_cv_admin_seed", content_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _local_meta() -> AdminCvMeta:
    meta = _cv_module().CV_META
    return AdminCvMeta(
        name=meta["name"],
        role=meta["role"],
        email=meta["email"],
        phone=meta["phone"],
        whatsapp=meta["whatsapp"],
        location=meta["location"],
        github=meta["github"],
        linkedin=meta["linkedin"],
        summary=meta["summary"],
        source="local",
    )


def get_cv_meta() -> AdminCvMeta:
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_meta", query="?select=full_name,role,email,phone,whatsapp,location,github_url,linkedin_url,summary&limit=1")
            if isinstance(rows, list) and rows:
                row = rows[0]
                return AdminCvMeta(
                    name=row.get("full_name") or "",
                    role=row.get("role") or "",
                    email=row.get("email") or "",
                    phone=row.get("phone") or "",
                    whatsapp=row.get("whatsapp") or "",
                    location=row.get("location") or "",
                    github=row.get("github_url") or "",
                    linkedin=row.get("linkedin_url") or "",
                    summary=row.get("summary") or "",
                    source="supabase",
                )
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_meta()


def list_work_history():
    return _cv_module().WORK_HISTORY


def list_education():
    return _cv_module().EDUCATION


def list_certifications():
    return _cv_module().CERTIFICATIONS


def list_tool_categories():
    return _cv_module().TOOLS_GRID


def list_languages():
    return _cv_module().LANGUAGES


def list_core_skills() -> tuple[str, ...]:
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_core_skills", query="?select=label&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(row.get("label", "").strip() for row in rows if row.get("label"))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _cv_module().CORE_SKILLS


def list_competencies() -> tuple[str, ...]:
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_competencies", query="?select=label&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(row.get("label", "").strip() for row in rows if row.get("label"))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _cv_module().COMPETENCIES


def get_cv_workspace_summary() -> CvWorkspaceSummary:
    source = get_cv_meta().source.title()
    return CvWorkspaceSummary(
        work_items=len(list_work_history()),
        certifications=len(list_certifications()),
        tool_groups=len(list_tool_categories()),
        source=source,
    )


def _parse_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _get_existing_cv_meta_id() -> str | None:
    rows = _rest_request("GET", "cv_meta", use_service_role=True, query="?select=id&limit=1")
    if isinstance(rows, list) and rows:
        row_id = rows[0].get("id")
        if isinstance(row_id, str) and row_id.strip():
            return row_id
    return None


def save_cv_profile(
    *,
    name: str,
    role: str,
    email: str,
    phone: str,
    whatsapp: str,
    location: str,
    github: str,
    linkedin: str,
    summary: str,
    core_skills: str,
    competencies: str,
) -> CvSaveResult:
    if not name.strip() or not role.strip() or not summary.strip():
        return CvSaveResult(
            success=False,
            tone="warning",
            message="Name, role, and summary are required before saving.",
            source="Validation",
        )

    if not service_role_is_configured():
        return CvSaveResult(
            success=False,
            tone="info",
            message="Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable saving.",
            source="Local seed data",
        )

    payload = {
        "full_name": name.strip(),
        "role": role.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "whatsapp": whatsapp.strip(),
        "location": location.strip(),
        "github_url": github.strip(),
        "linkedin_url": linkedin.strip(),
        "summary": summary.strip(),
    }

    try:
        existing_id = _get_existing_cv_meta_id()
        if existing_id:
            meta_rows = _rest_request(
                "PATCH",
                "cv_meta",
                payload=payload,
                use_service_role=True,
                prefer="return=representation",
                query=f"?id=eq.{existing_id}",
            )
        else:
            meta_rows = _rest_request(
                "POST",
                "cv_meta",
                payload=payload,
                use_service_role=True,
                prefer="return=representation",
            )
        meta_row = meta_rows[0] if isinstance(meta_rows, list) and meta_rows else None
        if not meta_row or "id" not in meta_row:
            return CvSaveResult(False, "danger", "Supabase did not return the saved CV meta record.", "Supabase")

        _rest_request("DELETE", "cv_core_skills", use_service_role=True)
        skills = _parse_lines(core_skills)
        if skills:
            _rest_request(
                "POST",
                "cv_core_skills",
                payload=[{"label": label, "sort_order": idx} for idx, label in enumerate(skills, start=1)],
                use_service_role=True,
                prefer="return=minimal",
            )

        _rest_request("DELETE", "cv_competencies", use_service_role=True)
        competency_items = _parse_lines(competencies)
        if competency_items:
            _rest_request(
                "POST",
                "cv_competencies",
                payload=[{"label": label, "sort_order": idx} for idx, label in enumerate(competency_items, start=1)],
                use_service_role=True,
                prefer="return=minimal",
            )

        return CvSaveResult(True, "success", "CV profile saved to Supabase.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return CvSaveResult(False, "danger", f"Supabase rejected the save request. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return CvSaveResult(False, "danger", f"Could not reach Supabase to save the CV profile. {exc}", "Supabase")
