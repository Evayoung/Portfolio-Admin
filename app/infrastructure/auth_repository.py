"""Simple admin access management with env-seeded fallback."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AdminAccessProfile, AdminAccessSaveResult, AdminLoginResult
from app.infrastructure.audit_repository import record_audit_event
from app.infrastructure.supabase_client import service_role_is_configured

_LOGIN_FAILURES: dict[str, tuple[int, float]] = {}  # keyed by email
_IP_FAILURES: dict[str, tuple[int, float]] = {}       # keyed by IP address
_MAX_LOGIN_FAILURES = 4          # attempts before lockout (per email)
_MAX_IP_FAILURES = 8             # attempts before IP lockout
_LOCKOUT_SECONDS = 30 * 60      # 30-minute lockout

# Seed password hash — computed once with a random salt (not hardcoded)
_SEED_SALT = secrets.token_hex(16)
_SEED_HASH: str = ""


def _seed_profile() -> tuple[AdminAccessProfile, str]:
    global _SEED_HASH
    if not _SEED_HASH:
        _SEED_HASH = _hash_password(settings.admin_login_password, salt=_SEED_SALT)
    return AdminAccessProfile(login_email=settings.admin_login_email, source="seed"), _SEED_HASH


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


def get_admin_access_profile() -> AdminAccessProfile:
    seed_profile, _ = _seed_profile()
    if not service_role_is_configured():
        return seed_profile
    try:
        rows = _rest_request("GET", "admin_access", query="?select=login_email&limit=1")
        if isinstance(rows, list) and rows:
            row = rows[0]
            login_email = (row.get("login_email") or "").strip().lower()
            if login_email:
                return AdminAccessProfile(login_email=login_email, source="supabase")
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        pass
    return seed_profile


def authenticate_admin(login_email: str, password: str, *, ip: str = "") -> AdminLoginResult:
    email = login_email.strip().lower()
    if not email or not password:
        return AdminLoginResult(False, "warning", "Enter both your login email and password.", "", "Validation")

    # --- IP-level lockout (blocks rotating-email attacks) ---
    if ip:
        ip_failures, ip_locked_until = _IP_FAILURES.get(ip, (0, 0.0))
        if ip_failures >= _MAX_IP_FAILURES and ip_locked_until > time.time():
            return AdminLoginResult(False, "danger", "Too many failed attempts from your location. Please wait before trying again.", email, "Rate Limit")

    # --- Email-level lockout ---
    failures, locked_until = _LOGIN_FAILURES.get(email, (0, 0.0))
    if failures >= _MAX_LOGIN_FAILURES and locked_until > time.time():
        return AdminLoginResult(False, "danger", "Too many failed attempts. Try again in 30 minutes.", email, "Rate Limit")

    seed_profile, seed_hash = _seed_profile()
    stored_email = seed_profile.login_email.lower()
    stored_hash = seed_hash
    source = "seed"

    if service_role_is_configured():
        try:
            rows = _rest_request("GET", "admin_access", query="?select=login_email,password_hash&limit=1")
            if isinstance(rows, list) and rows:
                row = rows[0]
                row_email = (row.get("login_email") or "").strip().lower()
                row_hash = (row.get("password_hash") or "").strip()
                if row_email and row_hash:
                    stored_email = row_email
                    stored_hash = row_hash
                    source = "supabase"
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            pass

    if email != stored_email or not _verify_password(password, stored_hash):
        current_failures = failures + 1
        lock_until = time.time() + _LOCKOUT_SECONDS if current_failures >= _MAX_LOGIN_FAILURES else 0.0
        _LOGIN_FAILURES[email] = (current_failures, lock_until)
        # Track IP failures too
        if ip:
            ip_current = _IP_FAILURES.get(ip, (0, 0.0))[0] + 1
            ip_lock = time.time() + _LOCKOUT_SECONDS if ip_current >= _MAX_IP_FAILURES else 0.0
            _IP_FAILURES[ip] = (ip_current, ip_lock)
        return AdminLoginResult(False, "danger", "The login credentials did not match this admin workspace.", email, source.title())

    _LOGIN_FAILURES.pop(email, None)
    if ip:
        _IP_FAILURES.pop(ip, None)
    return AdminLoginResult(True, "success", "Signed in successfully.", stored_email, source.title())


def save_admin_access(*, login_email: str, password: str, confirm_password: str) -> AdminAccessSaveResult:
    email = login_email.strip().lower()
    if not email:
        return AdminAccessSaveResult(False, "warning", "A login email is required before saving admin access.", "Validation")

    if password and password != confirm_password:
        return AdminAccessSaveResult(False, "warning", "The new password and confirmation did not match.", "Validation")
    if password and len(password) < 10:
        return AdminAccessSaveResult(False, "warning", "Use at least 10 characters for the new admin password.", "Validation")

    if not service_role_is_configured():
        return AdminAccessSaveResult(False, "info", "Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to manage admin access from the dashboard.", "Seed")

    seed_profile, seed_hash = _seed_profile()
    try:
        rows = _rest_request("GET", "admin_access", query="?select=id,password_hash,login_email&limit=1")
        if isinstance(rows, list) and rows:
            row = rows[0]
            row_id = str(row.get("id") or "")
            if not row_id:
                return AdminAccessSaveResult(False, "danger", "Supabase returned an admin access row without an id. Check the admin_access table schema.", "Supabase")
            next_hash = row.get("password_hash") or seed_hash
            if password:
                next_hash = _hash_password(password)
            _rest_request(
                "PATCH",
                "admin_access",
                payload={"login_email": email, "password_hash": next_hash},
                prefer="return=representation",
                query=f"?id=eq.{row_id}",
            )
        else:
            _rest_request(
                "POST",
                "admin_access",
                payload={"login_email": email, "password_hash": _hash_password(password or settings.admin_login_password)},
                prefer="return=representation",
            )

        record_audit_event(
            action="admin_access_updated",
            target_type="admin_access",
            actor_email=email,
            detail="Admin login email/password was updated." if password else "Admin login email was updated.",
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
