"""Media routes — workspace, search, upload, update, replace, delete."""

from __future__ import annotations

from typing import Any
from starlette.datastructures import UploadFile

try:
    from ..infrastructure.media_repository import delete_media_asset, replace_media_asset, update_media_asset, upload_media_asset
    from ..presentation.pages.media import _media_workspace_inner, media_workspace_page
except ImportError:
    from infrastructure.media_repository import delete_media_asset, replace_media_asset, update_media_asset, upload_media_asset
    from presentation.pages.media import _media_workspace_inner, media_workspace_page


def setup_media_routes(app: Any) -> None:
    @app.get("/media")
    def media(kind: str = "all", search: str = "") -> Any:
        return media_workspace_page(kind=kind, search=search)

    @app.get("/media/search")
    def media_search(kind: str = "all", search: str = "") -> Any:
        return _media_workspace_inner(kind=kind, search=search, message="", tone="info", public_url="")

    @app.post("/media/upload")
    def media_upload(
        title: str = "",
        kind: str = "image",
        alt_text: str = "",
        current_kind: str = "all",
        current_search: str = "",
        asset_file: UploadFile | None = None,
    ) -> Any:
        result = upload_media_asset(title=title, kind=kind, alt_text=alt_text, asset_file=asset_file)
        return _media_workspace_inner(
            kind=current_kind,
            search=current_search,
            message=result.message,
            tone=result.tone,
            public_url=result.public_url or "",
        )

    @app.post("/media/update")
    def media_update(asset_id: str = "", title: str = "", kind: str = "image", alt_text: str = "") -> Any:
        result = update_media_asset(asset_id=asset_id, title=title, kind=kind, alt_text=alt_text)
        return _media_workspace_inner(kind="all", search="", message=result.message, tone=result.tone, public_url=result.public_url or "")

    @app.post("/media/replace")
    def media_replace(asset_id: str = "", asset_file: UploadFile | None = None) -> Any:
        result = replace_media_asset(asset_id=asset_id, asset_file=asset_file)
        return _media_workspace_inner(kind="all", search="", message=result.message, tone=result.tone, public_url=result.public_url or "")

    @app.post("/media/delete")
    def media_delete(asset_id: str = "") -> Any:
        result = delete_media_asset(asset_id=asset_id)
        return _media_workspace_inner(kind="all", search="", message=result.message, tone=result.tone, public_url="")
