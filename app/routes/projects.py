"""Project routes — workspace page and save handler."""

from __future__ import annotations

from typing import Any

from fasthtml.common import Option, Select
from starlette.responses import Response

try:
    from ..infrastructure.project_repository import get_project, get_project_workspace_summary, list_projects, save_project
    from ..presentation.page_helpers import toast_fragment
    from ..presentation.pages.projects import _projects_list_panel, project_save_status_fragment, projects_page
except ImportError:
    from infrastructure.project_repository import get_project, get_project_workspace_summary, list_projects, save_project
    from presentation.page_helpers import toast_fragment
    from presentation.pages.projects import _projects_list_panel, project_save_status_fragment, projects_page


from starlette.datastructures import UploadFile


def setup_project_routes(app: Any) -> None:
    @app.get("/projects")
    def projects(slug: str = "", category: str = "all", featured: str = "0", search: str = "", new: str = "") -> Any:
        return projects_page(slug=slug, category=category, featured=featured, search=search, new=new)

    @app.get("/projects/search")
    def projects_search(category: str = "all", featured: str = "0", search: str = "") -> Any:
        """Return just the project list panel for HTMX live search."""
        featured_only = featured == "1"
        project_list = list_projects(category=category, featured_only=featured_only, search=search)
        selected = project_list[0] if project_list else None
        summary = get_project_workspace_summary()
        return _projects_list_panel(project_list, selected, category=category, featured_only=featured_only, search=search, summary=summary)

    @app.post("/projects/category/create")
    def project_category_create(name: str = "") -> Any:
        new_slug = name.strip().lower().replace(" ", "-")
        if not new_slug:
            return Select(Option("Choose category", value=""), name="category", cls="form-select admin-form-control", id="project-category-select")
        categories = list_project_categories()[1:]
        return Select(
            Option("Choose category", value=""),
            *[
                Option(label, value=value, selected=(value == new_slug))
                for value, label in categories
            ] + [Option(name.strip(), value=new_slug, selected=True)],
            name="category",
            cls="form-select admin-form-control",
            id="project-category-select",
        )

    @app.post("/projects/upload-image")
    def projects_upload_image(image_file: UploadFile | None = None) -> Any:
        try:
            from ..infrastructure.media_repository import upload_media_asset
        except ImportError:
            from infrastructure.media_repository import upload_media_asset
        from fasthtml.common import Div, Span, Script

        if image_file is None or not getattr(image_file, "filename", ""):
            return Div("Please select a file first.", cls="text-danger mt-1")
        title = f"Project Image - {image_file.filename}"
        result = upload_media_asset(title=title, kind="image", alt_text="", asset_file=image_file)
        if result.success and result.public_url:
            return Div(
                Span("✓ Uploaded successfully!", cls="text-success me-2"),
                Script(f"document.getElementById('image_url').value = '{result.public_url}';"),
                cls="mt-1"
            )
        return Div(f"Upload failed: {result.message}", cls="text-danger mt-1")

    @app.post("/projects/save")
    def project_save(
        original_slug: str = "",
        slug: str = "",
        title: str = "",
        category: str = "",
        category_custom: str = "",
        summary: str = "",
        narrative: str = "",
        tech_stack: str = "",
        image_url: str = "",
        complexity: str = "0",
        satisfaction: str = "0",
        featured: str = "",
        published: str = "",
    ) -> Any:
        result = save_project(
            original_slug=original_slug,
            slug=slug,
            title=title,
            category=category,
            category_custom=category_custom,
            summary=summary,
            narrative=narrative,
            tech_stack=tech_stack,
            image_url=image_url,
            complexity=complexity,
            satisfaction=satisfaction,
            featured=bool(featured),
            published=bool(published),
        )
        if result.success:
            return (
                Response("", status_code=200, headers={"HX-Refresh": "true"}),
                toast_fragment("Project saved", result.message),
            )
        title_text = "Save not completed"
        return project_save_status_fragment(title_text, result.message, tone=result.tone)
