"""Media workspace for reusable portfolio assets."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, H3, Input, Label, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.infrastructure.media_repository import get_media_workspace_summary, list_media_assets
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import floating_field, search_filter_bar, status_alert, summary_card, toggle_pill_group
from app.presentation.pages.dashboard import SectionWrap
from app.presentation.shell import page_frame


def media_save_status_fragment(title: str, message: str, tone: str = "info", public_url: str = "") -> Div:
    return Div(
        status_alert(title, message, tone),
        Div(
            Span("Uploaded URL", cls="admin-field-label"),
            A(public_url, href=public_url, target="_blank", rel="noreferrer", cls="admin-project-meta") if public_url else "",
            cls="admin-detail-block mt-3",
        )
        if public_url
        else "",
    )


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(label, href=href, cls=f"admin-filter-chip{' active' if active else ''}")


def _kind_options() -> list[tuple[str, str]]:
    return [
        ("image", "Image"),
        ("document", "Document"),
        ("logo", "Logo"),
        ("resume", "Resume"),
        ("other", "Other"),
    ]


def _asset_card(asset) -> Card:
    size_kb = max(1, round(asset.size_bytes / 1024))
    return Card(
        Div(
            Div(
                Span(asset.kind.title(), cls="admin-project-category"),
                Badge(asset.created_at or "Recent", cls="text-bg-secondary admin-project-flag"),
                cls="d-flex justify-content-between align-items-start gap-2",
            ),
            H3(asset.title, cls="admin-project-title"),
            P(asset.alt_text or asset.storage_path, cls="admin-project-copy"),
            Div(
                Span(asset.content_type, cls="admin-project-meta"),
                Span(f"{size_kb} KB", cls="admin-project-meta"),
                cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
            ),
            Div(
                A("Open Asset", href=asset.public_url, target="_blank", rel="noreferrer", cls="btn admin-install-btn"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            cls="admin-project-card-body",
        ),
        cls="admin-surface-card admin-project-card h-100",
    )


def _upload_form(*, kind: str, search: str) -> Form:
    return Form(
        Input(type="hidden", name="current_kind", value=kind),
        Input(type="hidden", name="current_search", value=search),
        floating_field("Asset Title", "title", "", placeholder="Homepage hero visual", required=True),
        Div(
            Label("Asset Type", cls="admin-form-label"),
            toggle_pill_group("kind", _kind_options(), selected_value="image" if kind == "all" else kind),
            cls="admin-form-group mt-3",
        ),
        floating_field("Alt Text / Notes", "alt_text", "", placeholder="Describe the image or how the file should be used"),
        Div(
            Label("Asset File", cls="admin-form-label"),
            Input(type="file", name="asset_file", required=True, cls="form-control admin-form-control"),
            P("Uploads go to Supabase Storage and return a reusable public URL for projects, blog posts, and documents.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-form-group mt-3",
        ),
        Div(
            Input(type="submit", value="Upload Media", cls="btn admin-module-btn"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable uploads",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        action="/media/upload",
        method="post",
        enctype="multipart/form-data",
        cls="admin-settings-form",
    )


def media_workspace_page(*, kind: str = "all", search: str = "", message: str = "", tone: str = "info", public_url: str = "") -> tuple:
    assets = list_media_assets(kind=kind, search=search)
    summary = get_media_workspace_summary()

    kind_links = Div(
        _filter_link("All", f"/media?kind=all&search={search}", active=kind == "all"),
        _filter_link("Images", f"/media?kind=image&search={search}", active=kind == "image"),
        _filter_link("Docs", f"/media?kind=document&search={search}", active=kind == "document"),
        _filter_link("Logos", f"/media?kind=logo&search={search}", active=kind == "logo"),
        _filter_link("Resume", f"/media?kind=resume&search={search}", active=kind == "resume"),
        cls="admin-filter-row",
    )
    search_form = search_filter_bar(
        endpoint="/media",
        placeholder="Search title, alt text, or storage path",
        search_value=search,
        hidden_fields={"kind": kind},
        form_cls="admin-search-form admin-filter-bar mt-3",
    )

    library_panel = Card(
        Div(
            Div(
                H2("Asset Library", cls="admin-section-title"),
                P("Upload once, then reuse the public URL across projects, blog posts, CV downloads, and commercial documents.", cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            kind_links,
            search_form,
            Div(
                *[
                    Col(_asset_card(asset), span=12, md=6, xl=4)
                    for asset in assets
                ],
                cls="g-4 mt-1 row",
            )
            if assets
            else EmptyState(
                icon="images",
                title="No assets in this view yet",
                description="Upload your first reusable media file or adjust the filter.",
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    upload_panel = Card(
        Div(
            H3("Upload Workspace", cls="admin-subsection-title"),
            P("This becomes the source of truth for visuals and downloadable assets. After upload, paste the generated URL into project, blog, or document records.", cls="admin-module-copy"),
            media_save_status_fragment("Upload status", message, tone, public_url) if message else "",
            _upload_form(kind=kind, search=search),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Media",
            description="Reusable media workspace for portfolio assets and uploads.",
            url=f"{settings.base_url}/media",
        ),
        *page_frame(
            Row(
                summary_card("Total Assets", str(summary.total), "Reusable files tracked in Supabase Storage."),
                summary_card("Images", str(summary.images), "Visual assets for projects, blog posts, and page surfaces."),
                summary_card("Documents", str(summary.documents), "PDFs, resumes, and other downloadable files."),
                cls="g-4",
            ),
            SectionWrap(
                "Media Workspace",
                Row(
                    Col(library_panel, span=12, lg=7),
                    Col(upload_panel, span=12, lg=5, cls="mt-4 mt-lg-0"),
                    cls="g-4",
                ),
            ),
            current="/media",
            title="Media",
        ),
    )
