"""Media workspace for reusable portfolio assets."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, H3, Img, Input, Label, P, Span, Strong
from faststrap import Badge, Button, Card, Col, EmptyState, Fx, Icon, Modal, Row, SEO
from faststrap.components.feedback.confirm import ConfirmDialog

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
                Button(Icon("clipboard"), type="button", cls="btn admin-icon-btn", aria_label="Copy asset URL", title="Copy asset URL", data_copy_target=public_url, data_copy_label="Copy URL"),
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
    return A(label, href=href, aria_label=f"Filter: {label}", cls=f"admin-filter-chip{' active' if active else ''}")


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


def _asset_delete_modal(asset) -> ConfirmDialog:
    return ConfirmDialog(
        f"Are you sure you want to delete \"{asset.title}\"? This removes the asset record and its storage object permanently.",
        confirm_text="Delete Asset",
        cancel_text="Cancel",
        title=f"Delete Asset: {asset.title}",
        variant="danger",
        dialog_id=f"delete-{asset.asset_id}",
        hx_confirm_method="post",
        hx_confirm_url=f"/media/delete?asset_id={asset.asset_id}",
    )


def _asset_card(asset, modals: list) -> Card:
    is_image = asset.kind in ("image", "logo")
    size_kb = round(asset.size_bytes / 1024, 1) if asset.size_bytes else 0
    # Collect modals for this asset
    modals.append(_asset_edit_modal(asset))
    modals.append(_asset_replace_modal(asset))
    modals.append(_asset_delete_modal(asset))
    return Card(
        Div(
            Div(
                Div(
                    Img(src=asset.public_url, alt=asset.alt_text or asset.title, cls="admin-media-thumb")
                    if is_image and asset.public_url
                    else Div(Icon("file-earmark"), Span(asset.content_type or "File", cls="admin-project-meta"), cls="admin-media-thumb admin-media-file-thumb"),
                    cls="admin-media-preview",
                ),
                Div(
                    Div(Span(asset.kind.title(), cls="admin-project-category"), Span(asset.created_at or "Recent", cls="admin-project-meta"), cls="d-flex justify-content-between align-items-center gap-2 mb-2"),
                    H3(asset.title, cls="admin-project-title mb-1"),
                    P(asset.alt_text or "Ready to reuse across your portfolio pages.", cls="admin-project-copy mb-2"),
                    Span(f"{asset.content_type} · {size_kb} KB", cls="admin-project-meta"),
                    cls="admin-media-card-copy",
                ),
                cls="admin-media-card-content",
            ),
            Div(
                A(Icon("box-arrow-up-right"), href=asset.public_url, target="_blank", rel="noreferrer", cls="btn admin-muted-btn admin-icon-btn", aria_label=f"Open {asset.title}", title="Open asset") if asset.public_url else "",
                Button(Icon("clipboard"), type="button", cls="btn admin-module-btn admin-icon-btn", aria_label=f"Copy URL for {asset.title}", title="Copy URL", data_copy_target=asset.public_url, data_copy_label="Copy URL") if asset.public_url else "",
                Div(
                    Button(Icon("three-dots"), type="button", cls="btn admin-muted-btn admin-icon-btn dropdown-toggle", data_bs_toggle="dropdown", aria_label=f"Manage {asset.title}", title="Manage asset", aria_expanded="false"),
                    Div(
                        Button("Edit details", type="button", cls="dropdown-item", data_bs_toggle="modal", data_bs_target=f"#edit-{asset.asset_id}"),
                        Button("Replace file", type="button", cls="dropdown-item", data_bs_toggle="modal", data_bs_target=f"#replace-{asset.asset_id}"),
                        Div(cls="dropdown-divider"),
                        Button("Delete", type="button", cls="dropdown-item text-danger", data_bs_toggle="modal", data_bs_target=f"#delete-{asset.asset_id}"),
                        cls="dropdown-menu dropdown-menu-end",
                    ),
                    cls="dropdown ms-auto",
                ),
                cls="admin-media-card-actions d-flex align-items-center gap-2 mt-3 pt-3 border-top border-secondary border-opacity-10",
            ),
            cls="admin-media-card-body",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card admin-media-asset-card h-100"],
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
                P("A visual shelf for project covers, article artwork, logos, and client downloads. Upload once, then copy an asset URL wherever you need it.", cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            kind_links,
            search_form,
            Row(
                *[_asset_card(asset, modals=modals) for asset in assets],
                cols=1,
                cols_xl=2,
                g=3,
                cls="mt-1",
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
            P("Upload once, then select the image from the Home Page or Projects editor. The same public URL can also be used in blog and document records.", cls="admin-module-copy"),
            media_save_status_fragment("Upload status", message, tone, public_url) if message else "",
            _upload_form(kind=kind, search=search),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
        id="media-upload-panel",
    )

    return Div(
        Card(
            Div(
                Div(
                    H3("Use media across your site", cls="admin-subsection-title mb-1"),
                    P("Manage files here, edit homepage copy and image assignments in Home Page, and choose a cover image for each project in Projects.", cls="admin-module-copy mb-0"),
                ),
                Div(
                    A(Icon("window-stack"), " Home Page", href="/website-content", cls="btn admin-muted-btn"),
                    A(Icon("kanban"), " Project Images", href="/projects", cls="btn admin-muted-btn"),
                    cls="d-flex flex-wrap gap-2 mt-3 mt-lg-0",
                ),
                cls="d-flex flex-column flex-lg-row justify-content-between align-items-start align-items-lg-center gap-3",
            ),
            cls="admin-surface-card mb-4",
        ),
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
                Col(upload_panel, span=12, lg=5),
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
