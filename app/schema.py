"""Schema-driven CRUD configuration for Neo Admin.

Define TableConfig and Field objects to auto-generate list/create/edit/delete
pages. Pattern inspired by datascience_admin's declarative approach.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field


# ── Field definition ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Field:
    """A single column/field in a resource table."""
    name: str
    label: str
    kind: str = "text"            # text, email, number, textarea, checkbox, select, choice, image, datetime
    required: bool = False
    full: bool = False            # full-width in form grid
    hidden: bool = False          # rendered as hidden input
    default: str | int | bool | None = None
    relation: str | None = None   # for select fields: key of another TABLES entry
    choices: tuple[tuple[str, str], ...] = ()  # for choice fields: (value, label) pairs
    readonly: bool = False        # display-only in edit mode
    placeholder: str = ""


# ── Table configuration ───────────────────────────────────────────────────

@dataclass(frozen=True)
class TableConfig:
    """Declarative configuration for a CRUD resource page."""
    key: str                      # URL segment and route key
    table: str                    # Supabase table name
    label: str                    # Human-readable name
    group: str                    # Sidebar group
    icon: str                     # Bootstrap icon name
    pk: str = "id"
    pk_kind: str = "generated"    # "generated" (uuid) or "text" (user-supplied)
    order: str = "created_at.desc"
    description: str = ""
    fields: tuple[Field, ...] = dc_field(default_factory=tuple)
    table_columns: tuple[str, ...] = dc_field(default_factory=tuple)
    readonly: bool = False        # view-only, no create/edit/delete


# ── Resource registry ─────────────────────────────────────────────────────

BLOG_POST_STATUS_CHOICES = (
    ("new", "New"),
    ("draft", "Draft"),
    ("published", "Published"),
    ("archived", "Archived"),
)

CONTACT_STATUS_CHOICES = (
    ("new", "New"),
    ("in_progress", "In Progress"),
    ("closed", "Closed"),
    ("spam", "Spam"),
)

BOOKING_STATUS_CHOICES = (
    ("new", "New"),
    ("reviewing", "Reviewing"),
    ("scheduled", "Scheduled"),
    ("closed", "Closed"),
    ("spam", "Spam"),
)


TABLES: dict[str, TableConfig] = {
    "blog_posts": TableConfig(
        key="blog_posts",
        table="blog_posts",
        label="Blog Posts",
        group="Content",
        icon="journal-richtext",
        pk="id",
        pk_kind="generated",
        order="created_at.desc",
        description="Manage portfolio blog posts and articles.",
        fields=(
            Field("title", "Title", required=True, full=True),
            Field("slug", "Slug", required=True, placeholder="auto-generated-if-blank"),
            Field("category", "Category", required=True, placeholder="e.g. Technology, Design"),
            Field("image_url", "Hero Image URL", kind="image", full=True),
            Field("summary", "Summary", kind="textarea", full=True, required=True),
            Field("content_html", "Content (HTML)", kind="textarea", full=True, required=True),
            Field("read_minutes", "Read Time (min)", kind="number", default=5),
            Field("published", "Published", kind="checkbox", default=False),
        ),
        table_columns=("title", "category", "read_minutes", "published"),
    ),
    "contact_submissions": TableConfig(
        key="contact_submissions",
        table="contact_submissions",
        label="Contact Submissions",
        group="Business",
        icon="envelope-paper",
        pk="id",
        pk_kind="generated",
        order="created_at.desc",
        readonly=True,
        description="Messages submitted from the public contact form.",
        fields=(
            Field("name", "Name", readonly=True),
            Field("email", "Email", kind="email", readonly=True),
            Field("subject", "Subject", readonly=True),
            Field("message", "Message", kind="textarea", full=True, readonly=True),
            Field("status", "Status", kind="choice", choices=CONTACT_STATUS_CHOICES),
            Field("notes", "Internal Notes", kind="textarea", full=True),
        ),
        table_columns=("name", "email", "subject", "status", "created_at"),
    ),
    "booking_requests": TableConfig(
        key="booking_requests",
        table="booking_requests",
        label="Booking Requests",
        group="Business",
        icon="calendar-check",
        pk="id",
        pk_kind="generated",
        order="created_at.desc",
        readonly=True,
        description="Project booking requests from the public intake form.",
        fields=(
            Field("name", "Name", readonly=True),
            Field("email", "Email", kind="email", readonly=True),
            Field("whatsapp", "WhatsApp", readonly=True),
            Field("service", "Service", readonly=True),
            Field("budget", "Budget", readonly=True),
            Field("timeline", "Timeline", readonly=True),
            Field("message", "Message", kind="textarea", full=True, readonly=True),
            Field("status", "Status", kind="choice", choices=BOOKING_STATUS_CHOICES),
            Field("notes", "Internal Notes", kind="textarea", full=True),
        ),
        table_columns=("name", "email", "service", "status", "created_at"),
    ),
}


# ── Navigation groups (auto-derived from TABLES) ──────────────────────────

def _build_nav_groups() -> dict[str, list[TableConfig]]:
    groups: dict[str, list[TableConfig]] = {}
    for cfg in TABLES.values():
        groups.setdefault(cfg.group, []).append(cfg)
    return groups

RESOURCE_NAV_GROUPS = _build_nav_groups()
