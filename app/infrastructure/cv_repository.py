"""Repository boundary for CV workspace data."""

from __future__ import annotations

import importlib.util
import json
from functools import lru_cache
from pathlib import Path
import sys
from types import SimpleNamespace
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
    if not content_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("neoportfolio_cv_admin_seed", content_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _local_seed(name: str, default):
    module = _cv_module()
    if module is None:
        return default
    return getattr(module, name, default)


def _local_meta() -> AdminCvMeta:
    meta = _local_seed("CV_META", {})
    return AdminCvMeta(
        name=meta.get("name", ""),
        role=meta.get("role", ""),
        email=meta.get("email", ""),
        phone=meta.get("phone", ""),
        whatsapp=meta.get("whatsapp", ""),
        location=meta.get("location", ""),
        github=meta.get("github", ""),
        linkedin=meta.get("linkedin", ""),
        summary=meta.get("summary", ""),
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
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_work_history", query="?select=title,organisation,period,location,bullets&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(
                    SimpleNamespace(
                        title=row.get("title", ""),
                        organisation=row.get("organisation", ""),
                        period=row.get("period", ""),
                        location=row.get("location", ""),
                        bullets=tuple(row.get("bullets") or []),
                    )
                    for row in rows
                )
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("WORK_HISTORY", tuple())


def list_education():
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_education", query="?select=degree,institution,period,note&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(
                    SimpleNamespace(
                        degree=row.get("degree", ""),
                        institution=row.get("institution", ""),
                        period=row.get("period", ""),
                        note=row.get("note", ""),
                    )
                    for row in rows
                )
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("EDUCATION", tuple())


def list_certifications():
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_certifications", query="?select=name,issuer,year,credential_url&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(
                    SimpleNamespace(
                        name=row.get("name", ""),
                        issuer=row.get("issuer", ""),
                        year=row.get("year", ""),
                        credential_url=row.get("credential_url", ""),
                    )
                    for row in rows
                )
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("CERTIFICATIONS", tuple())


def list_tool_categories():
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_tool_categories", query="?select=label,tools&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(
                    SimpleNamespace(
                        label=row.get("label", ""),
                        tools=tuple(row.get("tools") or []),
                    )
                    for row in rows
                )
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("TOOLS_GRID", tuple())


def list_languages():
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_languages", query="?select=label,proficiency_label,proficiency_score&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(
                    (
                        row.get("label", ""),
                        row.get("proficiency_label", ""),
                        int(row.get("proficiency_score") or 0),
                    )
                    for row in rows
                )
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("LANGUAGES", tuple())


def list_core_skills() -> tuple[str, ...]:
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_core_skills", query="?select=label&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(row.get("label", "").strip() for row in rows if row.get("label"))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("CORE_SKILLS", tuple())


def list_competencies() -> tuple[str, ...]:
    if supabase_is_configured():
        try:
            rows = _rest_request("GET", "cv_competencies", query="?select=label&order=sort_order.asc")
            if isinstance(rows, list) and rows:
                return tuple(row.get("label", "").strip() for row in rows if row.get("label"))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _local_seed("COMPETENCIES", tuple())


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


def _parse_pipe_rows(raw: str, *, section: str, min_parts: int) -> tuple[list[list[str]], str]:
    rows: list[list[str]] = []
    for line_number, line in enumerate(_parse_lines(raw), start=1):
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < min_parts or any(not part for part in parts[:min_parts]):
            return [], f"{section} line {line_number} is incomplete. Use the documented pipe-separated format."
        rows.append(parts)
    return rows, ""


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _split_bullets(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(";") if item.strip()]


def _get_existing_cv_meta_id() -> str | None:
    rows = _rest_request("GET", "cv_meta", use_service_role=True, query="?select=id&limit=1")
    if isinstance(rows, list) and rows:
        row_id = rows[0].get("id")
        if isinstance(row_id, str) and row_id.strip():
            return row_id
    return None


def _delete_all_rows(path: str) -> None:
    # Supabase REST blocks unscoped DELETEs, so we use a safe all-rows filter.
    _rest_request("DELETE", path, use_service_role=True, query="?id=not.is.null")


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
    work_history: str = "",
    education: str = "",
    certifications: str = "",
    tool_categories: str = "",
    languages: str = "",
) -> CvSaveResult:
    if not name.strip() or not role.strip() or not summary.strip():
        return CvSaveResult(
            success=False,
            tone="warning",
            message="Name, role, and summary are required before saving.",
            source="Validation",
        )

    work_rows, error = _parse_pipe_rows(work_history, section="Experience", min_parts=3)
    if error:
        return CvSaveResult(False, "warning", error, "Validation")
    education_rows, error = _parse_pipe_rows(education, section="Education", min_parts=3)
    if error:
        return CvSaveResult(False, "warning", error, "Validation")
    certification_rows, error = _parse_pipe_rows(certifications, section="Certifications", min_parts=3)
    if error:
        return CvSaveResult(False, "warning", error, "Validation")
    tool_rows, error = _parse_pipe_rows(tool_categories, section="Tools", min_parts=2)
    if error:
        return CvSaveResult(False, "warning", error, "Validation")
    language_rows, error = _parse_pipe_rows(languages, section="Languages", min_parts=3)
    if error:
        return CvSaveResult(False, "warning", error, "Validation")

    language_payload = []
    for idx, parts in enumerate(language_rows, start=1):
        try:
            score = int(parts[2])
        except ValueError:
            return CvSaveResult(False, "warning", f"Languages line {idx} needs a numeric score from 0 to 100.", "Validation")
        if score < 0 or score > 100:
            return CvSaveResult(False, "warning", f"Languages line {idx} score must be between 0 and 100.", "Validation")
        language_payload.append(
            {
                "label": parts[0],
                "proficiency_label": parts[1],
                "proficiency_score": score,
                "sort_order": idx,
            }
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

        _delete_all_rows("cv_core_skills")
        skills = _parse_lines(core_skills)
        if skills:
            _rest_request(
                "POST",
                "cv_core_skills",
                payload=[{"label": label, "sort_order": idx} for idx, label in enumerate(skills, start=1)],
                use_service_role=True,
                prefer="return=minimal",
            )

        _delete_all_rows("cv_competencies")
        competency_items = _parse_lines(competencies)
        if competency_items:
            _rest_request(
                "POST",
                "cv_competencies",
                payload=[{"label": label, "sort_order": idx} for idx, label in enumerate(competency_items, start=1)],
                use_service_role=True,
                prefer="return=minimal",
            )

        _delete_all_rows("cv_work_history")
        if work_rows:
            _rest_request(
                "POST",
                "cv_work_history",
                payload=[
                    {
                        "title": parts[0],
                        "organisation": parts[1],
                        "period": parts[2],
                        "location": parts[3] if len(parts) > 3 else "",
                        "bullets": _split_bullets(parts[4]) if len(parts) > 4 else [],
                        "sort_order": idx,
                    }
                    for idx, parts in enumerate(work_rows, start=1)
                ],
                use_service_role=True,
                prefer="return=minimal",
            )

        _delete_all_rows("cv_education")
        if education_rows:
            _rest_request(
                "POST",
                "cv_education",
                payload=[
                    {
                        "degree": parts[0],
                        "institution": parts[1],
                        "period": parts[2],
                        "note": parts[3] if len(parts) > 3 else "",
                        "sort_order": idx,
                    }
                    for idx, parts in enumerate(education_rows, start=1)
                ],
                use_service_role=True,
                prefer="return=minimal",
            )

        _delete_all_rows("cv_certifications")
        if certification_rows:
            _rest_request(
                "POST",
                "cv_certifications",
                payload=[
                    {
                        "name": parts[0],
                        "issuer": parts[1],
                        "year": parts[2],
                        "credential_url": parts[3] if len(parts) > 3 else "",
                        "sort_order": idx,
                    }
                    for idx, parts in enumerate(certification_rows, start=1)
                ],
                use_service_role=True,
                prefer="return=minimal",
            )

        _delete_all_rows("cv_tool_categories")
        if tool_rows:
            _rest_request(
                "POST",
                "cv_tool_categories",
                payload=[
                    {
                        "label": parts[0],
                        "tools": _split_csv(parts[1]),
                        "sort_order": idx,
                    }
                    for idx, parts in enumerate(tool_rows, start=1)
                ],
                use_service_role=True,
                prefer="return=minimal",
            )

        _delete_all_rows("cv_languages")
        if language_payload:
            _rest_request(
                "POST",
                "cv_languages",
                payload=language_payload,
                use_service_role=True,
                prefer="return=minimal",
            )

        return CvSaveResult(True, "success", "Full CV profile and structured sections saved to Supabase.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return CvSaveResult(False, "danger", f"Supabase rejected the save request. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return CvSaveResult(False, "danger", f"Could not reach Supabase to save the CV profile. {exc}", "Supabase")
