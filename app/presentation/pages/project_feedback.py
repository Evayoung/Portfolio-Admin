"""Private client feedback page and admin feedback workspace."""

from __future__ import annotations

from fasthtml.common import A, Div, Form, H1, H2, H3, Label, Link, P, Span, Strong, Textarea
from faststrap import Badge, Button, Card, EmptyState, Icon, Input, SEO, Select

from app.config import settings
from app.infrastructure.deal_repository import list_deals
from app.infrastructure.project_feedback_repository import list_project_feedback
from app.infrastructure.settings_repository import get_site_profile
from app.presentation.shell import page_frame


def _client_feedback_page(token: str, *, message: str = "", submitted: bool = False, invalid: bool = False):
    rows = []
    from app.infrastructure.project_feedback_repository import get_feedback_by_token
    feedback = get_feedback_by_token(token)
    profile = get_site_profile()
    if feedback:
        deal = feedback.get("client_deals") or {}
        title = str(deal.get("project_title") or "Your project")
        submitted = submitted or bool(feedback.get("submitted_at"))
    else:
        title = "Project feedback"
        invalid = True

    content = []
    if invalid:
        content = [H1("Feedback link unavailable", cls="project-feedback-title"), P("This link is invalid or no longer available. Please contact the project owner for help.", cls="project-feedback-copy")]
    elif submitted:
        content = [
            Div(Icon("check-circle-fill"), cls="project-feedback-success-icon"),
            H1("Thank you for your feedback", cls="project-feedback-title"),
            P("Your comments have been received privately. They will not appear publicly unless you separately gave permission to use a testimonial.", cls="project-feedback-copy"),
        ]
    else:
        content = [
            Span("PROJECT CLOSEOUT", cls="project-feedback-kicker"),
            H1("How did the project go?", cls="project-feedback-title"),
            P(title, cls="project-feedback-project"),
            P("Your private feedback helps improve future projects. A public testimonial is optional and requires your separate permission.", cls="project-feedback-copy"),
            Form(
                Div(
                    Label("Your rating", cls="project-feedback-label"),
                    Div(*[
                        Label(
                            Input("rating", input_type="radio", value=str(value), required=True, cls="project-feedback-rating-input"),
                            Span("★", aria_hidden="true"),
                            Span(f"{value} star{'s' if value != 1 else ''}", cls="visually-hidden"),
                            cls="project-feedback-rating-option",
                        ) for value in range(5, 0, -1)
                    ], cls="project-feedback-rating-options", role="radiogroup", aria_label="Project rating from 1 to 5 stars"),
                    cls="project-feedback-field",
                ),
                Div(
                    Label("Comments", for_="feedback-comments", cls="project-feedback-label"),
                    Textarea(name="comments", id="feedback-comments", rows=5, maxlength="4000", required=True, placeholder="What worked well? What could have gone better?", cls="project-feedback-textarea"),
                    cls="project-feedback-field",
                ),
                Div(
                    Label("Name (optional)", for_="feedback-name", cls="project-feedback-label"),
                    Input("reviewer_name", id="feedback-name", maxlength="120", autocomplete="name", cls="project-feedback-input"),
                    cls="project-feedback-field",
                ),
                Div(
                    Label("Email (optional)", for_="feedback-email", cls="project-feedback-label"),
                    Input("reviewer_email", input_type="email", id="feedback-email", maxlength="180", autocomplete="email", cls="project-feedback-input"),
                    cls="project-feedback-field",
                ),
                Div(
                    Label(
                        Input("testimonial_consent", input_type="checkbox", value="1", cls="project-feedback-consent-input"),
                        Span("I give permission for the separate quote below to be considered for a public testimonial. I understand it will not be published automatically.", cls="project-feedback-consent-copy"),
                        cls="project-feedback-consent",
                    ),
                    Div(
                        Label("Optional public quote", for_="testimonial-quote", cls="project-feedback-label"),
                        Textarea(name="testimonial_quote", id="testimonial-quote", rows=3, maxlength="1000", placeholder="Write only the words you are comfortable seeing publicly.", cls="project-feedback-textarea"),
                        cls="project-feedback-field",
                    ),
                ),
                Input("token", input_type="hidden", value=token),
                Button(Icon("send", cls="me-2"), "Send Private Feedback", type="submit", cls="project-feedback-submit"),
                action=f"/project-feedback/{token}/submit", method="post",
                cls="project-feedback-form",
            ),
        ]
    if message:
        rows.append(P(message, cls="project-feedback-alert"))
    return (
        *SEO(title=f"Project Feedback | {getattr(profile, 'site_name', settings.app_name)}", description="Share private project feedback."),
        Link(rel="stylesheet", href="/assets/css/doc-portal.css?v=20261014-feedback"),
        Div(
            Div(Span(getattr(profile, "site_name", settings.owner_name), cls="project-feedback-brand"), cls="project-feedback-brandbar"),
            Div(*rows, *content, cls="project-feedback-card"),
            cls="project-feedback-shell",
        ),
    )


def public_project_feedback_page(token: str, *, message: str = "", submitted: bool = False):
    return _client_feedback_page(token, message=message, submitted=submitted)


def _feedback_card(item: dict) -> Div:
    deal = item.get("client_deals") or {}
    status = "Awaiting client" if not item.get("submitted_at") else str(item.get("review_status") or "new").title()
    status_color = "warning" if not item.get("submitted_at") else "success" if status == "Reviewed" else "secondary"
    review = []
    if item.get("submitted_at"):
        review = [
            Div("★" * int(item.get("rating") or 0) + "☆" * (5 - int(item.get("rating") or 0)), cls="feedback-stars", aria_label=f"{item.get('rating')} out of 5 stars"),
            P(item.get("comments") or "", cls="admin-feedback-comment"),
            P(" · ".join(value for value in (item.get("reviewer_name") or "", item.get("reviewer_email") or "") if value), cls="admin-module-copy small"),
        ]
        if item.get("testimonial_consent") and item.get("testimonial_quote"):
            review.append(Div(
                P("Client gave permission to consider this quote for publication.", cls="admin-module-copy small mb-1"),
                P(f'“{item["testimonial_quote"]}”', cls="admin-feedback-quote"),
                A("Open Testimonials", href="/testimonials", cls="btn admin-muted-btn btn-sm"),
                cls="admin-feedback-consent mt-3",
            ))
        review.append(Form(
            Select(
                "review_status",
                *[(value, label.title(), value == (item.get("review_status") or "new")) for value, label in (("new", "New"), ("reviewed", "Reviewed"), ("archived", "Archived"))],
                cls="form-select admin-form-control", aria_label="Feedback review status",
            ),
            Input("feedback_id", input_type="hidden", value=item.get("id") or ""),
            Button("Save status", type="submit", cls="btn admin-muted-btn btn-sm mt-2"),
            action="/feedback/status", method="post",
            hx_post="/feedback/status", hx_target=f"#feedback-status-{item.get('id')}", hx_swap="innerHTML",
            cls="admin-feedback-status-form mt-2",
        ))
        review.append(Div(id=f"feedback-status-{item.get('id')}", cls="mt-2"))
    elif item.get("public_token"):
        link = f"{settings.base_url.rstrip('/')}/project-feedback/{item['public_token']}"
        review = [
            P("Share this private link with the client after delivery.", cls="admin-module-copy small"),
            Div(A(link, href=link, target="_blank", rel="noreferrer", cls="feedback-share-link"), cls="feedback-share-link-wrap"),
        ]
    return Div(
        Div(
            Div(H3(deal.get("project_title") or "Project", cls="admin-subsection-title mb-1"), P(deal.get("client_name") or "Client", cls="admin-module-copy mb-0")),
            Badge(status, cls=f"bg-{status_color} bg-opacity-10 text-{status_color}"),
            cls="d-flex align-items-start justify-content-between gap-3",
        ),
        *review,
        cls="admin-feedback-card",
    )


def project_feedback_admin_page(*, message: str = "", tone: str = "info"):
    feedback_rows = list_project_feedback()
    delivered = list_deals(stage="delivered")
    feedback_by_deal = {str(row.get("deal_id") or ""): row for row in feedback_rows}
    link_ready_deals = [deal for deal in delivered if not feedback_by_deal.get(deal.deal_id, {}).get("submitted_at")]
    submitted = sum(bool(row.get("submitted_at")) for row in feedback_rows)
    return page_frame(
        Div(
            P("Private project closeout feedback, separate from public testimonials.", cls="admin-module-copy"),
            Div(
                Div(Strong(str(submitted), cls="admin-metric-value"), Span("Submitted", cls="admin-metric-label"), cls="admin-feedback-stat"),
                Div(Strong(str(sum(not row.get("submitted_at") for row in feedback_rows)), cls="admin-metric-value"), Span("Awaiting client", cls="admin-metric-label"), cls="admin-feedback-stat"),
                cls="admin-feedback-stats",
            ),
            P(message, cls=f"alert alert-{tone} py-2") if message else "",
            Card(
                H2("Delivered projects", cls="admin-section-title"),
                P("Create a shareable feedback link for a delivered project. Existing active links are reused.", cls="admin-module-copy"),
                EmptyState(icon="check-circle", title="No delivered projects need a link", description="Mark a project Delivered in Deals, then come back here to request closeout feedback.") if not link_ready_deals else "",
                *[Div(
                    Div(H3(deal.project_title, cls="admin-subsection-title mb-1"), P(deal.client_name, cls="admin-module-copy mb-0")),
                    Form(
                        Input(type="hidden", name="deal_id", value=deal.deal_id),
                        Button(Icon("link-45deg", cls="me-1"), "Create / show link", type="submit", cls="btn admin-module-btn"),
                        action="/feedback/link", method="post",
                        hx_post="/feedback/link", hx_target=f"#feedback-link-{deal.deal_id}", hx_swap="innerHTML",
                    ),
                    Div(id=f"feedback-link-{deal.deal_id}", cls="feedback-link-result"),
                    cls="admin-feedback-ready-row",
                ) for deal in link_ready_deals],
                cls="admin-surface-card admin-feedback-panel",
            ),
            Div(
                H2("Feedback links and responses", cls="admin-section-title"),
                EmptyState(icon="chat-square-text", title="No client feedback yet", description="Links and submitted ratings or comments will appear here.") if not feedback_rows else "",
                *[_feedback_card(item) for item in feedback_rows],
                cls="admin-feedback-panel",
            ),
            cls="admin-panel-stack",
        ),
        current="/feedback", title="Project Feedback",
    )
