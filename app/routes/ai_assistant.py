"""AI Assistant routes — standalone draft generation outside the Deals editor."""

from __future__ import annotations

from typing import Any

try:
    from ..config import settings
    from ..infrastructure.ai_draft_repository import generate_document_draft
except ImportError:
    from config import settings
    from infrastructure.ai_draft_repository import generate_document_draft


def setup_ai_assistant_routes(app: Any) -> None:
    @app.get("/ai-assistant")
    def ai_assistant_get() -> Any:
        from ..presentation.pages.ai_assistant import ai_assistant_page
        return ai_assistant_page()

    @app.post("/ai-assistant/generate")
    def ai_assistant_generate(
        session,
        draft_kind: str = "proposal",
        context_text: str = "",
    ) -> Any:
        from ..presentation.pages.ai_assistant import ai_assistant_draft_result

        result = generate_document_draft(
            draft_kind=draft_kind,
            actor_email=session.get("admin_login_email", ""),
            context={"context": context_text or "No additional context provided."},
        )
        title_text = "AI draft ready" if result.success else "AI draft not generated"
        return ai_assistant_draft_result(title_text, result.message, tone=result.tone, draft=result.draft)
