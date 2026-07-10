"""Media workspace for reusable portfolio assets."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Img, Input, Label, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Modal, Row, SEO

from app.config import settings
from app.infrastructure.media_repository import get_media_workspace_summary, list_media_assets
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, action_group, action_link, floating_field, live_search_bar, loading_action_button, search_filter_bar, status_alert, summary_card, toggle_pill_group
from app.presentation.shell import page_frame


def media_save_status_fragment(title: str, message: str, tone: str = "info", public_url: str = "") -> Div:
    return Div(
        status_alert(title, message, tone),
        Div(
            Span("Uploaded URL", cls="admin-field-label"),
            A(public_url, href=public_url, target="_blank", rel="noreferrer", cls="admin-project-meta") if public_url else "",
            action_group(
                Button("Copy URL", type="button", cls="btn admin-module-btn", data_copy_target=public_url, data_copy_label="Copy URL"),
                action_link("Open Asset", public_url, variant="secondary", target="_blank"),
                action_link("Back to Images", "/media?kind=image", variant="secondary"),
            )
            if public_url
            else "",
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


def _asset_edit_modal(asset) -> Modal:
    mid = f"edit-{asset.asset_id}"
    return Modal(
        Form(
            Input(type="hidden", name="asset_id", value=asset.asset_id),
            floating_field("Asset Title", "title", asset.title, placeholder="Asset title", required=True),
            Div(
                Label("Asset Type", cls="admin-form-label"),
                toggle_pill_group("kind", _kind_options(), selected_value=asset.kind),
                cls="admin-form-group mt-3",
            ),
            floating_field("Alt Text / Notes", "alt_text", asset.alt_text, placeholder="Describe usage or accessibility text"),
            Div(
                loading_action_button("Save Metadata", endpoint="/media/update", target=f"#{mid}-status", button_cls="btn admin-install-btn"),
                cls="admin-form-actions mt-3",
            ),
            Div(id=f"{mid}-status", cls="mt-2"),
            action="/media/update",
            method="post",
            hx_post="/media/update",
            hx_target=f"#{mid}-status",
            hx_swap="innerHTML",
            cls="admin-settings-form",
        ),
        modal_id=mid,
        title=f"Edit: {asset.title}",
        size="lg",
        centered=True,
    )


def _asset_replace_modal(asset) -> Modal:
    mid = f"replace-{asset.asset_id}"
    return Modal(
        Form(
            Input(type="hidden", name="asset_id", value=asset.asset_id),
            Label("Replacement File", cls="admin-form-label"),
            Input(type="file", name="asset_file", required=True, cls="form-control admin-form-control"),
            P("Upload a new file to replace the existing asset. The public URL stays the same.", cls="admin-module-copy mt-2 mb-0"),
            Div(
                Button("Replace File", type="submit", cls="btn admin-install-btn"),
                Span(cls="spinner-border spinner-border-sm htmx-indicator ms-2", id=f"{mid}-spinner"),
                cls="admin-form-actions mt-3",
            ),
            Div(id=f"{mid}-status", cls="mt-2"),
            action="/media/replace",
            method="post",
            hx_post="/media/replace",
            hx_target=f"#{mid}-status",
            hx_swap="innerHTML",
            hx_indicator=f"#{mid}-spinner",
            enctype="multipart/form-data",
            cls="admin-settings-form",
        ),
        modal_id=mid,
        title=f"Replace: {asset.title}",
        size="lg",
        centered=True,
    )


def _asset_delete_modal(asset) -> Modal:
    mid = f"delete-{asset.asset_id}"
    return Modal(
        Form(
            Input(type="hidden", name="asset_id", value=asset.asset_id),
            P(f"Are you sure you want to delete \"{asset.title}\"? This removes the asset record and its storage object permanently.", cls="admin-module-copy"),
            Div(
                loading_action_button("Delete Asset", endpoint="/media/delete", target=f"#{mid}-status", button_cls="btn btn-outline-danger"),
                cls="admin-form-actions mt-3",
            ),
            Div(id=f"{mid}-status", cls="mt-2"),
            action="/media/delete",
            method="post",
            hx_post="/media/delete",
            hx_target=f"#{mid}-status",
            hx_swap="innerHTML",
            hx_confirm="Delete this asset permanently? This cannot be undone.",
            cls="admin-settings-form",
        ),
        modal_id=mid,
        title=f"Delete: {asset.title}",
        size="md",
        centered=True,
    )


def _asset_card(asset, *, modals: list) -> Card:
    size_kb = max(1, round(asset.size_bytes / 1024))
    is_image = (asset.content_type or "").startswith("image/")
    # Collect modals for this asset
    modals.append(_asset_edit_modal(asset))
    modals.append(_asset_replace_modal(asset))
    modals.append(_asset_delete_modal(asset))
    return Card(
        Div(
            Img(src=asset.public_url, alt=asset.alt_text or asset.title, cls="admin-media-thumb") if is_image and asset.public_url else "",
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
                Button("Copy URL", type="button", cls="btn admin-module-btn", data_copy_target=asset.public_url, data_copy_label="Copy URL"),
                Button("Edit", type="button", cls="btn admin-module-btn", data_bs_toggle="modal", data_bs_target=f"#edit-{asset.asset_id}"),
                Button("Replace", type="button", cls="btn admin-module-btn", data_bs_toggle="modal", data_bs_target=f"#replace-{asset.asset_id}"),
                Button("Delete", type="button", cls="btn btn-outline-danger", data_bs_toggle="modal", data_bs_target=f"#delete-{asset.asset_id}"),
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
            Input(type="file", name="asset_file", required=True, cls="form-control admin-form-control", data_preview_target="upload-preview-img"),
            Div(
                Img(src="", alt="Upload preview", cls="img-fluid mt-2 d-none rounded", id="upload-preview-img", style="max-height:200px;object-fit:contain;"),
                cls="text-center",
            ),
            P("Uploads go to Supabase Storage and return a reusable public URL for projects, blog posts, and documents.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-form-group mt-3",
        ),
        Div(
            Button("Upload Media", type="submit", cls="btn admin-module-btn"),
            Span(cls="spinner-border spinner-border-sm htmx-indicator ms-2", id="upload-spinner"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable uploads",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        action="/media/upload",
        method="post",
        hx_post="/media/upload",
        hx_target="#media-workspace-section",
        hx_swap="innerHTML",
        hx_indicator="#upload-spinner",
        enctype="multipart/form-data",
        cls="admin-settings-form",
    )


def _media_workspace_inner(*, kind: str, search: str, message: str, tone: str, public_url: str) -> Div:
    """Return just the workspace section content for HTMX partial swaps."""
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
    search_form = live_search_bar(
        endpoint="/media/search",
        target="#media-workspace-section",
        placeholder="Search title, alt text, or storage path",
        search_value=search,
        hidden_fields={"kind": kind},
        form_cls="admin-search-form admin-filter-bar mt-3",
    )

    modals: list[Modal] = []  # Collect asset modals

    library_panel = Card(
        Div(
            Div(
                H2("Asset Library", cls="admin-section-title"),
                P("Upload once, then reuse the public URL across projects, blog posts, CV downloads, and commercial documents.", cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            kind_links,
            search_form,
            Row(
                *[
                    Col(_asset_card(asset, modals=modals), span=12, md=6, xl=4)
                    for asset in assets
                ],
                cls="g-4 mt-1",
            )
            if assets
            else EmptyState(
                icon="images",
                title="No assets in this view yet",
                description="Upload your first reusable media file or adjust the filter.",
                cls="py-5",
            ),
            *modals,  # Render modals after the grid
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
        id="media-upload-panel",
    )

    return Div(
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
        id="media-workspace-section",
    )


def media_workspace_page(*, kind: str = "all", search: str = "", message: str = "", tone: str = "info", public_url: str = "") -> tuple:
    summary = get_media_workspace_summary()

    return (
        *SEO(
            title=f"{settings.app_name} | Media",
            description="Reusable media workspace for portfolio assets and uploads.",
            url=f"{settings.base_url}/media",
        ),
        *page_frame(
            _media_workspace_inner(kind=kind, search=search, message=message, tone=tone, public_url=public_url),
            current="/media",
            title="Media",
        ),
    )
