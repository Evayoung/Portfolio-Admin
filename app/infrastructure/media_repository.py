"""Repository boundary for media uploads and library records."""

from __future__ import annotations

import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from starlette.datastructures import UploadFile

from app.config import settings
from app.domain.models import AdminMediaAsset, MediaSaveResult, MediaWorkspaceSummary
from app.infrastructure.supabase_client import service_role_is_configured, supabase_is_configured


BUCKET_NAME = "portfolio-media"


def _rest_headers(*, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _rest_request(
    method: str,
    path: str,
    *,
    params: dict[str, str] | None = None,
    payload: object | None = None,
    prefer: str | None = None,
) -> object:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}{query}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_rest_headers(prefer=prefer))
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))


def _storage_headers(content_type: str) -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }


def _storage_upload(path: str, payload: bytes, content_type: str) -> None:
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{BUCKET_NAME}/{quote(path, safe='/')}"
    request = Request(url, data=payload, method="POST", headers=_storage_headers(content_type))
    with urlopen(request, timeout=30) as response:
        response.read()


def _public_url(path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{BUCKET_NAME}/{quote(path, safe='/')}"


def _asset_from_row(row: dict[str, object]) -> AdminMediaAsset:
    return AdminMediaAsset(
        asset_id=str(row.get("id") or ""),
        title=str(row.get("title") or ""),
        kind=str(row.get("asset_kind") or "image"),
        alt_text=str(row.get("alt_text") or ""),
        public_url=str(row.get("public_url") or ""),
        storage_path=str(row.get("storage_path") or ""),
        content_type=str(row.get("content_type") or ""),
        size_bytes=int(row.get("size_bytes") or 0),
        created_at=str(row.get("created_at") or "")[:10],
        source="supabase",
    )


def list_media_assets(*, kind: str = "all", search: str = "") -> tuple[AdminMediaAsset, ...]:
    if not supabase_is_configured():
        return ()
    try:
        rows = _rest_request(
            "GET",
            "media_assets",
            params={"select": "id,title,asset_kind,alt_text,public_url,storage_path,content_type,size_bytes,created_at", "order": "created_at.desc"},
        )
    except (HTTPError, URLError, TimeoutError, ValueError):
        return ()
    if not isinstance(rows, list):
        return ()
    items = tuple(_asset_from_row(row) for row in rows)
    if kind != "all":
        items = tuple(item for item in items if item.kind == kind)
    if search.strip():
        query = search.strip().lower()
        items = tuple(
            item
            for item in items
            if query in item.title.lower()
            or query in item.alt_text.lower()
            or query in item.storage_path.lower()
        )
    return items


def get_media_workspace_summary() -> MediaWorkspaceSummary:
    items = list_media_assets()
    return MediaWorkspaceSummary(
        total=len(items),
        images=sum(1 for item in items if item.kind == "image"),
        documents=sum(1 for item in items if item.kind == "document" or item.kind == "resume"),
        source="Supabase" if items else "Supabase" if supabase_is_configured() else "Local",
    )


def _safe_stem(name: str) -> str:
    stem = Path(name).stem or "asset"
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower()
    return cleaned or "asset"


def upload_media_asset(
    *,
    title: str,
    kind: str,
    alt_text: str,
    asset_file: UploadFile | None,
) -> MediaSaveResult:
    if not title.strip():
        return MediaSaveResult(False, "warning", "Add a title before uploading media.", "Validation")
    if kind not in {"image", "document", "logo", "resume", "other"}:
        return MediaSaveResult(False, "warning", "Choose a valid asset type.", "Validation")
    if asset_file is None or not getattr(asset_file, "filename", ""):
        return MediaSaveResult(False, "warning", "Choose a file to upload first.", "Validation")
    if not service_role_is_configured():
        return MediaSaveResult(False, "info", "Supabase write path is not configured yet. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable media uploads.", "Local seed data")

    filename = str(asset_file.filename or "asset")
    content = asset_file.file.read()
    if not content:
        return MediaSaveResult(False, "warning", "The selected file is empty.", "Validation")
    content_type = getattr(asset_file, "content_type", "") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    extension = Path(filename).suffix.lower()
    safe_name = _safe_stem(filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    storage_path = f"{kind}/{timestamp}-{safe_name}{extension}"
    public_url = _public_url(storage_path)

    try:
        _storage_upload(storage_path, content, content_type)
        payload = {
            "title": title.strip(),
            "asset_kind": kind,
            "alt_text": alt_text.strip(),
            "bucket_name": BUCKET_NAME,
            "storage_path": storage_path,
            "public_url": public_url,
            "content_type": content_type,
            "size_bytes": len(content),
        }
        _rest_request("POST", "media_assets", payload=payload, prefer="return=representation")
        return MediaSaveResult(True, "success", "Media uploaded successfully. You can now reuse the public URL across projects, blog posts, and documents.", "Supabase", public_url=public_url)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        return MediaSaveResult(False, "danger", f"Supabase rejected the media upload. {details or exc.reason}", "Supabase")
    except (URLError, TimeoutError, ValueError) as exc:
        return MediaSaveResult(False, "danger", f"Could not reach Supabase to upload media. {exc}", "Supabase")
