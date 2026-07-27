"""Blog workspace for Neo Admin — clean split grid list & dedicated editor page."""

from __future__ import annotations

from urllib.parse import urlencode

from fasthtml.common import A, Div, Form, H2, H3, Img, Input, Label, Option, P, Select, Span, Strong
from faststrap import Badge, Button, Card, Col, EmptyState, Fx, Icon, Modal, Progress, Row, SEO, Spinner, StatusBadge

from app.config import settings
from app.infrastructure.blog_repository import (
    get_blog_post,
    get_blog_workspace_summary,
    list_blog_categories,
    list_blog_posts,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, action_group, action_link, floating_field, loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field
from app.presentation.shell import page_frame


def blog_save_status_fragment(title: str, message: str, tone: str = "info", slug: str = "") -> Div:
    return Div(
        status_alert(title, message, tone),
        action_group(
            action_link("Open Saved Post", f"/blog/edit?slug={slug}", variant="secondary"),
            action_link("Create Another", "/blog/edit?new=1", variant="secondary"),
            action_link("Open Media Library", "/media?kind=image", variant="secondary"),
        )
        if slug and tone == "success"
        else "",
    )


def _filter_toggle_buttons(category: str, search: str) -> Div:
    """Render category filter links as branded Faststrap button toggle group."""
    categories = list_blog_categories()
    category_buttons = [
        A(
            label,
            href=f"/blog?category={item_slug}&search={search}",
            aria_label=f"Category filter: {label}",
            cls=f"btn admin-toggle-btn{' active' if item_slug == category else ''}",
        )
        for item_slug, label in categories
    ]
    return Div(
        Div(*category_buttons, cls="admin-filter-toggle-group flex-wrap"),
        cls="d-flex flex-wrap align-items-center mb-3",
    )


def _quick_preview_modal(post) -> Modal:
    """Root-level Quick Preview modal for a blog post — xl scrollable, branded surface."""
    modal_id = f"preview-modal-{post.slug}"
    read_pct = min(int(post.read_minutes) * 10, 100)
    return Modal(
        Div(
            Div(
                Img(
                    src=post.image or "/assets/images/hero-bg.jpg",
                    alt=post.title,
                    cls="admin-hero-preview-img rounded-top",
                ),
                cls="position-relative mb-4",
            ),
            Div(
                Div(
                    Badge(post.category.replace("-", " ").title(), cls="text-bg-secondary me-2 fs-6"),
                    Badge("Published", cls="text-bg-success fs-6") if post.published != "Draft" else Badge("Draft", cls="text-bg-secondary fs-6"),
                    Badge(f"{post.read_minutes} min read", cls="text-bg-info ms-2 fs-6"),
                    cls="d-flex flex-wrap gap-1 mb-3",
                ),
                H2(post.title, cls="admin-section-title mb-2 fs-3"),
                P(post.summary, cls="admin-module-copy mb-4 fs-6"),
                Div(
                    Div(Span("Estimated Read Time", cls="admin-field-label fw-bold"), Strong(f"{post.read_minutes} min"), cls="d-flex justify-content-between mb-1"),
                    Progress(value=read_pct, variant="info", height="8px"),
                    cls="admin-detail-block p-3 mb-4",
                ),
                Div(
                    Span("Tags", cls="admin-field-label mb-2 d-block fw-bold"),
                    Div(*[Badge(t, variant="secondary", cls="me-1 fs-6 p-2") for t in post.tags], cls="d-flex flex-wrap gap-1 mb-4"),
                ),
                Div(
                    Span("Content Excerpt", cls="admin-field-label mb-2 d-block fw-bold"),
                    P(
                        post.content_html.replace("<p>", "").replace("</p>", " ").replace("<br>", " ")[:400] + "...",
                        cls="admin-module-copy text-muted fst-italic mb-0",
                    ),
                    cls="admin-detail-block p-3 mb-3",
                ),
            ),
            Div(
                A(
                    Icon("pencil", cls="me-1"),
                    "Edit Full Article →",
                    href=f"/blog/edit?slug={post.slug}",
                    cls="btn admin-module-btn",
                ),
                Button("Close Preview", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
                cls="d-flex justify-content-between align-items-center mt-4 pt-3 border-top border-secondary border-opacity-10",
            ),
        ),
        modal_id=modal_id,
        title=f"Article Preview: {post.title}",
        size="xl",
        scrollable=True,
        centered=True,
    )


def _post_card(post, *, category: str = "all", search: str = "") -> Card:
    href = f"/blog/edit?slug={post.slug}"
    preview_modal_id = f"preview-modal-{post.slug}"
    card_id = f"blog-card-{post.slug}"

    card_body = Div(
        Div(
            Div(
                Span(post.category.replace("-", " ").title(), cls="admin-project-category"),
                cls="d-flex align-items-center gap-2 flex-wrap",
            ),
            Badge("Published", cls="text-bg-success admin-project-flag") if post.published != "Draft" else Badge("Draft", cls="text-bg-secondary admin-project-flag"),
            cls="d-flex justify-content-between align-items-start gap-2",
        ),
        H3(
            post.title,
            Span(cls="admin-card-loading-spinner"),
            cls="admin-project-title d-flex justify-content-between align-items-center",
        ),
        P(post.summary, cls="admin-project-copy"),
        Div(*[Badge(item, variant="secondary", cls="me-1") for item in post.tags], cls="admin-tech-row"),
        Div(
            Span(post.slug, cls="admin-project-meta"),
            Span(f"{post.read_minutes} min read", cls="admin-project-meta"),
            cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
        ),
        cls="admin-project-card-body",
    )

    return Card(
        A(
            card_body,
            href=href,
            hx_get=href,
            hx_target="body",
            hx_swap="innerHTML",
            hx_push_url="true",
            hx_indicator=f"#{card_id}",
            cls="admin-project-card-link",
        ),
        Div(
            Button(
                Icon("eye", cls="me-1"),
                "Quick Preview",
                type="button",
                cls="btn admin-muted-btn btn-sm",
                data_bs_toggle="modal",
                data_bs_target=f"#{preview_modal_id}",
            ),
            A(
                Icon("pencil", cls="me-1"),
                "Edit",
                href=href,
                hx_get=href,
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                hx_indicator=f"#{card_id}",
                cls="btn admin-icon-btn admin-module-btn btn-sm",
            ),
            cls="d-flex justify-content-between align-items-center pt-3 mt-3 border-top border-secondary border-opacity-10",
        ),
        id=card_id,
        cls=[Fx.base, Fx.fade_in, Fx.hover_lift, "admin-surface-card admin-project-card h-100"],
    )


def _blog_category_create_modal() -> Modal:
    """Faststrap modal for creating a new blog category inline — mirrors Projects pattern."""
    return Modal(
        Form(
            floating_field("Category Name", "new_category_name", "", placeholder="e.g. Case Study"),
            Div(
                Button("Create Category", type="submit", cls="btn admin-module-btn"),
                Button("Cancel", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
                cls="d-flex gap-2 justify-content-end mt-3",
            ),
            hx_post="/blog/category/create",
            hx_target="#blog-category-select",
            hx_swap="outerHTML",
            cls="admin-settings-form",
            **{"hx-on::after-request": "if(event.detail.successful){let m=document.getElementById('blog-category-create-modal');let btn=m.querySelector('[data-bs-dismiss=modal]');if(btn)btn.click();}"},
        ),
        modal_id="blog-category-create-modal",
        title="New Blog Category",
        size="sm",
        centered=True,
    )


def _editor_form(selected, *, category: str = "all", search: str = "") -> Form:
    category_options = list(list_blog_categories()[1:]) or [
        ("engineering", "Engineering"),
        ("case-study", "Case Study"),
        ("ai-systems", "AI Systems"),
    ]
    selected_category = selected.category if selected else (category_options[0][0] if category_options else "")
    return Form(
        Input(type="hidden", name="original_slug", value=selected.slug if selected else ""),
        Input(type="hidden", name="current_category", value=category),
        Input(type="hidden", name="current_search", value=search),
        Row(
            Col(floating_field("Title", "title", selected.title if selected else "", placeholder="Article title", required=True), span=12, md=8),
            Col(floating_field("Slug", "slug", selected.slug if selected else "", placeholder="article-slug", required=True), span=12, md=4, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Div(
            Label("Category", cls="admin-form-label"),
            Select(
                Option("Choose category", value=""),
                *[
                    Option(label, value=value, selected=(value == selected_category))
                    for value, label in category_options
                ],
                name="category",
                cls="form-select admin-form-control",
                id="blog-category-select",
            ),
            Div(
                Button("+ New Category", type="button", cls="btn admin-muted-btn btn-sm",
                       data_bs_toggle="modal", data_bs_target="#blog-category-create-modal"),
                cls="mt-2",
            ),
            cls="admin-form-group mt-3",
        ),
        floating_field("Hero Image URL", "image_url", selected.image if selected else "", placeholder="/assets/images/hero-bg.jpg"),
        Row(
            Col(floating_field("Read Minutes", "read_minutes", str(selected.read_minutes) if selected else "5", input_type="number", placeholder="5"), span=12, md=4),
            Col(floating_field("Tags", "tags", ", ".join(selected.tags) if selected else "", placeholder="FastAPI, Python, AI"), span=12, md=8, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Div(
            Div(
                A("Open Media Library", href="/media?kind=image", cls="btn admin-install-btn"),
                A("Upload Hero Image", href="/media?kind=image", cls="btn admin-install-btn"),
                cls="d-flex flex-wrap gap-2",
            ),
            P("Use Media to upload or copy a reusable public URL, then place it in Hero Image URL.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-detail-block mt-3",
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
            loading_action_button("Save Post", endpoint="/blog/save", target="#blog-save-result"),
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


def blog_workspace_page(*, category: str = "all", search: str = "") -> tuple:
    posts = list_blog_posts(category=category, search=search)
    summary = get_blog_workspace_summary()

    toggle_bar = _filter_toggle_buttons(category=category, search=search)
    search_form = search_filter_bar(
        endpoint="/blog",
        placeholder="Search title, slug, summary, or tags",
        search_value=search,
        hidden_fields={"category": category},
        form_cls="admin-search-form admin-filter-bar mb-4",
        hx_target="body",
        hx_swap="innerHTML",
        push_url=True,
    )

    grid_content = Row(
        *[Col(_post_card(item, category=category, search=search), span=12, md=6, lg=4) for item in posts],
        cls="g-4",
    ) if posts else EmptyState(
        icon="journal-richtext",
        title="No blog posts match this filter",
        description="Try a different category or search term, or write a new article.",
        action=A(
            Icon("plus-lg", cls="me-1"),
            "Write New Post",
            href="/blog/edit?new=1",
            cls="btn admin-module-btn mt-3",
        ),
        cls="py-5",
    )

    main_panel = Card(
        Div(
            Div(
                Div(
                    H2("Editorial Posts", cls="admin-section-title"),
                    P("Manage articles, categories, and publication state across the portfolio.", cls="admin-module-copy mb-0"),
                ),
                A(
                    Icon("plus-lg", cls="me-2"),
                    Span("Write Article"),
                    href="/blog/edit?new=1",
                    cls="btn admin-module-btn",
                ),
                cls="d-flex justify-content-between align-items-start gap-3 flex-wrap mb-4",
            ),
            toggle_bar,
            search_form,
            grid_content,
            cls="admin-panel-stack",
        ),
        id="blog-list-panel",
        cls="admin-surface-card h-100",
    )

    # Root-level modals outside cards to avoid z-index/backdrop clipping
    preview_modals = [_quick_preview_modal(p) for p in posts]

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
                main_panel,
            ),
            *preview_modals,
            current="/blog",
            title="Blog",
        ),
    )


def blog_edit_page(*, slug: str = "", category: str = "all", search: str = "", new: str = "") -> tuple:
    creating_new = new == "1"
    selected = None if creating_new else get_blog_post(slug)
    page_heading = "Create New Article" if creating_new else f"Edit Article: {selected.title if selected else 'Not Found'}"

    # HTMX-wired back link with Faststrap Spinner loading indicator
    back_link = A(
        Icon("arrow-left", cls="me-2"),
        "Back to Blog Workspace",
        Spinner(size="sm", cls="admin-back-spinner ms-2"),
        href="/blog",
        hx_get="/blog",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        hx_indicator="#blog-back-link",
        id="blog-back-link",
        cls="admin-back-link mb-3",
    )

    if not creating_new and not selected:
        editor_card = Card(
            EmptyState(
                icon="journal-richtext",
                title="Post not found",
                description=f"No article matches slug '{slug}'.",
                action=A("Back to Blog", href="/blog", cls="btn admin-module-btn mt-3"),
                cls="py-5",
            ),
            cls="admin-surface-card h-100",
        )
        return (
            *SEO(title=f"{settings.app_name} | Article Not Found", url=f"{settings.base_url}/blog/edit"),
            *page_frame(back_link, editor_card, current="/blog", title="Article Not Found"),
        )

    # Article Snapshot Hero Card (Left Column)
    if selected:
        read_pct = min(int(selected.read_minutes) * 10, 100)
        snapshot_card = Card(
            Div(
                Div(
                    Img(
                        src=selected.image or "/assets/images/hero-bg.jpg",
                        alt=selected.title,
                        cls="admin-hero-preview-img rounded-top",
                    ),
                    cls="position-relative mb-3",
                ),
                Div(
                    Div(
                        Badge(selected.category.replace("-", " ").title(), cls="text-bg-secondary me-2"),
                        Badge("Published", cls="text-bg-success") if selected.published != "Draft" else Badge("Draft", cls="text-bg-secondary"),
                        cls="d-flex flex-wrap gap-1 mb-2",
                    ),
                    H3(selected.title, cls="admin-section-title mb-2"),
                    P(selected.summary, cls="admin-module-copy mb-4"),
                    # Read-time progress gauge
                    Div(
                        H3("Read-Time Signal", cls="admin-subsection-title mb-3"),
                        Div(
                            Div(Span("Estimated Read", cls="admin-field-label"), Strong(f"{selected.read_minutes} min"), cls="d-flex justify-content-between mb-1"),
                            Progress(value=read_pct, variant="info", height="8px"),
                            cls="mb-3",
                        ),
                        cls="admin-detail-block p-3 mb-4",
                    ),
                    # Tags
                    Div(
                        H3("Tags", cls="admin-subsection-title mb-2"),
                        Div(*[Badge(t, variant="secondary", cls="me-1 mb-1") for t in selected.tags], cls="d-flex flex-wrap gap-1 mb-3"),
                    ),
                    # Metadata block
                    Div(
                        H3("Content Metadata", cls="admin-subsection-title mb-2"),
                        Div(
                            Div(Span("Slug", cls="admin-field-label"), Strong(selected.slug, cls="text-break")),
                            Div(Span("Category", cls="admin-field-label"), Strong(selected.category.replace("-", " ").title())),
                            Div(
                                Span("Sync Status", cls="admin-field-label"),
                                StatusBadge(
                                    "Live sync on" if service_role_is_configured() else "Setup needed",
                                    status="success" if service_role_is_configured() else "warning",
                                    show_dot=True,
                                    pill=True,
                                    cls="admin-badge-sm ms-2",
                                ),
                            ),
                            cls="admin-field-grid admin-detail-block p-3",
                        ),
                    ),
                ),
            ),
            cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
        )
    else:
        snapshot_card = Card(
            Div(
                H3("New Article Snapshot", cls="admin-section-title mb-2"),
                P("Fill in the fields on the right to draft a new article.", cls="admin-module-copy"),
                Div(
                    StatusBadge("Draft Creation Mode", status="info", show_dot=True, pill=True, cls="admin-badge-sm me-2"),
                    StatusBadge("Live sync on" if service_role_is_configured() else "Setup needed", status="success" if service_role_is_configured() else "warning", show_dot=True, pill=True, cls="admin-badge-sm"),
                    cls="mt-3",
                ),
            ),
            cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100 p-3"],
        )

    # Article Editor Form Panel (Right Column)
    form_panel = Card(
        Div(
            H3("Article Editor", cls="admin-subsection-title"),
            P("Update title, slug, summary, HTML content, tags, read-time, and publishing state.", cls="admin-module-copy mb-4"),
            _editor_form(selected, category=category, search=search),
            _blog_category_create_modal(),
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    return (
        *SEO(
            title=f"{settings.app_name} | {page_heading}",
            description="Edit article details and publishing status.",
            url=f"{settings.base_url}/blog/edit",
        ),
        *page_frame(
            back_link,
            Row(
                Col(snapshot_card, span=12, lg=5),
                Col(form_panel, span=12, lg=7, cls="mt-4 mt-lg-0"),
                cls="g-4",
            ),
            current="/blog",
            title="Edit Article" if not creating_new else "New Article",
        ),
    )
