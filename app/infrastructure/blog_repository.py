"""Repository boundary for blog workspace data."""

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
from app.domain.models import AdminBlogPost, BlogSaveResult, BlogWorkspaceSummary
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured


@lru_cache(maxsize=1)
def _neoportfolio_blog_module():
    content_path = Path(__file__).resolve().parents[3] / "neoportfolio" / "blog_content.py"
    spec = importlib.util.spec_from_file_location("neoportfolio_blog_admin_seed", content_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def _post_from_local(item) -> AdminBlogPost:
    return AdminBlogPost(
        slug=item.slug,
        title=item.title,
        category=item.category,
        summary=item.summary,
        content_html=item.content_html,
        published=item.published,
        read_minutes=item.read_minutes,
        tags=item.tags,
        image=item.image,
        source="local",
    )


def _load_local_posts() -> tuple[AdminBlogPost, ...]:
    module = _neoportfolio_blog_module()
    return tuple(_post_from_local(item) for item in module.BLOG_POSTS)


def _post_from_supabase(item: dict) -> AdminBlogPost:
    tag_links = item.get("blog_post_tags") or []
    tags = tuple(
        link["blog_tags"]["label"]
        for link in tag_links
        if isinstance(link, dict) and isinstance(link.get("blog_tags"), dict) and link["blog_tags"].get("label")
    )
    published_at = item.get("published_at") or ""
    published_label = published_at[:10] if published_at else "Draft"
    return AdminBlogPost(
        slug=item["slug"],
        title=item["title"],
        category=item["category"],
        summary=item["summary"],
        content_html=item["content_html"],
        published=published_label,
        read_minutes=int(item.get("read_minutes") or 0),
        tags=tags,
        image=item.get("image_url") or "",
        source="supabase",
    )


def _load_supabase_posts() -> tuple[AdminBlogPost, ...]:
    rows = _rest_request(
        "GET",
        "blog_posts",
        params={
            "select": "id,slug,title,category,summary,content_html,image_url,read_minutes,published,published_at,blog_post_tags(blog_tags(label))",
            "order": "published_at.desc.nullslast",
        },
    )
    if not isinstance(rows, list):
        return ()
    return tuple(_post_from_supabase(row) for row in rows)


def _load_posts() -> tuple[AdminBlogPost, ...]:
    if supabase_is_configured():
        try:
            items = _load_supabase_posts()
            if items:
                return items
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass
    return _load_local_posts()


def list_blog_posts(*, category: str = "all", search: str = "") -> tuple[AdminBlogPost, ...]:
    items = _load_posts()
    if category != "all":
        items = tuple(item for item in items if item.category == category)
    if search.strip():
        query = search.strip().lower()
        items = tuple(
            item
            for item in items
            if query in item.title.lower()
            or query in item.summary.lower()
            or query in item.slug.lower()
            or any(query in tag.lower() for tag in item.tags)
        )
    return items


def get_blog_post(slug: str) -> AdminBlogPost | None:
    for item in _load_posts():
        if item.slug == slug:
            return item
    return None


def list_blog_categories() -> tuple[tuple[str, str], ...]:
    module = _neoportfolio_blog_module()
    categories = getattr(module, "BLOG_CATEGORIES", ())
    if categories:
        return categories
    seen: list[str] = []
    for item in _load_posts():
        if item.category not in seen:
            seen.append(item.category)
    return (("all", "All"),) + tuple((slug, slug.replace("-", " ").title()) for slug in seen)


def get_blog_workspace_summary() -> BlogWorkspaceSummary:
    items = _load_posts()
    categories = {item.category for item in items}
    source = items[0].source.title() if items else "Local"
    published = sum(1 for item in items if item.published and item.published != "Draft")
    return BlogWorkspaceSummary(total=len(items), categories=len(categories), published=published, source=source)


def _parse_tags(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def save_blog_post(
    *,
    original_slug: str,
    slug: str,
    title: str,
    category: str,
    summary: str,
    content_html: str,
    image_url: str,
    read_minutes: str,
    tags: str,
    published: bool,
) -> BlogSaveResult:
    if not slug.strip() or not title.strip() or not category.strip() or not summary.strip() or not content_html.strip():
        return BlogSaveResult(
            success=False,
            tone="warning",
            message="Slug, title, category, summary, and content are required before saving.",
            source="Validation",
        )

    if not service_role_is_configured():
        return BlogSaveResult(
            success=False,
            tone="info",
            message="Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable saving.",
            source="Local seed data",
            slug=slug.strip(),
        )

    try:
        minutes_value = max(1, int(read_minutes or "1"))
    except ValueError:
        return BlogSaveResult(
            success=False,
            tone="warning",
            message="Read minutes must be a whole number.",
            source="Validation",
        )

    clean_slug = slug.strip()
    payload = {
        "slug": clean_slug,
        "title": title.strip(),
        "category": category.strip(),
        "summary": summary.strip(),
        "content_html": content_html.strip(),
        "image_url": image_url.strip(),
        "read_minutes": minutes_value,
        "published": published,
        "published_at": datetime.now(timezone.utc).isoformat() if published else None,
    }

    try:
        if original_slug.strip() and original_slug.strip() != clean_slug:
            rows = _rest_request(
                "PATCH",
                "blog_posts",
                params={"slug": f"eq.{quote(original_slug.strip(), safe='')}"},
                payload=payload,
                use_service_role=True,
                prefer="return=representation",
            )
        else:
            rows = _rest_request(
                "POST",
                "blog_posts",
                params={"on_conflict": "slug"},
                payload=payload,
                use_service_role=True,
                prefer="resolution=merge-duplicates,return=representation",
            )
        row = rows[0] if isinstance(rows, list) and rows else None
        if not row or "id" not in row:
            return BlogSaveResult(
                success=False,
                tone="danger",
                message="Supabase did not return the saved blog post record.",
                source="Supabase",
                slug=clean_slug,
            )

        post_id = row["id"]
        _rest_request(
            "DELETE",
            "blog_post_tags",
            params={"blog_post_id": f"eq.{quote(post_id, safe='-')}"},
            use_service_role=True,
        )

        tag_items = _parse_tags(tags)
        if tag_items:
            created_tag_ids: list[str] = []
            for label in tag_items:
                tag_rows = _rest_request(
                    "POST",
                    "blog_tags",
                    params={"on_conflict": "label"},
                    payload={"label": label},
                    use_service_role=True,
                    prefer="resolution=merge-duplicates,return=representation",
                )
                if isinstance(tag_rows, list) and tag_rows:
                    created_tag_ids.append(tag_rows[0]["id"])
            if created_tag_ids:
                _rest_request(
                    "POST",
                    "blog_post_tags",
                    payload=[{"blog_post_id": post_id, "blog_tag_id": tag_id} for tag_id in created_tag_ids],
                    use_service_role=True,
                    prefer="return=minimal",
                )

        return BlogSaveResult(
            success=True,
            tone="success",
            message=f"Blog post '{title.strip()}' saved to Supabase.",
            source="Supabase",
            slug=clean_slug,
        )
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return BlogSaveResult(
            success=False,
            tone="danger",
            message=f"Supabase rejected the save request. {details or exc.reason}",
            source="Supabase",
            slug=clean_slug,
        )
    except (URLError, TimeoutError, ValueError) as exc:
        return BlogSaveResult(
            success=False,
            tone="danger",
            message=f"Could not reach Supabase to save this post. {exc}",
            source="Supabase",
            slug=clean_slug,
        )
