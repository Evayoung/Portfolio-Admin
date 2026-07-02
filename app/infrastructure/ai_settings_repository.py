"""Repository boundary for AI provider settings."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.domain.models import AiProviderConfig, AiProviderSaveResult
from app.infrastructure.supabase_client import service_role_is_configured


GROQ_DEFAULT_URL = "https://api.groq.com/openai/v1"
OPENAI_DEFAULT_URL = "https://api.openai.com/v1"

PROVIDER_PRESETS = {
    "groq": ("Groq", GROQ_DEFAULT_URL),
    "openai": ("OpenAI", OPENAI_DEFAULT_URL),
    "custom": ("Custom", ""),
}


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


def _env_defaults() -> list[AiProviderConfig]:
    """Return providers derived from environment variables as fallback."""
    configs: list[AiProviderConfig] = []
    if settings.groq_api_key:
        configs.append(AiProviderConfig(
            config_id="env_groq",
            label="Groq (env)",
            provider_type="groq",
            base_url=GROQ_DEFAULT_URL,
            model=settings.groq_model,
            api_key="***configured***",
            is_default=not bool(settings.openai_api_key),
            source="env",
        ))
    if settings.openai_api_key:
        configs.append(AiProviderConfig(
            config_id="env_openai",
            label="OpenAI (env)",
            provider_type="openai",
            base_url=OPENAI_DEFAULT_URL,
            model=settings.openai_model or "gpt-4o",
            api_key="***configured***",
            is_default=not bool(settings.groq_api_key),
            source="env",
        ))
    if not configs:
        configs.append(AiProviderConfig(
            config_id="env_none",
            label="No provider",
            provider_type="groq",
            base_url=GROQ_DEFAULT_URL,
            model=settings.groq_model,
            api_key="",
            is_default=True,
            source="env",
        ))
    return configs


def get_ai_providers() -> list[AiProviderConfig]:
    """Load AI provider configs from Supabase, falling back to env vars."""
    if not service_role_is_configured():
        return _env_defaults()
    try:
        rows = _rest_request("GET", "ai_providers", query="?select=id,label,provider_type,base_url,model,api_key,is_default&order=created_at.asc")
        if not isinstance(rows, list) or not rows:
            return _env_defaults()
        return [
            AiProviderConfig(
                config_id=str(row.get("id", "")),
                label=row.get("label", ""),
                provider_type=row.get("provider_type", "custom"),
                base_url=row.get("base_url", ""),
                model=row.get("model", ""),
                api_key="***configured***" if row.get("api_key") else "",
                is_default=bool(row.get("is_default")),
                source="supabase",
            )
            for row in rows
        ]
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        return _env_defaults()


def get_active_provider() -> AiProviderConfig | None:
    """Return the default/active provider, falling back to env."""
    providers = get_ai_providers()
    for p in providers:
        if p.is_default:
            return p
    return providers[0] if providers else None


def get_provider_api_key(config_id: str) -> str:
    """Fetch the raw API key for a provider (masked in list)."""
    if not service_role_is_configured():
        if config_id == "env_groq":
            return settings.groq_api_key
        if config_id == "env_openai":
            return settings.openai_api_key or ""
        return ""
    try:
        rows = _rest_request("GET", "ai_providers", query=f"?select=api_key&id=eq.{config_id}&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0].get("api_key", "")
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        pass
    return ""


def save_ai_provider(
    *,
    config_id: str = "",
    label: str,
    provider_type: str,
    base_url: str,
    model: str,
    api_key: str,
    set_default: bool = False,
) -> AiProviderSaveResult:
    if not label.strip():
        return AiProviderSaveResult(False, "warning", "Provider label is required.", "Validation")
    if not base_url.strip():
        return AiProviderSaveResult(False, "warning", "Base URL is required for the provider endpoint.", "Validation")
    if not model.strip():
        return AiProviderSaveResult(False, "warning", "Model name is required.", "Validation")

    if not service_role_is_configured():
        return AiProviderSaveResult(False, "info", "Supabase write path is not configured. AI provider settings saved to env only — restart required.", "Local seed data")

    payload: dict[str, object] = {
        "label": label.strip(),
        "provider_type": provider_type.strip(),
        "base_url": base_url.strip(),
        "model": model.strip(),
        "is_default": set_default,
    }
    # Only update API key if a new one was provided (not the masked placeholder)
    if api_key.strip() and api_key.strip() != "***unchanged***":
        payload["api_key"] = api_key.strip()
    elif not api_key.strip() and config_id in ("", "new"):
        return AiProviderSaveResult(False, "warning", "API key is required.", "Validation")

    try:
        if set_default:
            _rest_request("PATCH", "ai_providers", payload={"is_default": False}, query="?is_default=eq.true")

        if config_id and config_id != "new":
            _rest_request("PATCH", "ai_providers", payload=payload, prefer="return=representation", query=f"?id=eq.{config_id}")
        else:
            _rest_request("POST", "ai_providers", payload=payload, prefer="return=representation")

        return AiProviderSaveResult(True, "success", f"AI provider '{label.strip()}' saved.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return AiProviderSaveResult(False, "danger", f"Supabase rejected the AI provider save. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return AiProviderSaveResult(False, "danger", f"Could not save AI provider. {exc}", "Supabase")


def delete_ai_provider(config_id: str) -> AiProviderSaveResult:
    if not service_role_is_configured():
        return AiProviderSaveResult(False, "info", "Supabase write path not configured.", "Local seed data")
    try:
        _rest_request("DELETE", "ai_providers", query=f"?id=eq.{config_id}")
        return AiProviderSaveResult(True, "success", "AI provider deleted.", "Supabase")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return AiProviderSaveResult(False, "danger", f"Supabase rejected the delete. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return AiProviderSaveResult(False, "danger", f"Could not delete AI provider. {exc}", "Supabase")
