"""Public client closeout feedback and authenticated admin management routes."""

from __future__ import annotations

from typing import Any

from fasthtml.common import A, Div, P

from app.infrastructure.project_feedback_repository import (
    create_or_get_feedback_link,
    submit_project_feedback,
    update_feedback_review_status,
)
from app.presentation.pages.project_feedback import project_feedback_admin_page, public_project_feedback_page


def setup_project_feedback_routes(app: Any) -> None:
    @app.get("/project-feedback/{token}")
    def project_feedback(token: str):
        return public_project_feedback_page(token)

    @app.post("/project-feedback/{token}/submit")
    def project_feedback_submit(
        token: str,
        reviewer_name: str = "",
        reviewer_email: str = "",
        rating: str = "",
        comments: str = "",
        testimonial_consent: str = "",
        testimonial_quote: str = "",
    ):
        success, message = submit_project_feedback(
            token=token,
            reviewer_name=reviewer_name,
            reviewer_email=reviewer_email,
            rating=rating,
            comments=comments,
            testimonial_consent=testimonial_consent == "1",
            testimonial_quote=testimonial_quote,
        )
        return public_project_feedback_page(token, message=message, submitted=success)

    @app.get("/feedback")
    def feedback_admin(message: str = "", tone: str = "info"):
        return project_feedback_admin_page(message=message, tone=tone)

    @app.post("/feedback/link")
    def feedback_create_link(deal_id: str = ""):
        success, message, url = create_or_get_feedback_link(deal_id)
        if not success:
            return Div(message, cls="alert alert-warning py-2 mb-0")
        return Div(
            P(message, cls="admin-module-copy small mb-1"),
            A(url, href=url, target="_blank", rel="noreferrer", cls="feedback-share-link"),
            cls="feedback-link-result-card",
        )

    @app.post("/feedback/status")
    def feedback_update_status(feedback_id: str = "", review_status: str = "new"):
        success, message = update_feedback_review_status(feedback_id, review_status)
        return Div(message, cls=f"alert alert-{'success' if success else 'warning'} py-2 mb-0")
