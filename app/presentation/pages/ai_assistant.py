"""Standalone AI Draft Assistant page — draft proposals, quotes, invoices, and more."""

from __future__ import annotations

from fasthtml.common import Div, Form, H2, H3, Input, Label, Option, P, Select, Span, Strong, Textarea
from faststrap import Card, Col, Row, SEO

from app.config import settings
from app.presentation.page_helpers import SectionWrap, loading_action_button, status_alert, textarea_field, toggle_pill_group
from app.presentation.shell import page_frame


def _ai_draft_options() -> list[tuple[str, str]]:
    return [
        ("proposal", "Proposal"),
        ("quote", "Quotation"),
        ("invoice", "Invoice"),
        ("scope", "Scope"),
        ("payment_terms", "Payment Terms"),
    ]


def ai_assistant_draft_result(title: str, message: str, tone: str = "info", draft: str = "") -> Div:
    """Reuse the same fragment from the deals page."""
    from app.presentation.pages.deals import ai_draft_result_fragment
    return ai_draft_result_fragment(title, message, tone, draft)


def ai_assistant_page() -> tuple:
    return (
        *SEO(
            title=f"{settings.app_name} | AI Draft Assistant",
            description="Generate proposals, quotes, invoices, scope, and payment drafts with Groq AI.",
            url=f"{settings.base_url}/ai-assistant",
        ),
        *page_frame(
            SectionWrap(
                "AI Draft Assistant",
                Card(
                    Form(
                        Div(
                            P("Draft Configuration", cls="admin-form-section-title"),
                            P("Generate draft text using Groq's LLM. Provide rough notes or context below — the more detail, the better the draft.", cls="admin-module-copy"),
                            Div(
                                Label("Draft Type", cls="admin-form-label"),
                                toggle_pill_group("draft_kind", _ai_draft_options(), selected_value="proposal"),
                                cls="admin-form-group",
                            ),
                            textarea_field(
                                "Context / Notes",
                                "context_text",
                                "",
                                rows=10,
                                placeholder="Paste notes, requirements, or any rough context you want the AI to use for drafting. The more detail you give, the better the draft will be.\n\nExample: Client needs a dashboard for farm operations tracking with field agent updates, reporting, and multi-role access. Budget around NGN 850k. Timeline 5 weeks.",
                            ),
                            Div(
                                loading_action_button("Generate AI Draft", endpoint="/ai-assistant/generate", target="#ai-assistant-result"),
                                Span("Powered by Groq. Review before using.", cls="admin-save-note"),
                                cls="admin-form-actions mt-3",
                            ),
                            Div(id="ai-assistant-result", cls="mt-3"),
                            cls="admin-panel-stack",
                        ),
                        cls="admin-surface-card",
                        action="/ai-assistant/generate",
                        method="post",
                        hx_post="/ai-assistant/generate",
                        hx_target="#ai-assistant-result",
                        hx_swap="innerHTML",
                        id="ai-assistant-form",
                    ),
                ),
            ),
            current="/ai-assistant",
            title="AI Draft Assistant",
        ),
    )
