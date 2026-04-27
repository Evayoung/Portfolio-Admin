"""Small domain models for the admin dashboard shell."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdminMetric:
    label: str
    value: str
    delta: str
    tone: str


@dataclass(frozen=True)
class AdminModule:
    title: str
    description: str
    href: str
    count: str
    icon: str


@dataclass(frozen=True)
class ActivityItem:
    title: str
    detail: str
    status: str


@dataclass(frozen=True)
class AdminProject:
    slug: str
    title: str
    category: str
    summary: str
    narrative: str
    tech: tuple[str, ...]
    image: str
    complexity: int
    satisfaction: int
    featured: bool
    published: bool
    source: str


@dataclass(frozen=True)
class ProjectWorkspaceSummary:
    total: int
    featured: int
    categories: int
    source: str


@dataclass(frozen=True)
class ProjectSaveResult:
    success: bool
    tone: str
    message: str
    source: str
    slug: str | None = None


@dataclass(frozen=True)
class AdminBlogPost:
    slug: str
    title: str
    category: str
    summary: str
    content_html: str
    published: str
    read_minutes: int
    tags: tuple[str, ...]
    image: str
    source: str


@dataclass(frozen=True)
class BlogWorkspaceSummary:
    total: int
    categories: int
    published: int
    source: str


@dataclass(frozen=True)
class BlogSaveResult:
    success: bool
    tone: str
    message: str
    source: str
    slug: str | None = None


@dataclass(frozen=True)
class AdminCvMeta:
    name: str
    role: str
    email: str
    phone: str
    whatsapp: str
    location: str
    github: str
    linkedin: str
    summary: str
    source: str


@dataclass(frozen=True)
class CvWorkspaceSummary:
    work_items: int
    certifications: int
    tool_groups: int
    source: str


@dataclass(frozen=True)
class CvSaveResult:
    success: bool
    tone: str
    message: str
    source: str


@dataclass(frozen=True)
class AdminSubmission:
    entry_id: str
    kind: str
    name: str
    email: str
    phone: str
    subject: str
    service: str
    budget: str
    timeline: str
    message: str
    status: str
    notes: str
    created_at: str
    source: str


@dataclass(frozen=True)
class SubmissionWorkspaceSummary:
    total: int
    new_items: int
    booking_items: int
    contact_items: int
    source: str
    note: str


@dataclass(frozen=True)
class SubmissionSaveResult:
    success: bool
    tone: str
    message: str
    source: str


@dataclass(frozen=True)
class AdminSiteProfile:
    site_name: str
    site_url: str
    full_name: str
    role: str
    email: str
    phone: str
    whatsapp: str
    location: str
    github: str
    linkedin: str
    seo_title: str
    seo_description: str
    source: str


@dataclass(frozen=True)
class SiteSettingsSaveResult:
    success: bool
    tone: str
    message: str
    source: str
