"""Blog routes — workspace page and save handler."""

from __future__ import annotations

from typing import Any

try:
    from ..infrastructure.blog_repository import save_blog_post
    from ..presentation.pages.blog_admin import blog_save_status_fragment, blog_workspace_page
except ImportError:
    from infrastructure.blog_repository import save_blog_post
    from presentation.pages.blog_admin import blog_save_status_fragment, blog_workspace_page


def setup_blog_routes(app: Any) -> None:
    @app.get("/blog")
    def blog(slug: str = "", category: str = "all", search: str = "", new: str = "") -> Any:
        return blog_workspace_page(slug=slug, category=category, search=search, new=new)

    @app.post("/blog/save")
    def blog_save(
        original_slug: str = "",
        slug: str = "",
        title: str = "",
        category: str = "",
        summary: str = "",
        content_html: str = "",
        image_url: str = "",
        read_minutes: str = "5",
        tags: str = "",
        published: str = "",
    ) -> Any:
        result = save_blog_post(
            original_slug=original_slug,
            slug=slug,
            title=title,
            category=category,
            summary=summary,
            content_html=content_html,
            image_url=image_url,
            read_minutes=read_minutes,
            tags=tags,
            published=bool(published),
        )
        title_text = "Blog post saved" if result.success else "Save not completed"
        return blog_save_status_fragment(title_text, result.message, tone=result.tone, slug=result.slug or "")
