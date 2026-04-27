"""Repository boundary for public site settings and profile metadata."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminSiteProfile, SiteSettingsSaveResult
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
    payload: object | None = None,
    prefer: str | None = None,
    query: str = "",
) -> object:
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(prefer=prefer))
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _local_settings() -> AdminSiteProfile:
    return AdminSiteProfile(
        site_name=f"{settings.owner_name} Portfolio",
        site_url="https://olorundaremicheal.vercel.app",
        full_name="Olorundare Micheal Babawale",
        role="Full-Stack & AI Systems Architect",
        email="meshelleva@gmail.com",
        phone="+2348064676590",
        whatsapp="+2348064676590",
        location="Ilorin, Kwara State, Nigeria",
        github="https://github.com/Evayoung",
        linkedin="https://www.linkedin.com/in/olorundare-micheal-babawale-12b40314b/",
        seo_title="Micheal Olorundare | Full-Stack & AI Systems Architect",
        seo_description=(
            "Portfolio settings and profile metadata for Micheal Olorundare's "
            "public website, CV, and client inquiry surfaces."
        ),
        source="local",
    )


def get_site_profile() -> AdminSiteProfile:
    if not service_role_is_configured():
        return _local_settings()
    try:
        site_rows = _rest_request("GET", "site_settings", query="?select=id,site_name,site_url,contact_email,contact_phone,location,github_url,linkedin_url,seo_title,seo_description&limit=1")
        cv_rows = _rest_request("GET", "cv_meta", query="?select=id,full_name,role,email,phone,whatsapp,location,github_url,linkedin_url&limit=1")
        site_row = site_rows[0] if isinstance(site_rows, list) and site_rows else {}
        cv_row = cv_rows[0] if isinstance(cv_rows, list) and cv_rows else {}
        fallback = _local_settings()
        return AdminSiteProfile(
            site_name=site_row.get("site_name") or fallback.site_name,
            site_url=site_row.get("site_url") or fallback.site_url,
            full_name=cv_row.get("full_name") or fallback.full_name,
            role=cv_row.get("role") or fallback.role,
            email=cv_row.get("email") or site_row.get("contact_email") or fallback.email,
            phone=cv_row.get("phone") or site_row.get("contact_phone") or fallback.phone,
            whatsapp=cv_row.get("whatsapp") or fallback.whatsapp,
            location=cv_row.get("location") or site_row.get("location") or fallback.location,
            github=cv_row.get("github_url") or site_row.get("github_url") or fallback.github,
            linkedin=cv_row.get("linkedin_url") or site_row.get("linkedin_url") or fallback.linkedin,
            seo_title=site_row.get("seo_title") or fallback.seo_title,
            seo_description=site_row.get("seo_description") or fallback.seo_description,
            source="supabase",
        )
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        return _local_settings()


def save_site_profile(
    *,
    site_name: str,
    site_url: str,
    full_name: str,
    role: str,
    email: str,
    phone: str,
    whatsapp: str,
    location: str,
    github: str,
    linkedin: str,
    seo_title: str,
    seo_description: str,
) -> SiteSettingsSaveResult:
    if not site_name.strip() or not site_url.strip() or not full_name.strip() or not role.strip():
        return SiteSettingsSaveResult(False, "warning", "Site name, site URL, full name, and role are required before saving.", "Validation")

    if not service_role_is_configured():
        return SiteSettingsSaveResult(False, "info", "Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable saving.", "Local seed data")

    site_payload = {
        "site_name": site_name.strip(),
        "site_url": site_url.strip(),
        "contact_email": email.strip(),
        "contact_phone": phone.strip(),
        "location": location.strip(),
        "github_url": github.strip(),
        "linkedin_url": linkedin.strip(),
        "seo_title": seo_title.strip(),
        "seo_description": seo_description.strip(),
    }
    cv_payload = {
        "full_name": full_name.strip(),
        "role": role.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "whatsapp": whatsapp.strip(),
        "location": location.strip(),
        "github_url": github.strip(),
        "linkedin_url": linkedin.strip(),
    }

    try:
        site_rows = _rest_request("GET", "site_settings", query="?select=id&limit=1")
        if isinstance(site_rows, list) and site_rows:
            _rest_request("PATCH", "site_settings", payload=site_payload, prefer="return=representation", query=f"?id=eq.{site_rows[0]['id']}")
        else:
            _rest_request("POST", "site_settings", payload=site_payload, prefer="return=representation")

        cv_rows = _rest_request("GET", "cv_meta", query="?select=id,summary&limit=1")
        if isinstance(cv_rows, list) and cv_rows:
            current = cv_rows[0]
            cv_payload["summary"] = current.get("summary") or _local_settings().seo_description
            _rest_request("PATCH", "cv_meta", payload=cv_payload, prefer="return=representation", query=f"?id=eq.{current['id']}")
        else:
            cv_payload["summary"] = _local_settings().seo_description
            _rest_request("POST", "cv_meta", payload=cv_payload, prefer="return=representation")

        return SiteSettingsSaveResult(True, "success", "Site settings saved to Supabase.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return SiteSettingsSaveResult(False, "danger", f"Supabase rejected the settings update. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return SiteSettingsSaveResult(False, "danger", f"Could not reach Supabase to update site settings. {exc}", "Supabase")
