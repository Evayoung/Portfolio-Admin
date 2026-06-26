"""Project routes — workspace page and save handler."""

from __future__ import annotations

from typing import Any

try:
    from ..infrastructure.project_repository import save_project
    from ..presentation.pages.projects import project_save_status_fragment, projects_page
except ImportError:
    from infrastructure.project_repository import save_project
    from presentation.pages.projects import project_save_status_fragment, projects_page


def setup_project_routes(app: Any) -> None:
    @app.get("/projects")
    def projects(slug: str = "", category: str = "all", featured: str = "0", search: str = "", new: str = "") -> Any:
        return projects_page(slug=slug, category=category, featured=featured, search=search, new=new)

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
        title_text = "Project saved" if result.success else "Save not completed"
        return project_save_status_fragment(title_text, result.message, tone=result.tone, slug=result.slug or "")
