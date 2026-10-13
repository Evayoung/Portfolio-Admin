"""Workspace pages for editing public Services and Pricing content."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, Input, Label, P, Span, Strong, Textarea
from faststrap import Badge, Card, Col, EmptyState, Icon, Row

from app.domain.models import AdminHomeContent, AdminPricingTier, AdminService, AdminTestimonial
from app.infrastructure.cv_repository import list_core_skills, list_work_history
from app.infrastructure.supabase_client import service_role_is_configured
from app.infrastructure.media_repository import list_media_assets
from app.infrastructure.website_content_repository import get_site_home_content, list_pricing_tiers, list_services, list_testimonials
from app.presentation.media_picker import media_picker_field
from app.presentation.page_helpers import status_alert
from app.presentation.shell import brand_profile, page_frame, public_site_url


def _field(label: str, name: str, value: str = "", *, required: bool = False, placeholder: str = "", full: bool = False):
    return Div(
        Label(label, for_=f"website-{name}", cls="form-label admin-field-label"),
        Input(
            name=name, id=f"website-{name}", value=value, required=required,
            placeholder=placeholder, cls="form-control admin-form-control",
        ),
        cls="col-12" if full else "col-md-6",
    )


def _textarea(label: str, name: str, value: str = "", *, required: bool = False, help_text: str = ""):
    return Div(
        Label(label, for_=f"website-{name}", cls="form-label admin-field-label"),
        Textarea(
            value, name=name, id=f"website-{name}", required=required, rows=4,
            cls="form-control admin-form-control", aria_describedby=f"website-{name}-help" if help_text else None,
        ),
        P(help_text, id=f"website-{name}-help", cls="admin-module-copy small mb-0") if help_text else "",
        cls="col-12",
    )


def _record_list(items, section: str, selected_id: str):
    if not items:
        message = "Connect Supabase admin access to load and edit these public records." if not service_role_is_configured() else f"No {section} have been added yet. Create the first one in the editor."
        return EmptyState(icon="database", title=f"No {section} available", description=message, cls="py-4")
    return Div(
        *[
            A(
                Div(
                    Div(
                        Strong(item.title if not isinstance(item, AdminTestimonial) else item.author, cls="d-block"),
                        Span(
                            item.slug if isinstance(item, AdminService) else item.price if isinstance(item, AdminPricingTier)
                            else " · ".join(part for part in (item.role, item.company) if part),
                            cls="admin-module-copy small",
                        ),
                        cls="min-w-0",
                    ),
                    Badge("Visible" if item.visible else "Hidden", cls="text-bg-success" if item.visible else "text-bg-secondary"),
                    cls="d-flex justify-content-between align-items-start gap-2",
                ),
                href=f"/{section}?item={item.id}",
                cls="admin-workspace-item" + (" is-selected" if item.id == selected_id else ""),
            )
            for item in items
        ],
        cls="admin-workspace-list",
    )


def _service_form(item: AdminService | None):
    deliverables = "\n".join(item.deliverables) if item else ""
    return Form(
        Input(type="hidden", name="record_id", value=item.id if item else ""),
        Div(
            _field("URL slug", "slug", item.slug if item else "", required=True, placeholder="e.g. backend-api"),
            _field("Display order", "sort_order", str(item.sort_order) if item else "100", required=True),
            _field("Service title", "title", item.title if item else "", required=True, full=True),
            _field("Price label", "price", item.price if item else "", placeholder="From N250k"),
            _field("Timeline", "timeline", item.timeline if item else "", placeholder="3 - 6 weeks"),
            _field("Icon name", "icon", item.icon if item else "code-slash", placeholder="Bootstrap icon name"),
            _textarea("Short summary", "summary", item.summary if item else "", required=True),
            _textarea("Service lead", "lead", item.lead if item else "", required=True),
            _textarea("Deliverables", "deliverables", deliverables, help_text="One deliverable per line. Lines keep their public display order."),
            Div(
                Input(type="checkbox", name="visible", value="1", checked=item.visible if item else True, id="website-visible", cls="form-check-input"),
                Label("Visible on public site", for_="website-visible", cls="form-check-label"),
                cls="form-check col-12",
            ),
            cls="row g-3",
        ),
        Div(
            Div(id="website-save-status", cls="flex-grow-1"),
            A("Cancel", href="/services", cls="btn admin-muted-btn"),
            A("Create new", href="/services?new=1", cls="btn admin-muted-btn") if item else "",
            Button(Icon("check2", cls="me-1"), "Save Service", type="submit", cls="btn admin-module-btn"),
            cls="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-3",
        ),
        action="/services/save", method="post", hx_post="/services/save", hx_target="#website-save-status", hx_swap="innerHTML",
        cls="admin-panel-stack",
    )


def _pricing_form(item: AdminPricingTier | None):
    points = "\n".join(item.points) if item else ""
    return Form(
        Input(type="hidden", name="record_id", value=item.id if item else ""),
        Div(
            _field("Tier name", "title", item.title if item else "", required=True),
            _field("Display order", "sort_order", str(item.sort_order) if item else "100", required=True),
            _field("Price label", "price", item.price if item else "", required=True, placeholder="N80k+"),
            _textarea("Highlight", "highlight", item.highlight if item else "", required=True),
            _textarea("Included points", "points", points, help_text="One point per line, in the order shown publicly."),
            Div(
                Input(type="checkbox", name="visible", value="1", checked=item.visible if item else True, id="pricing-visible", cls="form-check-input"),
                Label("Visible on public site", for_="pricing-visible", cls="form-check-label"),
                cls="form-check col-12",
            ),
            cls="row g-3",
        ),
        Div(
            Div(id="website-save-status", cls="flex-grow-1"),
            A("Cancel", href="/pricing", cls="btn admin-muted-btn"),
            A("Create new", href="/pricing?new=1", cls="btn admin-muted-btn") if item else "",
            Button(Icon("check2", cls="me-1"), "Save Tier", type="submit", cls="btn admin-module-btn"),
            cls="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-3",
        ),
        action="/pricing/save", method="post", hx_post="/pricing/save", hx_target="#website-save-status", hx_swap="innerHTML",
        cls="admin-panel-stack",
    )


def _testimonial_form(item: AdminTestimonial | None):
    return Form(
        Input(type="hidden", name="record_id", value=item.id if item else ""),
        Div(
            _field("Author name", "author", item.author if item else "", required=True),
            _field("Display order", "sort_order", str(item.sort_order) if item else "100", required=True),
            _field("Role", "role", item.role if item else "", placeholder="e.g. Product Lead"),
            _field("Company", "company", item.company if item else ""),
            _textarea("Testimonial quote", "quote", item.quote if item else "", required=True),
            Div(
                Input(type="checkbox", name="visible", value="1", checked=item.visible if item else True, id="testimonial-visible", cls="form-check-input"),
                Label("Visible on public site", for_="testimonial-visible", cls="form-check-label"),
                cls="form-check col-12",
            ),
            cls="row g-3",
        ),
        Div(
            Div(id="website-save-status", cls="flex-grow-1"),
            A("Cancel", href="/testimonials", cls="btn admin-muted-btn"),
            A("Create new", href="/testimonials?new=1", cls="btn admin-muted-btn") if item else "",
            Button(Icon("check2", cls="me-1"), "Save Testimonial", type="submit", cls="btn admin-module-btn"),
            cls="d-flex flex-wrap align-items-center justify-content-end gap-2 mt-3",
        ),
        action="/testimonials/save", method="post", hx_post="/testimonials/save", hx_target="#website-save-status", hx_swap="innerHTML",
        cls="admin-panel-stack",
    )


def website_content_page(section: str, *, item_id: str = "", new: bool = False):
    is_services = section == "services"
    is_pricing = section == "pricing"
    title = "Services" if is_services else "Pricing" if is_pricing else "Testimonials"
    items = list_services() if is_services else list_pricing_tiers() if is_pricing else list_testimonials()
    selected = next((item for item in items if item.id == item_id), None) if item_id else None
    editing = bool(selected or new)
    count_label = f"{len(items)} public {title.lower()} records"
    list_panel = Card(
        Div(
            Div(H3(title, cls="admin-subsection-title mb-0"), Span(f"{len(items)}", cls="badge text-bg-secondary"), cls="d-flex justify-content-between align-items-center"),
            P("Choose a record to edit, or create a new one. Hidden records stay in Admin and are excluded from public pages.", cls="admin-module-copy small"),
            _record_list(items, section, item_id),
            A(Icon("plus-lg", cls="me-1"), f"New {title[:-1] if is_services else 'Tier' if is_pricing else 'Testimonial'}", href=f"/{section}?new=1", cls="btn admin-module-btn w-100 mt-3"),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )
    if editing:
        form = _service_form(selected) if is_services else _pricing_form(selected) if is_pricing else _testimonial_form(selected)
        editor = Card(
            A(
                Icon("arrow-left", cls="me-1"), f"All {title}", href=f"/{section}",
                cls="website-content-back-link d-md-none",
            ),
            H3((f"Edit {selected.title if not isinstance(selected, AdminTestimonial) else selected.author}" if selected else f"New {title[:-1] if is_services else 'Tier' if is_pricing else 'Testimonial'}"), cls="admin-subsection-title"),
            P("These fields map directly to the public site content model.", cls="admin-module-copy"),
            status_alert("Admin write access unavailable", "Configure the Supabase service role in the Admin runtime before saving.", "warning") if not service_role_is_configured() else "",
            form,
            cls="admin-surface-card h-100",
        )
    else:
        editor = Card(
            EmptyState(icon="pencil-square", title=f"Select a {title[:-1] if is_services else 'tier' if is_pricing else 'testimonial'}", description="Pick a record from the list or create one to edit public content.", cls="py-5"),
            cls="admin-surface-card h-100",
        )
    return page_frame(
        Div(
            Div(
                Div(H2(f"Public {title.lower()}", cls="admin-section-title mb-1"), P(count_label, cls="admin-module-copy mb-0")),
                A("View public section", href=f"{public_site_url(brand_profile()).rstrip('/')}#{'services' if section in {'services', 'pricing'} else 'testimonials'}", target="_blank", rel="noreferrer", cls="btn admin-muted-btn"),
                cls="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-3",
            ),
            Row(
                Col(list_panel, span=12, lg=4, cls="website-content-list-column"),
                Col(editor, span=12, lg=8, cls="website-content-editor-column"),
                cls="g-4 align-items-start website-content-workspace" + (" is-editing" if editing else ""),
            ),
            cls="admin-panel-stack",
        ),
        current=f"/{section}", title=title,
    )


def _home_textarea(label: str, name: str, value: str, help_text: str, *, rows: int = 5):
    return Div(
        Label(label, for_=f"home-{name}", cls="form-label admin-field-label"),
        Textarea(value, name=name, id=f"home-{name}", rows=rows, cls="form-control admin-form-control"),
        P(help_text, cls="admin-module-copy small mb-0"),
        cls="mb-3",
    )


def _home_form(item: AdminHomeContent, image_assets):
    return Form(
        _home_textarea("Hero role titles", "hero_roles", "\n".join(item.hero_roles), "One rotating role title per line; up to eight."),
        _textarea("Hero summary", "hero_summary", item.hero_summary, required=True),
        _textarea("About summary", "about_summary", item.about_summary, required=True),
        _home_textarea("Journey paragraphs", "journey_paragraphs", "\n".join(item.journey_paragraphs), "One paragraph per line; keep each paragraph under 1,600 characters.", rows=7),
        _home_textarea("About stats", "about_stats", "\n".join(f"{value} | {label}" for value, label in item.about_stats), "One 'value | label' pair per line."),
        _home_textarea("CV highlights", "cv_highlights", "\n".join(f"{title} | {copy}" for title, copy in item.cv_highlights), "One 'heading | supporting copy' pair per line."),
        _home_textarea("Search keywords", "seo_keywords", "\n".join(item.seo_keywords), "One public search keyword per line; up to 32."),
        Div(
            H3("Public images", cls="admin-subsection-title"),
            P("Choose images already in Media. New uploads belong in the Media Library and become available here.", cls="admin-module-copy"),
            media_picker_field("Profile photo", "profile_image_url", item.profile_image_url, assets=image_assets),
            media_picker_field("Home hero background", "hero_background_url", item.hero_background_url, assets=image_assets),
            media_picker_field("Booking page background", "booking_background_url", item.booking_background_url, assets=image_assets),
            media_picker_field("CV page background", "cv_background_url", item.cv_background_url, assets=image_assets),
            cls="admin-panel-stack",
        ),
        Div(
            Button(Icon("check2", cls="me-1"), "Save Home Content", type="submit", cls="btn admin-module-btn"),
            Span("Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving", cls="admin-save-note"),
            cls="admin-form-actions mt-3",
        ),
        action="/website-content/save", method="post", hx_post="/website-content/save",
        hx_target="#website-home-save-status", hx_swap="innerHTML", cls="admin-panel-stack",
    )


def home_content_page():
    item = get_site_home_content()
    image_assets = list_media_assets(kind="image")
    cv_work = list_work_history()
    cv_skills = list_core_skills()
    cv_source_panel = Card(
        H3("Skills and experience come from the CV", cls="admin-subsection-title mb-1"),
        P(
            f"The public homepage reuses the first 3 of {len(cv_work)} CV work-history entries and the first 8 of {len(cv_skills)} CV core skills. Edit them in one place in the CV workspace; this page does not keep a second copy.",
            cls="admin-module-copy mb-3",
        ),
        A(Icon("file-earmark-person"), " Edit CV content", href="/cv", cls="btn admin-muted-btn"),
        cls="admin-surface-card mb-3",
    )
    editor = Card(
        H3("Home page content", cls="admin-subsection-title"),
        P("Edit homepage-specific hero and About copy, stats, highlights, search keywords, and image assignments here.", cls="admin-module-copy"),
        status_alert("Admin write access unavailable", "Configure the Supabase service role in the Admin runtime before saving.", "warning") if not service_role_is_configured() else "",
        status_alert("Home content not initialized", "Apply the home content database migration before editing this record.", "info") if item is None else "",
        Div(id="website-home-save-status"),
        _home_form(item, image_assets) if item else "",
        cls="admin-surface-card admin-panel-stack",
    )
    return page_frame(
        Div(
            Div(
                Div(H2("Home Page", cls="admin-section-title mb-1"), P("Public home-page copy and imagery", cls="admin-module-copy mb-0")),
                A("View public site", href=public_site_url(brand_profile()), target="_blank", rel="noreferrer", cls="btn admin-muted-btn"),
                cls="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-3",
            ),
            cv_source_panel,
            editor,
        ),
        current="/website-content", title="Home Page",
    )
