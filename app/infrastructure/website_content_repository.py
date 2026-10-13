"""Admin repository for the public Services and Pricing collections."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminHomeContent, AdminPricingTier, AdminService, AdminTestimonial, ContentSaveResult
from app.infrastructure.supabase_client import service_role_is_configured


def _request(method: str, table: str, *, params: dict[str, str] | None = None, payload=None, prefer: str = ""):
    key = settings.supabase_service_role_key
    query = f"?{urlencode(params)}" if params else ""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}{query}",
        data=body,
        method=method,
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else None


def _child_labels(rows: list[dict]) -> tuple[str, ...]:
    return tuple(
        item["label"]
        for item in sorted(rows or [], key=lambda row: row.get("sort_order", 100))
        if item.get("label")
    )


def list_services() -> tuple[AdminService, ...]:
    if not service_role_is_configured():
        return ()
    rows = _request(
        "GET",
        "services",
        params={"select": "id,slug,title,summary,lead,timeline,price,icon,visible,sort_order,service_deliverables(label,sort_order)", "order": "sort_order.asc"},
    )
    return tuple(
        AdminService(
            id=row["id"], slug=row["slug"], title=row["title"], summary=row["summary"], lead=row["lead"],
            deliverables=_child_labels(row.get("service_deliverables") or []), timeline=row.get("timeline") or "",
            price=row.get("price") or "", icon=row.get("icon") or "", visible=bool(row.get("visible")),
            sort_order=int(row.get("sort_order") or 100),
        )
        for row in rows or []
    )


def list_pricing_tiers() -> tuple[AdminPricingTier, ...]:
    if not service_role_is_configured():
        return ()
    rows = _request(
        "GET",
        "pricing_tiers",
        params={"select": "id,title,price,highlight,visible,sort_order,pricing_points(label,sort_order)", "order": "sort_order.asc"},
    )
    return tuple(
        AdminPricingTier(
            id=row["id"], title=row["title"], price=row["price"], highlight=row["highlight"],
            points=_child_labels(row.get("pricing_points") or []), visible=bool(row.get("visible")),
            sort_order=int(row.get("sort_order") or 100),
        )
        for row in rows or []
    )


def list_testimonials() -> tuple[AdminTestimonial, ...]:
    if not service_role_is_configured():
        return ()
    rows = _request(
        "GET",
        "testimonials",
        params={"select": "id,author,role,company,quote,visible,sort_order", "order": "sort_order.asc"},
    )
    return tuple(
        AdminTestimonial(
            id=row["id"], author=row["author"], role=row.get("role") or "", company=row.get("company") or "",
            quote=row["quote"], visible=bool(row.get("visible")), sort_order=int(row.get("sort_order") or 100),
        )
        for row in rows or []
    )


def _save_children(table: str, foreign_key: str, record_id: str, labels: tuple[str, ...]) -> None:
    _request("DELETE", table, params={foreign_key: f"eq.{record_id}"})
    if labels:
        _request(
            "POST",
            table,
            payload=[{foreign_key: record_id, "label": label, "sort_order": index} for index, label in enumerate(labels, 1)],
            prefer="return=minimal",
        )


def _parse_order(raw: str) -> int:
    return max(1, min(10000, int(raw or "100")))


def save_service(
    *, record_id: str = "", slug: str, title: str, summary: str, lead: str,
    deliverables: str, timeline: str, price: str, icon: str, visible: bool, sort_order: str,
) -> ContentSaveResult:
    slug, title, summary, lead = slug.strip(), title.strip(), summary.strip(), lead.strip()
    labels = tuple(line.strip() for line in deliverables.splitlines() if line.strip())
    if not slug or not title or not summary or not lead:
        return ContentSaveResult(False, "warning", "Slug, title, summary, and lead are required.", record_id)
    if len(slug) > 100 or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in slug.lower()):
        return ContentSaveResult(False, "warning", "Use a lowercase URL slug with letters, numbers, and hyphens only.", record_id)
    if len(labels) > 40 or any(len(label) > 240 for label in labels):
        return ContentSaveResult(False, "warning", "Enter up to 40 deliverables, with no more than 240 characters each.", record_id)
    if not service_role_is_configured():
        return ContentSaveResult(False, "info", "Supabase admin write access is not configured.", record_id)
    try:
        payload = {
            "slug": slug.lower(), "title": title, "summary": summary, "lead": lead,
            "timeline": timeline.strip(), "price": price.strip(), "icon": icon.strip() or "code-slash",
            "visible": visible, "sort_order": _parse_order(sort_order),
        }
        if record_id:
            rows = _request("PATCH", "services", params={"id": f"eq.{record_id}"}, payload=payload, prefer="return=representation")
        else:
            rows = _request("POST", "services", payload=payload, prefer="return=representation")
        row = rows[0] if isinstance(rows, list) and rows else None
        if not row or not row.get("id"):
            return ContentSaveResult(False, "danger", "Supabase did not return the saved service.", record_id)
        _save_children("service_deliverables", "service_id", row["id"], labels)
        return ContentSaveResult(True, "success", f"Service '{title}' saved.", row["id"])
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:400]
        return ContentSaveResult(False, "danger", f"Supabase rejected this service: {details or exc.reason}", record_id)
    except (URLError, TimeoutError, ValueError) as exc:
        return ContentSaveResult(False, "danger", f"Could not save this service: {exc}", record_id)


def save_pricing_tier(
    *, record_id: str = "", title: str, price: str, highlight: str, points: str, visible: bool, sort_order: str,
) -> ContentSaveResult:
    title, price, highlight = title.strip(), price.strip(), highlight.strip()
    labels = tuple(line.strip() for line in points.splitlines() if line.strip())
    if not title or not price or not highlight:
        return ContentSaveResult(False, "warning", "Title, price, and highlight are required.", record_id)
    if len(labels) > 40 or any(len(label) > 240 for label in labels):
        return ContentSaveResult(False, "warning", "Enter up to 40 points, with no more than 240 characters each.", record_id)
    if not service_role_is_configured():
        return ContentSaveResult(False, "info", "Supabase admin write access is not configured.", record_id)
    try:
        payload = {"title": title, "price": price, "highlight": highlight, "visible": visible, "sort_order": _parse_order(sort_order)}
        if record_id:
            rows = _request("PATCH", "pricing_tiers", params={"id": f"eq.{record_id}"}, payload=payload, prefer="return=representation")
        else:
            rows = _request("POST", "pricing_tiers", payload=payload, prefer="return=representation")
        row = rows[0] if isinstance(rows, list) and rows else None
        if not row or not row.get("id"):
            return ContentSaveResult(False, "danger", "Supabase did not return the saved pricing tier.", record_id)
        _save_children("pricing_points", "pricing_tier_id", row["id"], labels)
        return ContentSaveResult(True, "success", f"Pricing tier '{title}' saved.", row["id"])
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:400]
        return ContentSaveResult(False, "danger", f"Supabase rejected this pricing tier: {details or exc.reason}", record_id)
    except (URLError, TimeoutError, ValueError) as exc:
        return ContentSaveResult(False, "danger", f"Could not save this pricing tier: {exc}", record_id)


def save_testimonial(
    *, record_id: str = "", author: str, role: str, company: str, quote: str, visible: bool, sort_order: str,
) -> ContentSaveResult:
    author, role, company, quote = author.strip(), role.strip(), company.strip(), quote.strip()
    if not author or not quote:
        return ContentSaveResult(False, "warning", "Author and quote are required.", record_id)
    if len(author) > 180 or len(role) > 180 or len(company) > 180 or len(quote) > 3000:
        return ContentSaveResult(False, "warning", "Keep names and roles under 180 characters and the quote under 3,000 characters.", record_id)
    if not service_role_is_configured():
        return ContentSaveResult(False, "info", "Supabase admin write access is not configured.", record_id)
    try:
        payload = {
            "author": author, "role": role or None, "company": company or None,
            "quote": quote, "visible": visible, "sort_order": _parse_order(sort_order),
        }
        if record_id:
            rows = _request("PATCH", "testimonials", params={"id": f"eq.{record_id}"}, payload=payload, prefer="return=representation")
        else:
            rows = _request("POST", "testimonials", payload=payload, prefer="return=representation")
        row = rows[0] if isinstance(rows, list) and rows else None
        if not row or not row.get("id"):
            return ContentSaveResult(False, "danger", "Supabase did not return the saved testimonial.", record_id)
        return ContentSaveResult(True, "success", f"Testimonial from '{author}' saved.", row["id"])
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:400]
        return ContentSaveResult(False, "danger", f"Supabase rejected this testimonial: {details or exc.reason}", record_id)
    except (URLError, TimeoutError, ValueError) as exc:
        return ContentSaveResult(False, "danger", f"Could not save this testimonial: {exc}", record_id)


def _objects(raw) -> tuple[dict, ...]:
    return tuple(item for item in (raw or []) if isinstance(item, dict))


def _home_content_from_row(row: dict) -> AdminHomeContent:
    return AdminHomeContent(
        hero_roles=tuple(str(value) for value in row.get("hero_roles", []) if str(value).strip()),
        hero_summary=str(row.get("hero_summary") or ""),
        about_summary=str(row.get("about_summary") or ""),
        journey_paragraphs=tuple(str(value) for value in row.get("journey_paragraphs", []) if str(value).strip()),
        about_stats=tuple((str(item.get("value") or ""), str(item.get("label") or "")) for item in _objects(row.get("about_stats"))),
        experience_items=tuple((str(item.get("year") or ""), str(item.get("title") or ""), str(item.get("company") or ""), str(item.get("summary") or "")) for item in _objects(row.get("experience_items"))),
        technical_skills=tuple((str(item.get("name") or ""), int(item.get("score") or 0), str(item.get("badge") or "")) for item in _objects(row.get("technical_skills"))),
        cv_highlights=tuple((str(item.get("title") or ""), str(item.get("copy") or "")) for item in _objects(row.get("cv_highlights"))),
        seo_keywords=tuple(str(value) for value in row.get("seo_keywords", []) if str(value).strip()),
        profile_image_url=str(row.get("profile_image_url") or ""),
        hero_background_url=str(row.get("hero_background_url") or ""),
        booking_background_url=str(row.get("booking_background_url") or ""),
        cv_background_url=str(row.get("cv_background_url") or ""),
    )


def get_site_home_content() -> AdminHomeContent | None:
    if not service_role_is_configured():
        return None
    rows = _request(
        "GET", "site_home_content",
        params={"select": "*", "id": "eq.primary", "limit": "1"},
    )
    return _home_content_from_row(rows[0]) if isinstance(rows, list) and rows else None


def _parse_lines(raw: str, *, maximum: int, field: str) -> tuple[str, ...]:
    values = tuple(line.strip() for line in raw.splitlines() if line.strip())
    if len(values) > maximum:
        raise ValueError(f"Use no more than {maximum} {field} entries.")
    return values


def _parse_pairs(raw: str, *, maximum: int, field: str) -> tuple[tuple[str, str], ...]:
    result = []
    for line in _parse_lines(raw, maximum=maximum, field=field):
        left, separator, right = line.partition("|")
        if not separator or not left.strip() or not right.strip():
            raise ValueError(f"Enter each {field} as 'label | text', one per line.")
        result.append((left.strip(), right.strip()))
    return tuple(result)


def _parse_experience(raw: str) -> tuple[dict[str, str], ...]:
    result = []
    for line in _parse_lines(raw, maximum=8, field="experience records"):
        parts = [part.strip() for part in line.split("|", 3)]
        if len(parts) != 4 or not all(parts):
            raise ValueError("Enter each experience record as 'period | role | company | summary'.")
        result.append(dict(zip(("year", "title", "company", "summary"), parts)))
    return tuple(result)


def _parse_skills(raw: str) -> tuple[dict[str, object], ...]:
    result = []
    for line in _parse_lines(raw, maximum=16, field="technical skills"):
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3 or not parts[0] or not parts[2]:
            raise ValueError("Enter each skill as 'name | score (0-100) | group'.")
        try:
            score = int(parts[1])
        except ValueError as exc:
            raise ValueError("Skill scores must be whole numbers from 0 to 100.") from exc
        if not 0 <= score <= 100:
            raise ValueError("Skill scores must be from 0 to 100.")
        result.append({"name": parts[0], "score": score, "badge": parts[2]})
    return tuple(result)


def _valid_asset_url(value: str, label: str) -> str:
    value = value.strip()
    if not value or len(value) > 2048 or any(char.isspace() for char in value):
        raise ValueError(f"Enter a valid {label} URL.")
    if value.startswith("/assets/"):
        return value
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError(f"{label.title()} must be a public HTTPS URL or an existing /assets/ path.")
    return value


def save_site_home_content(
    *, hero_roles: str, hero_summary: str, about_summary: str,
    journey_paragraphs: str, about_stats: str, experience_items: str,
    technical_skills: str, cv_highlights: str, seo_keywords: str, profile_image_url: str,
    hero_background_url: str, booking_background_url: str, cv_background_url: str,
) -> ContentSaveResult:
    if not service_role_is_configured():
        return ContentSaveResult(False, "info", "Supabase admin write access is not configured.", "primary")
    try:
        roles = _parse_lines(hero_roles, maximum=8, field="hero role titles")
        journeys = _parse_lines(journey_paragraphs, maximum=8, field="journey paragraphs")
        stats = _parse_pairs(about_stats, maximum=8, field="stats")
        highlights = _parse_pairs(cv_highlights, maximum=8, field="highlights")
        keywords = _parse_lines(seo_keywords, maximum=32, field="SEO keywords")
        experience = _parse_experience(experience_items)
        skills = _parse_skills(technical_skills)
        hero_summary, about_summary = hero_summary.strip(), about_summary.strip()
        if not roles or not hero_summary or not about_summary or not journeys:
            raise ValueError("Add at least one role and journey paragraph, plus both home-page summaries.")
        if any(len(role) > 140 for role in roles) or len(hero_summary) > 1800 or len(about_summary) > 1000:
            raise ValueError("Keep role titles under 140 characters, the hero summary under 1,800, and the About summary under 1,000.")
        if any(len(paragraph) > 1600 for paragraph in journeys):
            raise ValueError("Keep each journey paragraph under 1,600 characters.")
        if any(len(value) > 80 or len(label) > 120 for value, label in stats):
            raise ValueError("Keep statistic values under 80 characters and labels under 120.")
        if any(len(year) > 80 or len(title) > 140 or len(company) > 160 or len(summary) > 1200
               for year, title, company, summary in ((row["year"], row["title"], row["company"], row["summary"]) for row in experience)):
            raise ValueError("Keep experience periods under 80 characters, roles under 140, companies under 160, and summaries under 1,200.")
        if any(len(row["name"]) > 120 or len(row["badge"]) > 80 for row in skills):
            raise ValueError("Keep skill names under 120 characters and groups under 80.")
        if any(len(title) > 120 or len(copy) > 800 for title, copy in highlights):
            raise ValueError("Keep highlight titles under 120 characters and descriptions under 800.")
        if any(len(keyword) > 120 for keyword in keywords):
            raise ValueError("Keep each SEO keyword under 120 characters.")
        payload = {
            "id": "primary",
            "hero_roles": list(roles),
            "hero_summary": hero_summary,
            "about_summary": about_summary,
            "journey_paragraphs": list(journeys),
            "about_stats": [{"value": left, "label": right} for left, right in stats],
            "experience_items": list(experience),
            "technical_skills": list(skills),
            "cv_highlights": [{"title": left, "copy": right} for left, right in highlights],
            "seo_keywords": list(keywords),
            "profile_image_url": _valid_asset_url(profile_image_url, "profile image"),
            "hero_background_url": _valid_asset_url(hero_background_url, "home background"),
            "booking_background_url": _valid_asset_url(booking_background_url, "booking background"),
            "cv_background_url": _valid_asset_url(cv_background_url, "CV background"),
        }
        rows = _request(
            "POST", "site_home_content", params={"on_conflict": "id"}, payload=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        if not isinstance(rows, list) or not rows:
            return ContentSaveResult(False, "danger", "Supabase did not confirm the saved home content.", "primary")
        return ContentSaveResult(True, "success", "Home-page content and images saved.", "primary")
    except ValueError as exc:
        return ContentSaveResult(False, "warning", str(exc), "primary")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:400]
        return ContentSaveResult(False, "danger", f"Supabase rejected the home content: {details or exc.reason}", "primary")
    except (URLError, TimeoutError) as exc:
        return ContentSaveResult(False, "danger", f"Could not save home content: {exc}", "primary")
