"""Public document routes — client-facing document portal."""

from __future__ import annotations

from typing import Any

try:
    from ..config import settings
    from ..infrastructure.deal_repository import save_document_response
    from ..presentation.pages.public_documents import document_portal_page
except ImportError:
    from config import settings
    from infrastructure.deal_repository import save_document_response
    from presentation.pages.public_documents import document_portal_page


def setup_document_routes(app: Any) -> None:
    @app.get("/documents/{token}")
    def public_document(token: str) -> Any:
        return document_portal_page(token=token)

    @app.post("/documents/{token}/respond")
    def public_document_respond(
        token: str,
        action: str = "",
        responder_name: str = "",
        responder_email: str = "",
        comment: str = "",
    ) -> Any:
        success, tone, message = save_document_response(
            token=token,
            action=action,
            responder_name=responder_name,
            responder_email=responder_email,
            comment=comment,
        )
        return document_portal_page(token=token, message=message, tone=tone if success else tone)
