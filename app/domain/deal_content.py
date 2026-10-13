"""Shared parsing helpers for deal and client-document content."""

from __future__ import annotations

import json
from typing import Any


def parse_document_sections(raw: str | None) -> list[dict[str, Any]]:
    """Return valid document sections from a JSON payload.

    Sections are stored as JSON so proposals can render rich narrative content.
    This parser is intentionally forgiving: malformed JSON, non-list payloads,
    and non-dict list items are ignored instead of crashing admin/public views.
    """
    if not raw or not str(raw).strip():
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []

    sections: list[dict[str, Any]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or "").strip()
        if not title and not content:
            continue
        try:
            order = int(item.get("order") or index + 1)
        except (TypeError, ValueError):
            order = index + 1
        sections.append({"order": order, "title": title, "content": content})
    return sorted(sections, key=lambda section: section["order"])


def serialize_document_sections(raw: str | None) -> str:
    """Normalize a sections JSON payload for persistence."""
    sections = parse_document_sections(raw)
    return json.dumps(sections) if sections else ""
