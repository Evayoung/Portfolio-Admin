"""Theme tokens and Faststrap defaults for Neo Admin."""

from __future__ import annotations

from faststrap import create_theme, set_component_defaults

BRAND = {
    "primary": "#2DB8E8",
    "secondary": "#F3A53D",
    "success": "#6CD8A4",
    "info": "#7F9BFF",
    "warning": "#F2C35B",
    "danger": "#FF727E",
    "light": "#F4F8FB",
    "dark": "#091321",
}

NEO_ADMIN_THEME = create_theme(
    primary=BRAND["primary"],
    secondary=BRAND["secondary"],
    success=BRAND["success"],
    info=BRAND["info"],
    warning=BRAND["warning"],
    danger=BRAND["danger"],
    light=BRAND["light"],
    dark=BRAND["dark"],
)


def setup_theme_defaults() -> None:
    """Apply shared component defaults."""
    set_component_defaults("Button", size="md")
    set_component_defaults("Card", cls="border-0 shadow-sm")
    set_component_defaults("Badge", pill=True)
