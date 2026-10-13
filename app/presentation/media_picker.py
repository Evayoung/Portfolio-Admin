"""Small reusable database-backed image selector for admin content forms."""

from __future__ import annotations

from fasthtml.common import Div, Img, Label, Option, P, Select, Input

from app.domain.models import AdminMediaAsset
from app.infrastructure.media_repository import list_media_assets


def media_picker_field(
    label: str, field_name: str, value: str = "", *, help_text: str = "",
    assets: tuple[AdminMediaAsset, ...] | None = None,
) -> Div:
    field_id = field_name
    picker_id = f"media-select-{field_name.replace('_', '-')}"
    preview_id = f"media-preview-{field_name.replace('_', '-')}"
    assets = assets if assets is not None else list_media_assets(kind="image")
    options = [Option("Choose an image from Media", value="")]
    options.extend(Option(asset.title, value=asset.public_url) for asset in assets)
    onchange = (
        f"const field=document.getElementById('{field_id}');"
        f"if(this.value&&field){{field.value=this.value;field.dispatchEvent(new Event('input',{{bubbles:true}}));}}"
        f"const preview=document.getElementById('{preview_id}');"
        f"if(this.value&&preview){{preview.src=this.value;preview.classList.remove('d-none');}}"
    )
    return Div(
        Label(label, for_=field_id, cls="admin-form-label"),
        Input(
            type="text", name=field_name, id=field_id, value=value,
            placeholder="Choose from Media or paste a public HTTPS URL",
            cls="form-control admin-form-control",
        ),
        Select(
            *options, id=picker_id, onchange=onchange,
            cls="form-select admin-form-control mt-2",
        ),
        Img(
            src=value or "", alt=f"{label} preview", id=preview_id,
            cls="img-fluid rounded mt-2" + (" d-none" if not value else ""),
            style="max-height: 150px; object-fit: contain;",
        ),
        P(help_text or f"{len(assets)} images available from the Media Library.", cls="admin-module-copy small mb-0 mt-1"),
        cls="admin-form-group",
    )
