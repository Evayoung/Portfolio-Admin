"""Supabase configuration helpers for Neo Admin."""

from __future__ import annotations

from app.config import settings


def supabase_is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_anon_key)


def service_role_is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def current_data_source_label() -> str:
    return "Supabase" if supabase_is_configured() else "Local seed data"
