"""Repository boundary for project workspace data."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminProject, ProjectSaveResult, ProjectWorkspaceSummary
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured


@lru_cache(maxsize=1)
def _neoportfolio_projects():
    content_path = Path(__file__).resolve().parents[3] / "neoportfolio" / "content.py"
    spec = importlib.util.spec_from_file_location("neoportfolio_content_admin_seed", content_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PROJECTS


def _project_from_local(item) -> AdminProject:
    return AdminProject(
        slug=item.slug,
        title=item.title,
        category=item.category,
        summary=item.summary,
        narrative=item.narrative,
        tech=item.tech,
        image=item.image,
        complexity=item.complexity,
        satisfaction=item.satisfaction,
        featured=item.featured,
        published=True,
        source="local",
    )


def _load_local_projects() -> tuple[AdminProject, ...]:
    return tuple(_project_from_local(item) for item in _neoportfolio_projects())


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


def _project_from_supabase(item: dict) -> AdminProject:
    tech_items = item.get("project_tech_stack") or []
    ordered_tech = tuple(
        row["label"]
        for row in sorted(tech_items, key=lambda row: row.get("sort_order", 100))
        if row.get("label")
    )
    return AdminProject(
        slug=item["slug"],
        title=item["title"],
        category=item["category"],
        summary=item["summary"],
        narrative=item["narrative"],
        tech=ordered_tech,
        image=item.get("image_url") or "",
        complexity=int(item.get("complexity") or 0),
        satisfaction=int(item.get("satisfaction") or 0),
        featured=bool(item.get("featured")),
        published=bool(item.get("published")),
        source="supabase",
    )


def _load_supabase_projects() -> tuple[AdminProject, ...]:
    rows = _rest_request(
        "GET",
        "projects",
        params={
            "select": "slug,title,category,summary,narrative,image_url,complexity,satisfaction,featured,published,sort_order,project_tech_stack(label,sort_order)",
            "order": "sort_order.asc",
        },
    )
    if not isinstance(rows, list):
        return ()
    return tuple(_project_from_supabase(row) for row in rows)


def _load_projects() -> tuple[AdminProject, ...]:
    if supabase_is_configured():
        try:
            items = _load_supabase_projects()
            if items:
                return items
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _load_local_projects()


def list_projects(*, category: str = "all", featured_only: bool = False, search: str = "") -> tuple[AdminProject, ...]:
    items = _load_projects()
    if category != "all":
        items = tuple(item for item in items if item.category == category)
    if featured_only:
        items = tuple(item for item in items if item.featured)
    if search.strip():
        query = search.strip().lower()
        items = tuple(
            item
            for item in items
            if query in item.title.lower() or query in item.summary.lower() or query in item.slug.lower()
        )
    return items


def get_project(slug: str) -> AdminProject | None:
    for item in _load_projects():
        if item.slug == slug:
            return item
    return None


def list_project_categories() -> tuple[tuple[str, str], ...]:
    items = _load_projects()
    seen: list[str] = []
    for item in items:
        if item.category not in seen:
            seen.append(item.category)
    return (("all", "All"),) + tuple((slug, slug.replace("-", " ").title()) for slug in seen)


def get_project_workspace_summary() -> ProjectWorkspaceSummary:
    items = _load_projects()
    categories = {item.category for item in items}
    source = items[0].source.title() if items else "Local"
    return ProjectWorkspaceSummary(
        total=len(items),
        featured=sum(1 for item in items if item.featured),
        categories=len(categories),
        source=source,
    )


def _parse_tech_stack(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def save_project(
    *,
    original_slug: str,
    slug: str,
    title: str,
    category: str,
    summary: str,
    narrative: str,
    tech_stack: str,
    image_url: str,
    complexity: str,
    satisfaction: str,
    featured: bool,
    published: bool,
) -> ProjectSaveResult:
    if not slug.strip() or not title.strip() or not category.strip() or not summary.strip() or not narrative.strip():
        return ProjectSaveResult(
            success=False,
            tone="warning",
            message="Slug, title, category, summary, and narrative are required before saving.",
            source="Validation",
        )

    if not service_role_is_configured():
        return ProjectSaveResult(
            success=False,
            tone="info",
            message="Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable saving.",
            source="Local seed data",
            slug=slug.strip(),
        )

    try:
        complexity_value = max(0, min(100, int(complexity or "0")))
        satisfaction_value = max(0, min(100, int(satisfaction or "0")))
    except ValueError:
        return ProjectSaveResult(
            success=False,
            tone="warning",
            message="Complexity and satisfaction must be whole numbers between 0 and 100.",
            source="Validation",
        )

    clean_slug = slug.strip()
    payload = {
        "slug": clean_slug,
        "title": title.strip(),
        "category": category.strip(),
        "summary": summary.strip(),
        "narrative": narrative.strip(),
        "image_url": image_url.strip(),
        "complexity": complexity_value,
        "satisfaction": satisfaction_value,
        "featured": featured,
        "published": published,
        "published_at": None,
    }
    if published:
        payload["published_at"] = datetime.now(timezone.utc).isoformat()

    try:
        if original_slug.strip() and original_slug.strip() != clean_slug:
            rows = _rest_request(
                "PATCH",
                "projects",
                params={"slug": f"eq.{quote(original_slug.strip(), safe='')}"},
                payload=payload,
                use_service_role=True,
                prefer="return=representation",
            )
        else:
            rows = _rest_request(
                "POST",
                "projects",
                params={"on_conflict": "slug"},
                payload=payload,
                use_service_role=True,
                prefer="resolution=merge-duplicates,return=representation",
            )
        row = rows[0] if isinstance(rows, list) and rows else None
        if not row or "id" not in row:
            return ProjectSaveResult(
                success=False,
                tone="danger",
                message="Supabase did not return the saved project record.",
                source="Supabase",
                slug=clean_slug,
            )

        project_id = row["id"]
        _rest_request(
            "DELETE",
            "project_tech_stack",
            params={"project_id": f"eq.{quote(project_id, safe='-')}"},
            use_service_role=True,
        )

        tech_items = _parse_tech_stack(tech_stack)
        if tech_items:
            _rest_request(
                "POST",
                "project_tech_stack",
                payload=[
                    {"project_id": project_id, "label": label, "sort_order": index}
                    for index, label in enumerate(tech_items, start=1)
                ],
                use_service_role=True,
                prefer="return=minimal",
            )

        return ProjectSaveResult(
            success=True,
            tone="success",
            message=f"Project '{title.strip()}' saved to Supabase.",
            source="Supabase",
            slug=clean_slug,
        )
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return ProjectSaveResult(
            success=False,
            tone="danger",
            message=f"Supabase rejected the save request. {details or exc.reason}",
            source="Supabase",
            slug=clean_slug,
        )
    except (URLError, TimeoutError, ValueError) as exc:
        return ProjectSaveResult(
            success=False,
            tone="danger",
            message=f"Could not reach Supabase to save this project. {exc}",
            source="Supabase",
            slug=clean_slug,
        )
