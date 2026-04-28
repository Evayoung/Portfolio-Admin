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
class DealDocument:
    document_id: str
    kind: str
    status: str
    title: str
    document_number: str
    public_token: str
    payment_account_id: str
    total_amount: int
    valid_until: str
    due_date: str
    updated_at: str


@dataclass(frozen=True)
class AdminDeal:
    deal_id: str
    client_name: str
    client_email: str
    client_phone: str
    company: str
    project_title: str
    service_type: str
    stage: str
    summary: str
    background_text: str
    scope_notes: str
    option_notes_text: str
    tech_stack: tuple[str, ...]
    timeline_text: str
    payment_terms: str
    line_items_text: str
    exclusions_text: str
    closing_note: str
    amount_ngn: int
    deposit_percent: int
    source: str
    documents: tuple[DealDocument, ...]
    latest_document: DealDocument | None


@dataclass(frozen=True)
class DealWorkspaceSummary:
    total: int
    proposals: int
    quotes: int
    invoices: int
    source: str


@dataclass(frozen=True)
class DealSaveResult:
    success: bool
    tone: str
    message: str
    source: str
    deal_id: str | None = None


@dataclass(frozen=True)
class AdminMediaAsset:
    asset_id: str
    title: str
    kind: str
    alt_text: str
    public_url: str
    storage_path: str
    content_type: str
    size_bytes: int
    created_at: str
    source: str


@dataclass(frozen=True)
class MediaWorkspaceSummary:
    total: int
    images: int
    documents: int
    source: str


@dataclass(frozen=True)
class MediaSaveResult:
    success: bool
    tone: str
    message: str
    source: str
    public_url: str | None = None


@dataclass(frozen=True)
class PaymentAccount:
    account_id: str
    label: str
    bank_name: str
    account_name: str
    account_number: str
    note: str
    is_default: bool
    source: str


@dataclass(frozen=True)
class PaymentAccountSaveResult:
    success: bool
    tone: str
    message: str
    source: str


@dataclass(frozen=True)
class ClientDocumentResponse:
    response_id: str
    action: str
    comment: str
    responder_name: str
    created_at: str


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


@dataclass(frozen=True)
class AdminAccessProfile:
    login_email: str
    source: str


@dataclass(frozen=True)
class AdminAccessSaveResult:
    success: bool
    tone: str
    message: str
    source: str


@dataclass(frozen=True)
class AdminLoginResult:
    success: bool
    tone: str
    message: str
    login_email: str
    source: str
