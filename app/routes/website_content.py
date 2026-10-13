"""Routes for editing public Services and Pricing content."""

from __future__ import annotations

from typing import Any

from fasthtml.common import Div
from starlette.responses import Response

from app.infrastructure.audit_repository import record_audit_event
from app.infrastructure.website_content_repository import save_pricing_tier, save_service, save_site_home_content, save_testimonial
from app.presentation.page_helpers import status_alert, toast_fragment
from app.presentation.pages.website_content import home_content_page, website_content_page


def _save_response(result, *, label: str):
    if result.success:
        return (
            Response("", status_code=200, headers={"HX-Refresh": "true"}),
            toast_fragment(f"{label} saved", result.message),
        )
    return Div(
        status_alert("Save not completed", result.message, result.tone),
        cls="mb-2",
    )


def setup_website_content_routes(app: Any) -> None:
    @app.get("/website-content")
    def website_home_content():
        return home_content_page()

    @app.post("/website-content/save")
    def website_home_content_save(
        hero_roles: str = "", hero_summary: str = "", about_summary: str = "",
        journey_paragraphs: str = "", about_stats: str = "", cv_highlights: str = "", seo_keywords: str = "", profile_image_url: str = "",
        hero_background_url: str = "", booking_background_url: str = "", cv_background_url: str = "",
    ):
        result = save_site_home_content(
            hero_roles=hero_roles, hero_summary=hero_summary, about_summary=about_summary,
            journey_paragraphs=journey_paragraphs, about_stats=about_stats,
            cv_highlights=cv_highlights, seo_keywords=seo_keywords,
            profile_image_url=profile_image_url,
            hero_background_url=hero_background_url, booking_background_url=booking_background_url,
            cv_background_url=cv_background_url,
        )
        if result.success:
            record_audit_event(action="update_public_content", target_type="site_home_content", target_id="primary", detail="Home page content and imagery")
        return _save_response(result, label="Home content")

    @app.get("/services")
    def services(item: str = "", new: str = ""):
        return website_content_page("services", item_id=item, new=new == "1")

    @app.post("/services/save")
    def service_save(
        record_id: str = "", slug: str = "", title: str = "", summary: str = "", lead: str = "",
        deliverables: str = "", timeline: str = "", price: str = "", icon: str = "",
        visible: str = "", sort_order: str = "100",
    ):
        result = save_service(
            record_id=record_id, slug=slug, title=title, summary=summary, lead=lead,
            deliverables=deliverables, timeline=timeline, price=price, icon=icon,
            visible=visible == "1", sort_order=sort_order,
        )
        if result.success:
            record_audit_event(action="update_public_content", target_type="service", target_id=result.record_id, detail=title[:120])
        return _save_response(result, label="Service")

    @app.get("/pricing")
    def pricing(item: str = "", new: str = ""):
        return website_content_page("pricing", item_id=item, new=new == "1")

    @app.post("/pricing/save")
    def pricing_save(
        record_id: str = "", title: str = "", price: str = "", highlight: str = "",
        points: str = "", visible: str = "", sort_order: str = "100",
    ):
        result = save_pricing_tier(
            record_id=record_id, title=title, price=price, highlight=highlight, points=points,
            visible=visible == "1", sort_order=sort_order,
        )
        if result.success:
            record_audit_event(action="update_public_content", target_type="pricing_tier", target_id=result.record_id, detail=title[:120])
        return _save_response(result, label="Pricing tier")

    @app.get("/testimonials")
    def testimonials(item: str = "", new: str = ""):
        return website_content_page("testimonials", item_id=item, new=new == "1")

    @app.post("/testimonials/save")
    def testimonial_save(
        record_id: str = "", author: str = "", role: str = "", company: str = "", quote: str = "",
        visible: str = "", sort_order: str = "100",
    ):
        result = save_testimonial(
            record_id=record_id, author=author, role=role, company=company, quote=quote,
            visible=visible == "1", sort_order=sort_order,
        )
        if result.success:
            record_audit_event(action="update_public_content", target_type="testimonial", target_id=result.record_id, detail=author[:120])
        return _save_response(result, label="Testimonial")
