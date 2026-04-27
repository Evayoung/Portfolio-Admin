"""Blog workspace for Neo Admin."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H2, H3, Input, Label, P, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.infrastructure.blog_repository import (
    get_blog_post,
    get_blog_workspace_summary,
    list_blog_categories,
    list_blog_posts,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.pages.dashboard import SectionWrap
from app.presentation.page_helpers import floating_field, search_filter_bar, status_alert, summary_card, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def blog_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(label, href=href, cls=f"admin-filter-chip{' active' if active else ''}")


def _post_card(post, *, selected: bool, category: str, search: str) -> Card:
    href = f"/blog?slug={post.slug}&category={category}&search={search}"
    return Card(
        A(
            Div(
                Div(
                    Div(
                        Span(post.category.replace("-", " ").title(), cls="admin-project-category"),
                        cls="d-flex align-items-center gap-2 flex-wrap",
                    ),
                    Badge("Published", cls="text-bg-success admin-project-flag") if post.published != "Draft" else Badge("Draft", cls="text-bg-secondary admin-project-flag"),
                    cls="d-flex justify-content-between align-items-start gap-2",
                ),
                H3(post.title, cls="admin-project-title"),
                P(post.summary, cls="admin-project-copy"),
                Div(*[Span(item, cls="admin-tech-pill") for item in post.tags], cls="admin-tech-row"),
                Div(
                    Span(post.slug, cls="admin-project-meta"),
                    Span(f"{post.read_minutes} min read", cls="admin-project-meta"),
                    cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
                ),
                cls="admin-project-card-body",
            ),
            href=href,
            cls=f"admin-project-card-link{' is-selected' if selected else ''}",
        ),
        cls="admin-surface-card admin-project-card",
    )


def _editor_form(selected, *, category: str, search: str) -> Form:
    category_options = list_blog_categories()[1:]
    selected_category = selected.category if selected else ""
    category_buttons = toggle_pill_group("category", list(category_options), selected_value=selected_category)
    return Form(
        Input(type="hidden", name="original_slug", value=selected.slug if selected else ""),
        Input(type="hidden", name="current_category", value=category),
        Input(type="hidden", name="current_search", value=search),
        Row(
            Col(floating_field("Title", "title", selected.title if selected else "", placeholder="Article title", required=True), span=12, md=8),
            Col(floating_field("Slug", "slug", selected.slug if selected else "", placeholder="article-slug", required=True), span=12, md=4, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Div(Label("Category", cls="admin-form-label"), category_buttons, cls="admin-form-group mt-3"),
        floating_field("Hero Image URL", "image_url", selected.image if selected else "", placeholder="/assets/images/hero-bg.jpg"),
        Row(
            Col(floating_field("Read Minutes", "read_minutes", str(selected.read_minutes) if selected else "5", input_type="number", placeholder="5"), span=12, md=4),
            Col(floating_field("Tags", "tags", ", ".join(selected.tags) if selected else "", placeholder="FastAPI, Python, AI"), span=12, md=8, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        textarea_field("Summary", "summary", selected.summary if selected else "", rows=3, required=True, placeholder="Short excerpt for listings and previews"),
        textarea_field("HTML Content", "content_html", selected.content_html if selected else "", rows=12, required=True, placeholder="<p>Article body...</p>"),
        Div(
            Label(
                Input(type="checkbox", name="published", checked=(selected.published != "Draft" if selected else True), cls="form-check-input admin-check-input"),
                Span("Published and visible publicly", cls="admin-check-label"),
                cls="admin-check-row",
            ),
            cls="admin-check-grid mt-3",
        ),
        Div(
            Input(type="submit", value="Save Post", cls="btn admin-module-btn"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="blog-save-result", cls="mt-3"),
        action="/blog/save",
        method="post",
        hx_post="/blog/save",
        hx_target="#blog-save-result",
        hx_swap="innerHTML",
        cls="admin-blog-form",
    )


def blog_workspace_page(*, slug: str = "", category: str = "all", search: str = "") -> tuple:
    categories = list_blog_categories()
    posts = list_blog_posts(category=category, search=search)
    selected = get_blog_post(slug) or (posts[0] if posts else None)
    summary = get_blog_workspace_summary()

    category_links = Div(
        *[
            _filter_link(label, f"/blog?category={item_slug}&search={search}", active=item_slug == category)
            for item_slug, label in categories
        ],
        cls="admin-filter-row",
    )
    search_form = search_filter_bar(
        endpoint="/blog",
        placeholder="Search title, slug, summary, or tags",
        search_value=search,
        hidden_fields={"category": category},
        form_cls="admin-search-form admin-filter-bar mt-3",
    )

    list_panel = Card(
        Div(
            Div(
                H2("Blog Records", cls="admin-section-title"),
                P("Select a post to refine its editorial details and keep the public blog up to date.", cls="admin-module-copy mb-0"),
                cls="mb-3",
            ),
            category_links,
            search_form,
            Div(
                *[
                    _post_card(
                        item,
                        selected=bool(selected and item.slug == selected.slug),
                        category=category,
                        search=search,
                    )
                    for item in posts
                ],
                cls="admin-project-list mt-4",
            )
            if posts
            else EmptyState(
                icon="search",
                title="No blog post matches this filter",
                description="Try a different category or search term.",
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    detail_panel = (
        Card(
            Div(
                Div(
                    Div(
                        Span("Selected post", cls="admin-kicker"),
                        H2(selected.title, cls="admin-section-title mb-2"),
                        P(selected.summary, cls="admin-module-copy mb-0"),
                        cls="admin-detail-copy",
                    ),
                    Div(
                        Badge(summary.source, cls="text-bg-secondary admin-metric-delta"),
                        Badge("Live sync on" if service_role_is_configured() else "Setup needed", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                        cls="d-flex flex-wrap gap-2 mt-3 mt-lg-0",
                    ),
                    cls="d-flex flex-column flex-lg-row justify-content-between gap-3",
                ),
                Div(
                    Row(
                        Col(
                            Div(
                                H3("Post Snapshot", cls="admin-subsection-title"),
                                Div(
                                    Div(Span("Slug", cls="admin-field-label"), Strong(selected.slug)),
                                    Div(Span("Category", cls="admin-field-label"), Strong(selected.category.replace("-", " ").title())),
                                    Div(Span("Published", cls="admin-field-label"), Strong(selected.published)),
                                    Div(Span("Read time", cls="admin-field-label"), Strong(f"{selected.read_minutes} min")),
                                    cls="admin-field-grid",
                                ),
                                cls="admin-detail-block",
                            ),
                            span=12,
                            md=6,
                        ),
                        Col(
                            Div(
                                H3("Metadata", cls="admin-subsection-title"),
                                Div(
                                    Div(Span("Image", cls="admin-field-label"), Strong(selected.image)),
                                    Div(Span("Source", cls="admin-field-label"), Strong(selected.source.title())),
                                    Div(Span("Tags", cls="admin-field-label"), Strong(", ".join(selected.tags))),
                                    cls="admin-field-grid",
                                ),
                                cls="admin-detail-block",
                            ),
                            span=12,
                            md=6,
                            cls="mt-4 mt-md-0",
                        ),
                        cls="g-4 mt-1",
                    ),
                    cls="mt-4",
                ),
                Div(
                    H3("Article Editor", cls="admin-subsection-title"),
                    P("Edit the article body, tagging, and publishing status from the same editorial surface.", cls="admin-module-copy"),
                    _editor_form(selected, category=category, search=search),
                    cls="admin-detail-block mt-4",
                ),
                cls="admin-panel-stack",
            ),
            cls="admin-surface-card h-100",
        )
        if selected
        else Card(
            EmptyState(
                icon="journal-richtext",
                title="No post selected",
                description="Pick a post from the list to inspect its content, metadata, and publishing state.",
                cls="py-5",
            ),
            cls="admin-surface-card h-100",
        )
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Blog",
            description="Blog workspace for managing editorial content and publishing state.",
            url=f"{settings.base_url}/blog",
        ),
        *page_frame(
            Row(
                summary_card("Posts", str(summary.total), "Current editorial records available in the workspace."),
                summary_card("Categories", str(summary.categories), "Distinct public-facing post categories."),
                summary_card("Published", str(summary.published), f"Live source: {summary.source}."),
                cls="g-4",
            ),
            SectionWrap(
                "Blog Workspace",
                Row(
                    Col(list_panel, span=12, lg=5),
                    Col(detail_panel, span=12, lg=7, cls="mt-4 mt-lg-0"),
                    cls="g-4",
                ),
            ),
            current="/blog",
            title="Blog",
        ),
    )
