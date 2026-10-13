"""Copy bundled NeoPortfolio images into Supabase Storage and repoint content.

Default mode is a local dry-run. Use --apply only after migrations 004 and 012
are applied in the intended Supabase project and its content has been backed up.
The original public files remain in place as a rollback and offline fallback.
"""

from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path

from app.config import settings
from app.infrastructure.media_repository import BUCKET_NAME, _public_url, _rest_request, _storage_upload
from app.infrastructure.supabase_client import service_role_is_configured


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "neoportfolio" / "assets" / "images"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


def _assets(source: Path) -> tuple[Path, ...]:
    resolved = source.resolve()
    if not resolved.is_dir():
        raise SystemExit(f"Image directory does not exist: {resolved}")
    return tuple(sorted(path for path in resolved.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES))


def _upload(path: Path) -> str:
    storage_path = f"legacy-public-assets/{path.name}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = path.read_bytes()
    _storage_upload(storage_path, payload, content_type)
    record = {
        "title": path.stem.replace("-", " ").replace("_", " ").title(),
        "asset_kind": "image",
        "alt_text": path.stem.replace("-", " ").replace("_", " ").title(),
        "bucket_name": BUCKET_NAME,
        "storage_path": storage_path,
        "public_url": _public_url(storage_path),
        "content_type": content_type,
        "size_bytes": len(payload),
    }
    _rest_request(
        "POST", "media_assets", params={"on_conflict": "storage_path"}, payload=record,
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return record["public_url"]


def _replace_references(mapping: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    targets = {
        "projects": ("image_url",),
        "blog_posts": ("image_url",),
        "site_home_content": (
            "profile_image_url", "hero_background_url", "booking_background_url", "cv_background_url",
        ),
    }
    for table, columns in targets.items():
        updated = 0
        for old_url, new_url in mapping.items():
            for column in columns:
                rows = _rest_request(
                    "PATCH", table, params={column: f"eq.{old_url}"}, payload={column: new_url},
                    prefer="return=representation",
                )
                updated += len(rows) if isinstance(rows, list) else 0
        counts[table] = updated
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Bundled public image directory")
    parser.add_argument("--apply", action="store_true", help="Upload files and repoint matching database URLs")
    args = parser.parse_args()
    images = _assets(args.source)
    if not images:
        print("No supported image assets found.")
        return 0
    total_bytes = sum(path.stat().st_size for path in images)
    print(f"Found {len(images)} image assets ({total_bytes:,} bytes) in {args.source.resolve()}")
    for path in images:
        print(f"  {path.name} ({path.stat().st_size:,} bytes)")
    if not args.apply:
        print("Dry run only. Apply migrations 004 and 012, back up the target content, then pass --apply to upload and repoint matching URLs.")
        return 0
    if not settings.supabase_url or not service_role_is_configured():
        print("Set SUPABASE_URL and the Neo Admin service-role key in the local runtime before applying.")
        return 2

    mapping = {f"/assets/images/{path.name}": _upload(path) for path in images}
    counts = _replace_references(mapping)
    print(f"Uploaded or refreshed {len(mapping)} Storage objects and media library records.")
    for table, count in counts.items():
        print(f"Updated {count} matching URLs in {table}.")
    print("Original files were kept in place for rollback and offline fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
