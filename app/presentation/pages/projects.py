"""Projects workspace for Neo Admin — split records list, root-level quick preview modal, and dedicated editor page."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Img, Input, Label, Option, P, Select, Span, Strong
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Modal, Progress, Row, SEO, Spinner, StatusBadge

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
            action_link("Open Saved Project", f"/projects/edit?slug={slug}", variant="secondary"),
            action_link("Create Another", "/projects/edit?new=1", variant="secondary"),
            action_link("Open Media Library", "/media", variant="secondary"),
        )
        if slug and tone == "success"
        else "",
    )


def _project_card(project, *, category: str, featured_only: bool, search: str, selected: bool = False) -> Card:
    href = f"/projects/edit?slug={project.slug}"
    preview_modal_id = f"preview-modal-{project.slug}"
    card_id = f"project-card-{project.slug}"

    card_body = Div(
        Div(
            Div(
                Span(project.category.replace("-", " ").title(), cls="admin-project-category"),
                Badge("Featured", cls="text-bg-info admin-project-flag") if project.featured else "",
                cls="d-flex align-items-center gap-2 flex-wrap",
            ),
            Badge("Published", cls="text-bg-success admin-project-flag") if project.published else Badge("Draft", cls="text-bg-secondary admin-project-flag"),
            cls="d-flex justify-content-between align-items-start gap-2",
        ),
        H3(
            project.title,
            Span(cls="admin-card-loading-spinner"),
            cls="admin-project-title d-flex justify-content-between align-items-center",
        ),
        P(project.summary, cls="admin-project-copy"),
        Div(*[Badge(item, variant="secondary", cls="me-1") for item in project.tech], cls="admin-tech-row"),
        Div(
            Span(project.slug, cls="admin-project-meta"),
            Span(f"Complexity {project.complexity}%", cls="admin-project-meta"),
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
        # Card quick action bar (outside main link so Quick Preview button can open modal directly)
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


def _quick_preview_modal(project) -> Modal:
    """Render a Quick Preview Faststrap modal for a given project at xl size."""
    modal_id = f"preview-modal-{project.slug}"
    return Modal(
        Div(
            # Hero Image Banner
            Div(
                Img(
                    src=project.image or "/assets/images/hero-bg.jpg",
                    alt=project.title,
                    cls="admin-hero-preview-img rounded-top",
                ),
                cls="position-relative mb-4",
            ),
            Div(
                Div(
                    Badge(project.category.replace("-", " ").title(), cls="text-bg-secondary me-2 fs-6"),
                    Badge("Featured", cls="text-bg-info me-2 fs-6") if project.featured else "",
                    Badge("Published", cls="text-bg-success fs-6") if project.published else Badge("Draft", cls="text-bg-secondary fs-6"),
                    cls="d-flex flex-wrap gap-1 mb-3",
                ),
                H2(project.title, cls="admin-section-title mb-2 fs-3"),
                P(project.summary, cls="admin-module-copy mb-4 fs-6"),
                # Score Signals Progress Bars
                Row(
                    Col(
                        Div(
                            Div(Span("Complexity Score", cls="admin-field-label fw-bold"), Strong(f"{project.complexity}%"), cls="d-flex justify-content-between mb-1"),
                            Progress(value=project.complexity, variant="info", height="10px"),
                            cls="admin-detail-block p-3",
                        ),
                        span=12,
                        md=6,
                    ),
                    Col(
                        Div(
                            Div(Span("Satisfaction Rating", cls="admin-field-label fw-bold"), Strong(f"{project.satisfaction}%"), cls="d-flex justify-content-between mb-1"),
                            Progress(value=project.satisfaction, variant="success", height="10px"),
                            cls="admin-detail-block p-3 mt-3 mt-md-0",
                        ),
                        span=12,
                        md=6,
                    ),
                    cls="g-3 mb-4",
                ),
                Div(
                    Span("Tech Stack & Architecture", cls="admin-field-label mb-2 d-block fw-bold"),
                    Div(*[Badge(item, variant="secondary", cls="me-1 fs-6 p-2") for item in project.tech], cls="d-flex flex-wrap gap-1 mb-4"),
                ),
                Div(
                    Span("Case Study Narrative Excerpt", cls="admin-field-label mb-2 d-block fw-bold"),
                    P(project.narrative[:400] + ("..." if len(project.narrative) > 400 else ""), cls="admin-module-copy text-muted fst-italic mb-0"),
                    cls="admin-detail-block p-3 mb-3",
                ),
            ),
            # Footer CTA
            Div(
                A(
                    Icon("pencil", cls="me-1"),
                    "Edit Full Record →",
                    href=f"/projects/edit?slug={project.slug}",
                    cls="btn admin-module-btn",
                ),
                Button("Close Preview", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
                cls="d-flex justify-content-between align-items-center mt-4 pt-3 border-top border-secondary border-opacity-10",
            ),
        ),
        modal_id=modal_id,
        title=f"Project Snapshot: {project.title}",
        size="xl",
        scrollable=True,
        centered=True,
    )


def _filter_toggle_buttons(category: str, featured_only: bool, search: str) -> Div:
    """Render category & featured filter links as branded Faststrap button toggle group."""
    categories = list_project_categories()
    category_buttons = [
        A(
            label,
            href=f"/projects?category={item_slug}&featured={'1' if featured_only else '0'}&search={search}",
            aria_label=f"Category filter: {label}",
            cls=f"btn admin-toggle-btn{' active' if item_slug == category else ''}",
        )
        for item_slug, label in categories
    ]
    featured_button = A(
        Icon("star-fill" if featured_only else "star", cls="me-1"),
        "Featured only",
        href=f"/projects?category={category}&featured={'0' if featured_only else '1'}&search={search}",
        aria_label="Toggle featured projects only",
        cls=f"btn admin-toggle-btn{' active' if featured_only else ''}",
    )
    return Div(
        Div(*category_buttons, cls="admin-filter-toggle-group flex-wrap me-2 mb-2"),
        Div(featured_button, cls="admin-filter-toggle-group mb-2"),
        cls="d-flex flex-wrap align-items-center mb-3",
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
                Button("+ New Category", type="button", cls="btn admin-muted-btn btn-sm",
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
                A("Open Media Library", href="/media?kind=image", target="_blank", cls="btn admin-muted-btn"),
                Input(
                    type="file",
                    id="project-image-file-input",
                    name="image_file",
                    accept="image/*",
                    hx_post="/projects/upload-image",
                    hx_encoding="multipart/form-data",
                    hx_target="#project-image-upload-result",
                    hx_swap="innerHTML",
                    cls="form-control admin-form-control d-inline-block w-auto",
                ),
                cls="d-flex flex-wrap align-items-center gap-2",
            ),
            Div(id="project-image-upload-result", cls="mt-2"),
            P("Use the selector to upload directly, or open the media library. The Image URL field will auto-fill.", cls="admin-module-copy mt-2 mb-0"),
            cls="admin-detail-block mt-3",
        ),
        Div(
            Label(
                Input(type="checkbox", name="featured", checked=(selected.featured if selected else False), cls="form-check-input admin-check-input"),
                Span("Featured on key discovery surfaces", cls="admin-check-label"),
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
                Button("Cancel", type="button", cls="btn admin-muted-btn", data_bs_dismiss="modal"),
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


def _projects_list_panel(projects, selected, *, category: str, featured_only: bool, search: str, summary) -> Card:
    """Render the project list grid panel — reusable for both full page and live search fragment."""
    toggle_bar = _filter_toggle_buttons(category=category, featured_only=featured_only, search=search)
    search_form = search_filter_bar(
        endpoint="/projects/search",
        placeholder="Search title, slug, or summary (live)",
        search_value=search,
        hidden_fields={
            "category": category,
            "featured": "1" if featured_only else "0",
        },
        form_cls="admin-search-form admin-filter-bar mb-4",
        hx_target="#projects-list-panel",
        hx_swap="outerHTML",
        mode="auto",
    )
    return Card(
        Div(
            Div(
                Div(
                    H2("Project Records", cls="admin-section-title"),
                    P("Browse, search, and inspect portfolio case studies. Click any record to edit or preview.", cls="admin-module-copy mb-0"),
                ),
                Div(
                    A(
                        Icon("plus-lg", cls="me-1"),
                        Span("New Project"),
                        href=f"/projects/edit?new=1&category={category}&featured={'1' if featured_only else '0'}&search={search}",
                        cls="btn admin-module-btn",
                    ),
                    A(
                        Icon("folder2-open", cls="me-1"),
                        Span("Media Library"),
                        href="/media?kind=image",
                        cls="btn admin-muted-btn",
                    ),
                    cls="d-flex flex-wrap gap-2 mt-3 mt-md-0",
                ),
                cls="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-4",
            ),
            toggle_bar,
            search_form,
            Row(
                *[
                    Col(
                        _project_card(
                            item,
                            selected=bool(selected and item.slug == selected.slug),
                            category=category,
                            featured_only=featured_only,
                            search=search,
                        ),
                        span=12,
                        md=6,
                        lg=4,
                    )
                    for item in projects
                ],
                cls="g-4",
            )
            if projects
            else EmptyState(
                icon="kanban",
                title="No projects found" if summary.total > 0 else "No portfolio projects yet",
                description="Try adjusting your category filter, turning off featured-only view, or clearing your search term.",
                action=A(
                    Icon("plus-lg", cls="me-1"),
                    "Create Project",
                    href="/projects/edit?new=1",
                    cls="btn admin-module-btn mt-3",
                ),
                cls="py-5",
            ),
            cls="admin-panel-stack",
        ),
        id="projects-list-panel",
        cls="admin-surface-card h-100",
    )


def projects_page(*, category: str = "all", featured: str = "0", search: str = "") -> tuple:
    """Projects Workspace Page — Grid listing, search, category filters, root-level quick preview modals."""
    featured_only = featured == "1"
    projects = list_projects(category=category, featured_only=featured_only, search=search)
    summary = get_project_workspace_summary()

    list_panel = _projects_list_panel(projects, None, category=category, featured_only=featured_only, search=search, summary=summary)
    preview_modals = [_quick_preview_modal(p) for p in projects]

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
                list_panel,
            ),
            *preview_modals,  # Modals rendered at root level outside cards to avoid z-index/backdrop clipping!
            current="/projects",
            title="Projects",
        ),
    )


def project_edit_page(*, slug: str = "", category: str = "all", featured: str = "0", search: str = "", new: str = "") -> tuple:
    """Dedicated Project Editor Page — Back link, visual hero snapshot card, progress gauges, full editor form."""
    featured_only = featured == "1"
    creating_new = new == "1"
    selected = None if creating_new else get_project(slug)
    summary = get_project_workspace_summary()

    page_heading = "Create New Project" if creating_new else f"Edit Project: {selected.title if selected else 'Not Found'}"

    back_link = A(
        Icon("arrow-left", cls="me-2"),
        "Back to Projects Workspace",
        Spinner(size="sm", cls="admin-back-spinner ms-2"),
        href="/projects",
        hx_get="/projects",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        hx_indicator="#projects-back-link",
        id="projects-back-link",
        cls="admin-back-link mb-3",
    )

    if not creating_new and not selected:
        editor_panel = Card(
            EmptyState(
                icon="kanban",
                title="Project not found",
                description=f"No portfolio project matches slug '{slug}'.",
                action=A("Back to Projects", href="/projects", cls="btn admin-module-btn mt-3"),
                cls="py-5",
            ),
            cls="admin-surface-card h-100",
        )
        return (
            *SEO(title=f"{settings.app_name} | Project Not Found", url=f"{settings.base_url}/projects/edit"),
            *page_frame(back_link, editor_panel, current="/projects", title="Project Not Found"),
        )

    # Hero Visual Snapshot Card (Left Column)
    if selected:
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
                        Badge("Featured", cls="text-bg-info me-2") if selected.featured else "",
                        Badge("Published", cls="text-bg-success") if selected.published else Badge("Draft", cls="text-bg-secondary"),
                        cls="d-flex flex-wrap gap-1 mb-2",
                    ),
                    H3(selected.title, cls="admin-section-title mb-2"),
                    P(selected.summary, cls="admin-module-copy mb-4"),
                    # Score Signal Progress Bars
                    Div(
                        H3("Score Signals", cls="admin-subsection-title mb-3"),
                        Div(
                            Div(Span("Complexity", cls="admin-field-label"), Strong(f"{selected.complexity}%"), cls="d-flex justify-content-between mb-1"),
                            Progress(value=selected.complexity, variant="info", height="8px"),
                            cls="mb-3",
                        ),
                        Div(
                            Div(Span("Satisfaction", cls="admin-field-label"), Strong(f"{selected.satisfaction}%"), cls="d-flex justify-content-between mb-1"),
                            Progress(value=selected.satisfaction, variant="success", height="8px"),
                            cls="mb-3",
                        ),
                        cls="admin-detail-block p-3 mb-4",
                    ),
                    # Metadata Compact Badges
                    Div(
                        H3("Content Metadata", cls="admin-subsection-title mb-2"),
                        Div(
                            Div(Span("Slug", cls="admin-field-label"), Strong(selected.slug, cls="text-break")),
                            Div(Span("Category", cls="admin-field-label"), Strong(selected.category.replace("-", " ").title())),
                            Div(
                                Span("Source", cls="admin-field-label"),
                                Badge(summary.source, cls="text-bg-secondary admin-badge-sm ms-2"),
                            ),
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
                H3("New Record Snapshot", cls="admin-section-title mb-2"),
                P("Fill in the fields on the right to create a new portfolio project.", cls="admin-module-copy"),
                Div(
                    StatusBadge("Manual Creation Mode", status="info", show_dot=True, pill=True, cls="admin-badge-sm me-2"),
                    StatusBadge("Live sync on" if service_role_is_configured() else "Setup needed", status="success" if service_role_is_configured() else "warning", show_dot=True, pill=True, cls="admin-badge-sm"),
                    cls="mt-3",
                ),
            ),
            cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100 p-3"],
        )

    # Form Panel (Right Column)
    form_panel = Card(
        Div(
            H3("Project Editor", cls="admin-subsection-title"),
            P("Update title, slug, summary, score signals, tech stack, and publishing state.", cls="admin-module-copy mb-4"),
            _editor_form(selected, category=category, featured_only=featured_only, search=search),
            _category_create_modal(),
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    return (
        *SEO(
            title=f"{settings.app_name} | {page_heading}",
            description="Edit portfolio project record and publishing details.",
            url=f"{settings.base_url}/projects/edit",
        ),
        *page_frame(
            back_link,
            Row(
                Col(snapshot_card, span=12, lg=5),
                Col(form_panel, span=12, lg=7, cls="mt-4 mt-lg-0"),
                cls="g-4",
            ),
            current="/projects",
            title="Edit Project" if not creating_new else "New Project",
        ),
    )
