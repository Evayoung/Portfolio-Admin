"""Blog routes — workspace page, dedicated edit page, and save handler."""

from __future__ import annotations

from typing import Any

from fasthtml.common import Option, Select
from starlette.responses import Response

try:
    from ..infrastructure.blog_repository import get_blog_post, get_blog_workspace_summary, list_blog_categories, list_blog_posts, save_blog_post
    from ..presentation.page_helpers import toast_fragment
    from ..presentation.pages.blog_admin import blog_edit_page, blog_save_status_fragment, blog_workspace_page
except ImportError:
    from infrastructure.blog_repository import get_blog_post, get_blog_workspace_summary, list_blog_categories, list_blog_posts, save_blog_post
    from presentation.page_helpers import toast_fragment
    from presentation.pages.blog_admin import blog_edit_page, blog_save_status_fragment, blog_workspace_page


def setup_blog_routes(app: Any) -> None:
    @app.get("/blog")
    def blog(category: str = "all", search: str = "") -> Any:
        return blog_workspace_page(category=category, search=search)

    @app.get("/blog/edit")
    def blog_edit(slug: str = "", category: str = "all", search: str = "", new: str = "") -> Any:
        return blog_edit_page(slug=slug, category=category, search=search, new=new)

    @app.post("/blog/category/create")
    def blog_category_create(new_category_name: str = "") -> Any:
        """HTMX endpoint — returns a refreshed Select element with the new category pre-selected."""
        new_slug = new_category_name.strip().lower().replace(" ", "-")
        if not new_slug:
            return Select(
                Option("Choose category", value=""),
                name="category",
                cls="form-select admin-form-control",
                id="blog-category-select",
            )
        categories = list_blog_categories()[1:]  # skip the "all" sentinel
        return Select(
            Option("Choose category", value=""),
            *[
                Option(label, value=value, selected=(value == new_slug))
                for value, label in categories
            ],
            Option(new_category_name.strip(), value=new_slug, selected=True),
            name="category",
            cls="form-select admin-form-control",
            id="blog-category-select",
        )

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
        if result.success:
            return (
                Response("", status_code=200, headers={"HX-Refresh": "true"}),
                toast_fragment("Blog post saved", result.message),
            )
        title_text = "Save not completed"
        return blog_save_status_fragment(title_text, result.message, tone=result.tone, slug=result.slug or "")
