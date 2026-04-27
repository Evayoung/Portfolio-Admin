"""Sync local portfolio seed content into Supabase."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from app.config import settings
from app.infrastructure.supabase_client import service_role_is_configured


def _rest_headers(*, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _rest_request(
    method: str,
    path: str,
    *,
    query: str = "",
    payload: object | None = None,
    prefer: str | None = None,
) -> object:
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(prefer=prefer))
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _load_module(filename: str, module_name: str):
    path = Path(__file__).resolve().parents[3] / "neoportfolio" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ensure_service_role() -> None:
    if not service_role_is_configured():
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required before syncing content.")


def _replace_table(table: str, rows: list[dict]) -> None:
    _clear_table(table)
    if rows:
        _rest_request("POST", table, payload=rows, prefer="return=representation")


def _clear_table(table: str, *, filter_query: str = "?id=not.is.null") -> None:
    _rest_request("DELETE", table, query=filter_query)


def _upsert_by_slug(table: str, rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    result = _rest_request(
        "POST",
        table,
        query="?on_conflict=slug",
        payload=rows,
        prefer="resolution=merge-duplicates,return=representation",
    )
    return result if isinstance(result, list) else []


def _upsert_site_settings(content_module) -> None:
    payload = {
        "site_name": f"{content_module.DEVELOPER_NAME_SHORT} Portfolio",
        "site_url": content_module.SITE_URL,
        "contact_email": content_module.EMAIL,
        "contact_phone": content_module.PHONE,
        "location": content_module.LOCATION,
        "github_url": content_module.GITHUB_URL,
        "linkedin_url": content_module.LINKEDIN_URL,
        "seo_title": f"{content_module.DEVELOPER_NAME_SHORT} | {content_module.DEVELOPER_ROLE}",
        "seo_description": content_module.HERO_SUMMARY,
    }
    rows = _rest_request("GET", "site_settings", query="?select=id&limit=1")
    if isinstance(rows, list) and rows:
        row_id = rows[0]["id"]
        _rest_request("PATCH", "site_settings", query=f"?id=eq.{row_id}", payload=payload, prefer="return=representation")
    else:
        _rest_request("POST", "site_settings", payload=payload, prefer="return=representation")


def sync_projects(content_module) -> int:
    project_rows = [
        {
            "slug": item.slug,
            "title": item.title,
            "category": item.category,
            "summary": item.summary,
            "narrative": item.narrative,
            "image_url": item.image,
            "complexity": item.complexity,
            "satisfaction": item.satisfaction,
            "featured": item.featured,
            "published": True,
        }
        for item in content_module.PROJECTS
    ]
    saved = _upsert_by_slug("projects", project_rows)
    project_ids = {row["slug"]: row["id"] for row in saved if isinstance(row, dict) and row.get("slug") and row.get("id")}
    _clear_table("project_tech_stack")
    tech_rows: list[dict] = []
    for item in content_module.PROJECTS:
        project_id = project_ids.get(item.slug)
        if not project_id:
            continue
        tech_rows.extend(
            {"project_id": project_id, "label": label, "sort_order": index}
            for index, label in enumerate(item.tech, start=1)
        )
    if tech_rows:
        _rest_request("POST", "project_tech_stack", payload=tech_rows, prefer="return=minimal")
    return len(project_rows)


def sync_blog(blog_module) -> int:
    post_rows = [
        {
            "slug": post.slug,
            "title": post.title,
            "category": post.category,
            "summary": post.summary,
            "content_html": post.content_html,
            "image_url": post.image,
            "read_minutes": post.read_minutes,
            "published": True,
            "published_at": f"{post.published}T00:00:00+00:00",
        }
        for post in blog_module.BLOG_POSTS
    ]
    saved = _upsert_by_slug("blog_posts", post_rows)
    post_ids = {row["slug"]: row["id"] for row in saved if isinstance(row, dict) and row.get("slug") and row.get("id")}
    tags = sorted({tag for post in blog_module.BLOG_POSTS for tag in post.tags})
    tag_rows = [{"label": label} for label in tags]
    saved_tags = _rest_request(
        "POST",
        "blog_tags",
        query="?on_conflict=label",
        payload=tag_rows,
        prefer="resolution=merge-duplicates,return=representation",
    )
    tag_ids = {row["label"]: row["id"] for row in saved_tags if isinstance(row, dict) and row.get("label") and row.get("id")}
    _clear_table("blog_post_tags", filter_query="?blog_post_id=not.is.null")
    link_rows: list[dict] = []
    for post in blog_module.BLOG_POSTS:
        post_id = post_ids.get(post.slug)
        if not post_id:
            continue
        for tag in post.tags:
            tag_id = tag_ids.get(tag)
            if tag_id:
                link_rows.append({"blog_post_id": post_id, "blog_tag_id": tag_id})
    if link_rows:
        _rest_request("POST", "blog_post_tags", payload=link_rows, prefer="return=minimal")
    return len(post_rows)


def sync_cv(cv_module) -> dict[str, int]:
    meta = cv_module.CV_META
    _replace_table(
        "cv_meta",
        [
            {
                "full_name": meta["name"],
                "role": meta["role"],
                "email": meta["email"],
                "phone": meta["phone"],
                "whatsapp": meta["whatsapp"],
                "location": meta["location"],
                "github_url": meta["github"],
                "linkedin_url": meta["linkedin"],
                "summary": meta["summary"],
            }
        ],
    )
    _replace_table(
        "cv_work_history",
        [
            {
                "title": item.title,
                "organisation": item.organisation,
                "period": item.period,
                "location": item.location,
                "bullets": list(item.bullets),
                "sort_order": index,
            }
            for index, item in enumerate(cv_module.WORK_HISTORY, start=1)
        ],
    )
    _replace_table(
        "cv_education",
        [
            {
                "degree": item.degree,
                "institution": item.institution,
                "period": item.period,
                "note": item.note,
                "sort_order": index,
            }
            for index, item in enumerate(cv_module.EDUCATION, start=1)
        ],
    )
    _replace_table(
        "cv_certifications",
        [
            {
                "name": item.name,
                "issuer": item.issuer,
                "year": item.year,
                "credential_url": item.credential_url,
                "sort_order": index,
            }
            for index, item in enumerate(cv_module.CERTIFICATIONS, start=1)
        ],
    )
    _replace_table(
        "cv_tool_categories",
        [
            {
                "label": item.label,
                "tools": list(item.tools),
                "sort_order": index,
            }
            for index, item in enumerate(cv_module.TOOLS_GRID, start=1)
        ],
    )
    _replace_table(
        "cv_languages",
        [
            {
                "label": label,
                "proficiency_label": level,
                "proficiency_score": score,
                "sort_order": index,
            }
            for index, (label, level, score) in enumerate(cv_module.LANGUAGES, start=1)
        ],
    )
    _replace_table(
        "cv_core_skills",
        [{"label": label, "sort_order": index} for index, label in enumerate(cv_module.CORE_SKILLS, start=1)],
    )
    _replace_table(
        "cv_competencies",
        [{"label": label, "sort_order": index} for index, label in enumerate(cv_module.COMPETENCIES, start=1)],
    )
    return {
        "work_history": len(cv_module.WORK_HISTORY),
        "education": len(cv_module.EDUCATION),
        "certifications": len(cv_module.CERTIFICATIONS),
        "tool_groups": len(cv_module.TOOLS_GRID),
    }


def sync_services_and_pricing(content_module) -> dict[str, int]:
    service_rows = [
        {
            "slug": item.slug,
            "title": item.title,
            "summary": item.summary,
            "lead": item.lead,
            "timeline": item.timeline,
            "price": item.price,
            "icon": item.icon,
            "visible": True,
            "sort_order": index,
        }
        for index, item in enumerate(content_module.SERVICES, start=1)
    ]
    saved_services = _upsert_by_slug("services", service_rows)
    service_ids = {row["slug"]: row["id"] for row in saved_services if isinstance(row, dict) and row.get("slug") and row.get("id")}
    _clear_table("service_deliverables")
    deliverable_rows: list[dict] = []
    for item in content_module.SERVICES:
        service_id = service_ids.get(item.slug)
        if not service_id:
            continue
        deliverable_rows.extend(
            {"service_id": service_id, "label": label, "sort_order": index}
            for index, label in enumerate(item.deliverables, start=1)
        )
    if deliverable_rows:
        _rest_request("POST", "service_deliverables", payload=deliverable_rows, prefer="return=minimal")

    _replace_table(
        "pricing_tiers",
        [
            {
                "title": item.title,
                "price": item.price,
                "highlight": item.highlight,
                "visible": True,
                "sort_order": index,
            }
            for index, item in enumerate(content_module.PRICING_TIERS, start=1)
        ],
    )
    pricing_rows = _rest_request("GET", "pricing_tiers", query="?select=id,title")
    pricing_ids = {row["title"]: row["id"] for row in pricing_rows if isinstance(row, dict) and row.get("title") and row.get("id")}
    _clear_table("pricing_points")
    point_rows: list[dict] = []
    for item in content_module.PRICING_TIERS:
        tier_id = pricing_ids.get(item.title)
        if not tier_id:
            continue
        point_rows.extend(
            {"pricing_tier_id": tier_id, "label": label, "sort_order": index}
            for index, label in enumerate(item.points, start=1)
        )
    if point_rows:
        _rest_request("POST", "pricing_points", payload=point_rows, prefer="return=minimal")
    return {"services": len(service_rows), "pricing_tiers": len(content_module.PRICING_TIERS)}


def sync_testimonials(content_module) -> int:
    _replace_table(
        "testimonials",
        [
            {
                "author": item.author,
                "role": item.role,
                "company": item.company,
                "quote": item.quote,
                "visible": True,
                "sort_order": index,
            }
            for index, item in enumerate(content_module.TESTIMONIALS, start=1)
        ],
    )
    return len(content_module.TESTIMONIALS)


def sync_all_content() -> dict[str, object]:
    _ensure_service_role()
    content_module = _load_module("content.py", "neoportfolio_content_sync")
    blog_module = _load_module("blog_content.py", "neoportfolio_blog_sync")
    cv_module = _load_module("cv_content.py", "neoportfolio_cv_sync")

    _upsert_site_settings(content_module)
    project_count = sync_projects(content_module)
    blog_count = sync_blog(blog_module)
    cv_counts = sync_cv(cv_module)
    service_counts = sync_services_and_pricing(content_module)
    testimonial_count = sync_testimonials(content_module)

    return {
        "projects": project_count,
        "blog_posts": blog_count,
        "cv": cv_counts,
        "services": service_counts["services"],
        "pricing_tiers": service_counts["pricing_tiers"],
        "testimonials": testimonial_count,
        "site_settings": 1,
    }
