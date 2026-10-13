"""Standalone AI Draft Assistant page — draft proposals, quotes, invoices, and more."""

from __future__ import annotations

from fasthtml.common import Div, Form, H3, Label, P, Span
from faststrap import Card, Col, EmptyState, Row, SEO

from app.config import settings
from app.presentation.page_helpers import loading_action_button, textarea_field, toggle_pill_group
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
    """Render the shared draft result fragment used by document workflows."""
    from app.presentation.pages.deal_helpers import deal_generate_result_fragment
    return deal_generate_result_fragment(title, message, tone, draft)


def ai_assistant_page() -> tuple:
    draft_form = Form(
        Div(
            H3("Draft inputs", cls="admin-subsection-title"),
            P("Choose the document type, then add the client and project context the draft should use.", cls="admin-module-copy"),
            Div(
                Label("Draft Type", cls="admin-form-label"),
                toggle_pill_group("draft_kind", _ai_draft_options(), selected_value="proposal"),
                cls="admin-form-group",
            ),
            textarea_field(
                "Context / Notes",
                "context_text",
                "",
                rows=12,
                placeholder="Include the client, project goals, scope, budget, timeline, and any constraints. For example: a farm operations dashboard with field updates and reporting, a budget around NGN 850k, and a five-week delivery window.",
            ),
            Div(
                loading_action_button("Generate Draft", endpoint="/ai-assistant/generate", target="#ai-assistant-result"),
                Span("AI output is a draft. Review it before sharing.", cls="admin-save-note"),
                cls="admin-form-actions mt-3",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card",
        action="/ai-assistant/generate",
        method="post",
        hx_post="/ai-assistant/generate",
        hx_target="#ai-assistant-result",
        hx_swap="innerHTML",
        id="ai-assistant-form",
    )
    result_panel = Card(
        Div(
            H3("Generated draft", cls="admin-subsection-title"),
            P("The result stays here while you refine the context or generate another version.", cls="admin-module-copy"),
            Div(
                EmptyState(
                    icon="stars",
                    title="Your draft will appear here",
                    description="Add context on the left and generate a draft to review or copy.",
                    cls="py-5",
                ),
                id="ai-assistant-result",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )
    return (
        *SEO(
            title=f"{settings.app_name} | AI Draft Assistant",
            description="Generate proposals, quotes, invoices, scope, and payment drafts with Groq AI.",
            url=f"{settings.base_url}/ai-assistant",
        ),
        *page_frame(
            Div(
                P("Generate a first draft, review it beside the source context, and refine it without losing either.", cls="admin-module-copy mb-3"),
                Row(
                    Col(draft_form, span=12, lg=5),
                    Col(result_panel, span=12, lg=7),
                    cls="g-4 align-items-start",
                ),
            ),
            current="/ai-assistant",
            title="AI Draft Assistant",
        ),
    )
