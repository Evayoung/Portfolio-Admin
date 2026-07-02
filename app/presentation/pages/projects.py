"""Projects workspace for Neo Admin."""

from __future__ import annotations

from urllib.parse import urlencode

from fasthtml.common import A, Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong
from faststrap import Badge, Button, Card, Col, EmptyState, Icon, Modal, Row, SEO

from app.config import settings
from app.infrastructure.project_repository import (
    get_project,
    get_project_workspace_summary,
    list_project_categories,
    list_projects,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, action_group, action_link, floating_field, loading_action_button, search_filter_bar, status_alert, summary_card, textarea_field
from app.presentation.shell import page_frame


def project_save_status_fragment(title: str, message: str, tone: str = "info", slug: str = "") -> Div:
    return Div(
        status_alert(title, message, tone),
        action_group(
            action_link("Open Saved Project", f"/projects?slug={slug}", variant="secondary"),
            action_link("Create Another", "/projects?new=1", variant="secondary"),
            action_link("Open Media Library", "/media", variant="secondary"),
        )
        if slug and tone == "success"
        else "",
    )


def _project_card(project, *, selected: bool, category: str, featured_only: bool, search: str) -> Card:
    href = _project_href(slug=project.slug, category=category, featured="1" if featured_only else "0", search=search)
    return Card(
        A(
            Div(
                Div(
                    Div(
                        Span(project.category.replace("-", " ").title(), cls="admin-project-category"),
                        Badge("Featured", cls="text-bg-info admin-project-flag") if project.featured else "",
                        cls="d-flex align-items-center gap-2 flex-wrap",
                    ),
                    Badge("Published", cls="text-bg-success admin-project-flag") if project.published else Badge("Draft", cls="text-bg-secondary admin-project-flag"),
                    cls="d-flex justify-content-between align-items-start gap-2",
                ),
                H3(project.title, cls="admin-project-title"),
                P(project.summary, cls="admin-project-copy"),
                Div(*[Badge(item, variant="secondary", cls="me-1") for item in project.tech], cls="admin-tech-row"),
                Div(
                    Span(project.slug, cls="admin-project-meta"),
                    Span(f"Complexity {project.complexity}%", cls="admin-project-meta"),
                    cls="d-flex justify-content-between flex-wrap gap-2 mt-3",
                ), 
                cls="admin-project-card-body",
            ),
            href=href,
            cls=f"admin-project-card-link{' admin-is-selected' if selected else ''}"
        ),
        cls="admin-surface-card admin-project-card",
    )


def _filter_link(label: str, href: str, *, active: bool) -> A:
    return A(label, href=href, cls=f"admin-filter-chip{' active' if active else ''}")


def _project_href(**params: str) -> str:
    return f"/projects?{urlencode(params)}"


def _new_project_href(*, category: str, featured_only: bool, search: str) -> str:
    return _project_href(
        category=category,
        featured="1" if featured_only else "0",
        search=search,
        new="1",
    )


def _editor_form(selected, *, category: str, featured_only: bool, search: str) -> Form:
    category_options = list_project_categories()[1:]
    selected_category = selected.category if selected else ""
    return Form(
        Input(type="hidden", name="original_slug", value=selected.slug if selected else ""),
        Input(type="hidden", name="current_category", value=category),
        Input(type="hidden", name="current_featured", value="1" if featured_only else "0"),
        Input(type="hidden", name="current_search", value=search),
        Row(
            Col(floating_field("Title", "title", selected.title if selected else "", placeholder="Project title", required=True), span=12, md=8),
            Col(floating_field("Slug", "slug", selected.slug if selected else "", placeholder="project-slug", required=True), span=12, md=4, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Div(
            Label("Category", cls="admin-form-label"),
            Select(
                Option("Choose category", value=""),
                *[
                    Option(label, value=value, selected=value == selected_category)
                    for value, label in category_options
                ],
                name="category",
                cls="form-select admin-form-control",
                id="project-category-select",
            ),
            Div(
                Button("+ New Category", type="button", cls="btn admin-install-btn",
                       data_bs_toggle="modal", data_bs_target="#category-create-modal"),
                cls="mt-2",
            ),
            cls="admin-form-group mt-3",
        ),
        floating_field("Image URL", "image_url", selected.image if selected else "", placeholder="/assets/images/example.jpg"),
        textarea_field("Summary", "summary", selected.summary if selected else "", rows=3, required=True, placeholder="Short public-facing project summary"),
        textarea_field("Narrative", "narrative", selected.narrative if selected else "", rows=6, required=True, placeholder="Longer case-study narrative"),
        floating_field("Tech Stack", "tech_stack", ", ".join(selected.tech) if selected else "", placeholder="Python, FastAPI, PostgreSQL"),
        Row(
            Col(floating_field("Complexity", "complexity", str(selected.complexity) if selected else "0", input_type="number", placeholder="0-100"), span=12, md=6),
            Col(floating_field("Satisfaction", "satisfaction", str(selected.satisfaction) if selected else "0", input_type="number", placeholder="0-100"), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Div(
            Div(
                A("Open Media Library", href="/media?kind=image", cls="btn admin-install-btn"),
                A("Upload Project Image", href="/media?kind=image", cls="btn admin-install-btn"),
                cls="d-flex flex-wrap gap-2",
            ),
            P("Use the media page to upload or copy an existing public URL, then place it in Image URL.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-detail-block mt-3",
        ),
        Div(
            Label(
                Input(type="checkbox", name="featured", checked=(selected.featured if selected else False), cls="form-check-input admin-check-input"),
                Span("Featured on key surfaces", cls="admin-check-label"),
                cls="admin-check-row",
            ),
            Label(
                Input(type="checkbox", name="published", checked=(selected.published if selected else True), cls="form-check-input admin-check-input"),
                Span("Published and visible publicly", cls="admin-check-label"),
                cls="admin-check-row",
            ),
            cls="admin-check-grid mt-3",
        ),
        Div(
            loading_action_button("Save Project", endpoint="/projects/save", target="#project-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="project-save-result", cls="mt-3"),
        action="/projects/save",
        method="post",
        hx_post="/projects/save",
        hx_target="#project-save-result",
        hx_swap="innerHTML",
        cls="admin-project-form",
    )


def _category_create_modal() -> Modal:
    return Modal(
        Form(
            floating_field("Category Name", "new_category_name", "", placeholder="e.g. Data Science"),
            Div(
                Button("Create Category", type="submit", cls="btn admin-module-btn"),
                Button("Cancel", type="button", cls="btn admin-install-btn", data_bs_dismiss="modal"),
                cls="d-flex gap-2 justify-content-end mt-3",
            ),
            hx_post="/projects/category/create",
            hx_target="#project-category-select",
            hx_swap="outerHTML",
            cls="admin-settings-form",
            **{"hx-on::after-request": "if(event.detail.successful){let m=document.getElementById('category-create-modal');let btn=m.querySelector('[data-bs-dismiss=modal]');if(btn)btn.click();}"},
        ),
        modal_id="category-create-modal",
        title="New Category",
        size="sm",
        centered=True,
    )


def projects_page(*, slug: str = "", category: str = "all", featured: str = "0", search: str = "", new: str = "") -> tuple:
    featured_only = featured == "1"
    creating_new = new == "1"
    categories = list_project_categories()
    projects = list_projects(category=category, featured_only=featured_only, search=search)
    selected = None if creating_new else get_project(slug) or (projects[0] if projects else None)
    summary = get_project_workspace_summary()

    category_links = Div(
        *[
            _filter_link(
                label,
                _project_href(category=item_slug, featured="1" if featured_only else "0", search=search),
                active=item_slug == category,
            )
            for item_slug, label in categories
        ],
        cls="admin-filter-row",
    )
    featured_toggle = _filter_link(
        "Featured only",
        _project_href(category=category, featured="0" if featured_only else "1", search=search),
        active=featured_only,
    )
    search_form = search_filter_bar(
        endpoint="/projects",
        placeholder="Search title, slug, or summary",
        search_value=search,
        hidden_fields={
            "category": category,
            "featured": "1" if featured_only else "0",
        },
        form_cls="admin-search-form admin-filter-bar mt-3",
    )

    list_panel = Card(
        Div(
            Div(
                H2("Project Records", cls="admin-section-title"),
                P(
                    "Select a project to review, refine, and keep aligned with the public portfolio.",
                    cls="admin-module-copy mb-0",
                ),
                cls="mb-3",
            ),
            Div(
                A(
                    Icon("plus-lg", cls="me-2"),
                    Span("New Project"),
                    href=_new_project_href(category=category, featured_only=featured_only, search=search),
                    cls="btn admin-module-btn",
                ),
                A("Media Library", href="/media?kind=image", cls="btn admin-install-btn"),
                cls="d-flex flex-wrap gap-2 mt-3 mb-3",
            ),
            category_links,
            Div(featured_toggle, cls="mt-3"),
            search_form,
            Div(
                *[
                    _project_card(
                        item,
                        selected=bool(selected and item.slug == selected.slug),
                        category=category,
                        featured_only=featured_only,
                        search=search,
                    )
                    for item in projects
                ],
                cls="admin-project-list mt-4",
            )
            if projects
            else EmptyState(
                icon="search",
                title="No project matches this filter",
                description="Try a different category, search term, or turn off the featured-only view.",
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
            cls="admin-surface-card h-100",
        )

    if creating_new:
        detail_panel = Card(
            Div(
                Div(
                    Div(
                        Span("Selected record", cls="admin-kicker"),
                        H2("Create New Project", cls="admin-section-title mb-2"),
                        P("Add a previous project manually, attach a media URL, and save it as an editable portfolio record.", cls="admin-module-copy mb-0"),
                        cls="admin-detail-copy",
                    ),
                    Div(
                        Badge("Manual add", cls="text-bg-primary admin-metric-delta"),
                        Badge("Live sync on" if service_role_is_configured() else "Setup needed", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                        cls="d-flex flex-wrap gap-2 mt-3 mt-lg-0",
                    ),
                    cls="d-flex flex-column flex-lg-row justify-content-between gap-3",
                ),
                Div(
                    H3("Project Editor", cls="admin-subsection-title"),
                    P("Fill in the details, then save. The response will give you a direct link back to the saved record.", cls="admin-module-copy"),
                    _editor_form(None, category=category, featured_only=featured_only, search=search),
                    _category_create_modal(),
                    cls="admin-detail-block mt-4",
                ),
                cls="admin-panel-stack",
            ),
            cls="admin-surface-card h-100",
        )

    else:
        detail_panel = (
            Card(
                Div(
                    Div(
                        Div(
                            Span("Selected record", cls="admin-kicker"),
                            H2(selected.title, cls="admin-section-title mb-2"),
                            P(selected.summary, cls="admin-module-copy mb-0"),
                            cls="admin-detail-copy",
                        ),
                        Div(
                            Badge(summary.source, cls="text-bg-secondary admin-metric-delta"),
                            Badge(
                                "Live sync on" if service_role_is_configured() else "Setup needed",
                                cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta",
                            ),
                            cls="d-flex flex-wrap gap-2 mt-3 mt-lg-0",
                        ),
                        cls="d-flex flex-column flex-lg-row justify-content-between gap-3",
                    ),
                    Div(
                        Row(
                            Col(
                                Div(
                                    H3("Content Snapshot", cls="admin-subsection-title"),
                                    Div(
                                        Div(Span("Slug", cls="admin-field-label"), Strong(selected.slug)),
                                        Div(Span("Category", cls="admin-field-label"), Strong(selected.category.replace("-", " ").title())),
                                        Div(Span("Featured", cls="admin-field-label"), Strong("Yes" if selected.featured else "No")),
                                        Div(Span("Published", cls="admin-field-label"), Strong("Yes" if selected.published else "No")),
                                        cls="admin-field-grid",
                                    ),
                                    cls="admin-detail-block",
                                ),
                                span=12,
                                md=6,
                            ),
                            Col(
                                Div(
                                    H3("Score Signals", cls="admin-subsection-title"),
                                    Div(
                                        Div(Span("Complexity", cls="admin-field-label"), Strong(f"{selected.complexity}%")),
                                        Div(Span("Satisfaction", cls="admin-field-label"), Strong(f"{selected.satisfaction}%")),
                                        Div(Span("Image", cls="admin-field-label"), Strong(selected.image)),
                                        Div(Span("Source", cls="admin-field-label"), Strong(selected.source.title())),
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
                        H3("Project Editor", cls="admin-subsection-title"),
                        P(
                            "Update the project record, publishing flags, and story details from one focused workspace.",
                            cls="admin-module-copy",
                        ),
                        _editor_form(selected, category=category, featured_only=featured_only, search=search),
                        _category_create_modal(),
                        cls="admin-detail-block mt-4",
                    ),
                    cls="admin-panel-stack",
                ),
                cls="admin-surface-card h-100",
            )
            if selected
            else Card(
                EmptyState(
                    icon="kanban",
                    title="No project selected",
                    description="Pick a project from the list to inspect its content, metadata, and publishing details.",
                    cls="py-5",
                ),
                cls="admin-surface-card h-100",
            )
        )

    return (
        *SEO(
            title=f"{settings.app_name} | Projects",
            description="Projects workspace for managing portfolio case studies and publishing details.",
            url=f"{settings.base_url}/projects",
        ),
        *page_frame(
            Row(
                summary_card("Projects", str(summary.total), "Current portfolio records available in the workspace."),
                summary_card("Featured", str(summary.featured), "Flagged for homepage or primary discovery surfaces."),
                summary_card("Categories", str(summary.categories), f"Live source: {summary.source}."),
                cls="g-4",
            ),
            SectionWrap(
                "Projects Workspace",
                Row(
                    Col(list_panel, span=12, lg=5),
                    Col(
                        Button(
                            "Show Editor ↓",
                            type="button",
                            cls="admin-panel-toggle-btn",
                            data_panel_toggle="projects-detail-panel",
                            id="projects-panel-toggle",
                        ),
                        span=12,
                        cls="d-lg-none",
                    ),
                    Col(
                        detail_panel,
                        id="projects-detail-panel",
                        span=12,
                        lg=7,
                        cls="admin-panel-hidden",
                    ),
                    cls="g-4",
                ),
            ),
            current="/projects",
            title="Projects",
        ),
    )
