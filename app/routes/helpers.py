"""Shared helpers for route modules."""

from __future__ import annotations


def _safe_next_path(next_path: str) -> str:
    candidate = (next_path or "/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return candidate
