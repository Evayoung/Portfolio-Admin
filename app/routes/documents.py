"""Public document routes — client-facing document portal."""

from __future__ import annotations

from typing import Any

from starlette.responses import FileResponse, JSONResponse, Response

try:
    from ..config import settings
    from ..infrastructure.deal_pdf import build_deal_document_pdf
    from ..infrastructure.deal_repository import get_document_by_token, record_document_view, reset_document_with_responses, save_document_response
    from ..presentation.page_helpers import toast_fragment
    from ..presentation.pages.public_documents import document_portal_page
except ImportError:
    from config import settings
    from infrastructure.deal_pdf import build_deal_document_pdf
    from infrastructure.deal_repository import get_document_by_token, record_document_view, reset_document_with_responses, save_document_response
    from presentation.page_helpers import toast_fragment
    from presentation.pages.public_documents import document_portal_page


def setup_document_routes(app: Any) -> None:
    @app.get("/documents/{token}")
    def public_document(token: str) -> Any:
        deal, doc = get_document_by_token(token)
        if doc:
            record_document_view(doc.document_id)
        return document_portal_page(token=token)

    @app.post("/documents/{token}/respond")
    def public_document_respond(
        token: str,
        action: str = "",
        responder_name: str = "",
        responder_email: str = "",
        comment: str = "",
        selected_package: str = "",
    ) -> Any:
        success, tone, message = save_document_response(
            token=token,
            action=action,
            responder_name=responder_name,
            responder_email=responder_email,
            comment=comment,
            selected_package=selected_package,
        )
        page = document_portal_page(token=token, message=message, tone=tone)
        from faststrap.presets import toast_response
        return toast_response(
            content=page,
            message=message,
            variant=tone,
        )

    @app.get("/documents/{token}/pdf")
    def public_document_pdf(token: str) -> Any:
        deal, doc = get_document_by_token(token)
        if not deal or not doc:
            return JSONResponse({"error": "Document not found"}, status_code=404)
        pdf_path = build_deal_document_pdf(deal, doc.kind)
        safe_title = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in deal.project_title.strip().replace(" ", "-")).strip("-") or "deal-document"
        filename = f"{safe_title}-{doc.kind}.pdf"
        return FileResponse(pdf_path, filename=filename, media_type="application/pdf")

    @app.post("/admin/document/reset")
    def reset_document_status(
        deal_id: str = "",
        document_id: str = "",
        document_kind: str = "",
    ) -> Any:
        """Reset a document back to 'sent' status and clear client responses."""
        success, tone, message = reset_document_with_responses(
            deal_id=deal_id,
            document_id=document_id,
            document_kind=document_kind,
        )
        if success:
            return (
                Response("", status_code=200, headers={"HX-Refresh": "true"}),
                toast_fragment("Document reset", message),
            )
        return toast_fragment("Reset failed", message, variant=tone)
