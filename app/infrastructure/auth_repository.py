"""Simple admin access management with env-seeded fallback."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminAccessProfile, AdminAccessSaveResult, AdminLoginResult
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


def _hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    iterations = 240_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt_value}${derived.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
    return hmac.compare_digest(derived.hex(), expected)


def _seed_profile() -> tuple[AdminAccessProfile, str]:
    hashed = _hash_password(settings.admin_login_password, salt="neo-admin-seed")
    return AdminAccessProfile(login_email=settings.admin_login_email, source="seed"), hashed


def get_admin_access_profile() -> AdminAccessProfile:
    seed_profile, _ = _seed_profile()
    if not service_role_is_configured():
        return seed_profile
    try:
        rows = _rest_request("GET", "admin_access", query="?select=login_email&limit=1")
        if isinstance(rows, list) and rows:
            row = rows[0]
            return AdminAccessProfile(login_email=row.get("login_email") or seed_profile.login_email, source="supabase")
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        pass
    return seed_profile


def authenticate_admin(login_email: str, password: str) -> AdminLoginResult:
    email = login_email.strip().lower()
    if not email or not password:
        return AdminLoginResult(False, "warning", "Enter both your login email and password.", "", "Validation")

    seed_profile, seed_hash = _seed_profile()
    stored_email = seed_profile.login_email.lower()
    stored_hash = seed_hash
    source = "seed"

    if service_role_is_configured():
        try:
            rows = _rest_request("GET", "admin_access", query="?select=login_email,password_hash&limit=1")
            if isinstance(rows, list) and rows:
                row = rows[0]
                stored_email = (row.get("login_email") or stored_email).lower()
                stored_hash = row.get("password_hash") or stored_hash
                source = "supabase"
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass

    if email != stored_email or not _verify_password(password, stored_hash):
        return AdminLoginResult(False, "danger", "The login credentials did not match this admin workspace.", email, source.title())

    return AdminLoginResult(True, "success", "Signed in successfully.", stored_email, source.title())


def save_admin_access(*, login_email: str, password: str, confirm_password: str) -> AdminAccessSaveResult:
    email = login_email.strip().lower()
    if not email:
        return AdminAccessSaveResult(False, "warning", "A login email is required before saving admin access.", "Validation")

    if password and password != confirm_password:
        return AdminAccessSaveResult(False, "warning", "The new password and confirmation did not match.", "Validation")

    if not service_role_is_configured():
        return AdminAccessSaveResult(False, "info", "Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to manage admin access from the dashboard.", "Seed")

    seed_profile, seed_hash = _seed_profile()
    try:
        rows = _rest_request("GET", "admin_access", query="?select=id,password_hash&limit=1")
        if isinstance(rows, list) and rows:
            row = rows[0]
            next_hash = row.get("password_hash") or seed_hash
            if password:
                next_hash = _hash_password(password)
            _rest_request(
                "PATCH",
                "admin_access",
                payload={"login_email": email, "password_hash": next_hash},
                prefer="return=representation",
                query=f"?id=eq.{row['id']}",
            )
        else:
            _rest_request(
                "POST",
                "admin_access",
                payload={"login_email": email, "password_hash": _hash_password(password or settings.admin_login_password)},
                prefer="return=representation",
            )

        if password:
            message = "Admin login credentials saved."
        elif email != seed_profile.login_email.lower():
            message = "Admin login email saved. The existing password remains unchanged."
        else:
            message = "Admin login email saved."
        return AdminAccessSaveResult(True, "success", message, "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return AdminAccessSaveResult(False, "danger", f"Supabase rejected the admin access update. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return AdminAccessSaveResult(False, "danger", f"Could not reach Supabase to update admin access. {exc}", "Supabase")
