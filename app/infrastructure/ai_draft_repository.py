"""Internal AI drafting helper for client documents."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.infrastructure.audit_repository import record_audit_event


_DRAFT_LIMITS: dict[str, list[float]] = {}
_MAX_DRAFTS_PER_WINDOW = 12
_DRAFT_WINDOW_SECONDS = 60 * 60


@dataclass(frozen=True)
class AiDraftResult:
    success: bool
    tone: str
    message: str
    draft: str = ""


def _check_limit(key: str) -> bool:
    now = time.time()
    recent = [item for item in _DRAFT_LIMITS.get(key, []) if now - item < _DRAFT_WINDOW_SECONDS]
    if len(recent) >= _MAX_DRAFTS_PER_WINDOW:
        _DRAFT_LIMITS[key] = recent
        return False
    recent.append(now)
    _DRAFT_LIMITS[key] = recent
    return True


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }


def _system_prompt() -> str:
    return (
        "You are an internal proposal assistant for a senior full-stack and AI systems portfolio admin. "
        "Draft client-ready commercial text only. Be specific, calm, concise, and professional. "
        "Do not invent legal guarantees, fake credentials, discounts, payment confirmations, or delivery dates. "
        "Use the provided deal context. Return editable plain text with clear sections."
    )


def _user_prompt(*, draft_kind: str, context: dict[str, str]) -> str:
    labels = {
        "proposal": "Draft a proposal scope and delivery plan.",
        "quote": "Draft a quotation summary with pricing assumptions and line-item framing.",
        "invoice": "Draft invoice wording, payment terms, and a concise client note.",
        "payment_terms": "Improve the payment terms and commercial boundaries.",
        "scope": "Improve the scope and deliverables section.",
    }
    task = labels.get(draft_kind, labels["proposal"])
    context_lines = "\n".join(f"{key}: {value}" for key, value in context.items() if value.strip())
    return f"{task}\n\nDeal context:\n{context_lines}\n\nReturn the draft only."


def generate_document_draft(*, draft_kind: str, context: dict[str, str], actor_email: str = "") -> AiDraftResult:
    if draft_kind not in {"proposal", "quote", "invoice", "payment_terms", "scope"}:
        return AiDraftResult(False, "warning", "Choose a valid AI draft type.")
    if not settings.groq_enabled:
        return AiDraftResult(False, "info", "Groq is not configured yet. Add GROQ_API_KEY to enable AI drafting.")
    limit_key = actor_email or "admin"
    if not _check_limit(limit_key):
        return AiDraftResult(False, "warning", "AI drafting is temporarily rate limited. Try again later.")
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(draft_kind=draft_kind, context=context)},
        ],
        "temperature": 0.35,
        "max_completion_tokens": 1400,
    }
    try:
        request = Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=_headers(),
        )
        with urlopen(request, timeout=35) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return AiDraftResult(False, "warning", "Groq returned an empty draft. Try again with more deal context.")
        record_audit_event(
            action="ai_document_draft_generated",
            target_type="client_document",
            actor_email=actor_email,
            detail=f"{draft_kind} via {settings.groq_model}",
        )
        return AiDraftResult(True, "success", "AI draft generated. Review and edit before saving or sending.", content)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return AiDraftResult(False, "danger", f"Groq rejected the draft request. {details or exc.reason}")
    except (URLError, TimeoutError, ValueError, KeyError) as exc:
        return AiDraftResult(False, "danger", f"Could not generate the AI draft. {exc}")
