"""Repository boundary for reusable payment accounts."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import PaymentAccount, PaymentAccountSaveResult
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


def _rest_request(method: str, path: str, *, params: dict[str, str] | None = None, payload: object | None = None, prefer: str | None = None) -> object:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(prefer=prefer))
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _local_accounts() -> tuple[PaymentAccount, ...]:
    return (
        PaymentAccount(
            account_id="acct-local-main",
            label="Primary Business Account",
            bank_name="Access Bank",
            account_name="Olorundare Micheal",
            account_number="0000000000",
            note="Replace this local fallback with your real saved account in Supabase.",
            is_default=True,
            source="local",
        ),
    )


def _account_from_row(row: dict[str, object]) -> PaymentAccount:
    return PaymentAccount(
        account_id=str(row.get("id") or ""),
        label=str(row.get("label") or ""),
        bank_name=str(row.get("bank_name") or ""),
        account_name=str(row.get("account_name") or ""),
        account_number=str(row.get("account_number") or ""),
        note=str(row.get("note") or ""),
        is_default=bool(row.get("is_default")),
        source="supabase",
    )


def list_payment_accounts() -> tuple[PaymentAccount, ...]:
    if not service_role_is_configured():
        return _local_accounts()
    try:
        rows = _rest_request("GET", "payment_accounts", params={"select": "id,label,bank_name,account_name,account_number,note,is_default", "order": "created_at.asc"})
        if isinstance(rows, list) and rows:
            return tuple(_account_from_row(row) for row in rows)
    except (HTTPError, URLError, TimeoutError, ValueError):
        pass
    return _local_accounts()


def get_payment_account(account_id: str) -> PaymentAccount | None:
    for account in list_payment_accounts():
        if account.account_id == account_id:
            return account
    return None


def get_default_payment_account() -> PaymentAccount | None:
    accounts = list_payment_accounts()
    return next((account for account in accounts if account.is_default), accounts[0] if accounts else None)


def save_payment_account(
    *,
    label: str,
    bank_name: str,
    account_name: str,
    account_number: str,
    note: str,
    is_default: bool,
) -> PaymentAccountSaveResult:
    if not label.strip() or not bank_name.strip() or not account_name.strip() or not account_number.strip():
        return PaymentAccountSaveResult(False, "warning", "Label, bank name, account name, and account number are required.", "Validation")
    if not service_role_is_configured():
        return PaymentAccountSaveResult(False, "info", "Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable account saving.", "Local seed data")
    payload = {
        "label": label.strip(),
        "bank_name": bank_name.strip(),
        "account_name": account_name.strip(),
        "account_number": account_number.strip(),
        "note": note.strip(),
        "is_default": is_default,
    }
    try:
        if is_default:
            _rest_request("PATCH", "payment_accounts", payload={"is_default": False}, prefer="return=minimal")
        _rest_request("POST", "payment_accounts", payload=payload, prefer="return=representation")
        return PaymentAccountSaveResult(True, "success", "Payment account saved to Supabase.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return PaymentAccountSaveResult(False, "danger", f"Supabase rejected the payment account save request. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return PaymentAccountSaveResult(False, "danger", f"Could not reach Supabase to save the payment account. {exc}", "Supabase")
