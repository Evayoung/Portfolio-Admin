"""Deal routes — workspace, CRUD, AI draft, document management."""

from __future__ import annotations

from typing import Any
from fasthtml.common import A, Button, Div
from starlette.responses import FileResponse, JSONResponse

try:
    from ..config import settings
    from ..infrastructure.ai_draft_repository import generate_document_draft
    from ..infrastructure.deal_pdf import build_deal_document_pdf
    from ..infrastructure.deal_repository import (
        get_deal,
        regenerate_document_link,
        resend_document_link,
        revoke_document_link,
        save_deal_document,
        save_quick_document,
        update_document_status,
    )
    from ..presentation.pages.deals import ai_draft_result_fragment, deal_save_status_fragment, deals_workspace_page
except ImportError:
    from config import settings
    from infrastructure.ai_draft_repository import generate_document_draft
    from infrastructure.deal_pdf import build_deal_document_pdf
    from infrastructure.deal_repository import (
        get_deal,
        regenerate_document_link,
        resend_document_link,
        revoke_document_link,
        save_deal_document,
        save_quick_document,
        update_document_status,
    )
    from presentation.pages.deals import ai_draft_result_fragment, deal_save_status_fragment, deals_workspace_page


def setup_deal_routes(app: Any) -> None:
    @app.get("/deals")
    def deals(deal_id: str = "", stage: str = "all", document_kind: str = "all", search: str = "", from_submission: str = "", from_kind: str = "") -> Any:
        return deals_workspace_page(
            deal_id=deal_id,
            stage=stage,
            document_kind=document_kind,
            search=search,
            from_submission=from_submission,
            from_kind=from_kind,
        )

    @app.get("/deals/{deal_id}/documents/{document_kind}/pdf")
    def deal_document_pdf(deal_id: str, document_kind: str) -> Any:
        deal = get_deal(deal_id)
        if not deal:
            return JSONResponse({"error": "Deal not found"}, status_code=404)
        if document_kind not in {"proposal", "quote", "invoice"}:
            return JSONResponse({"error": "Unsupported document type"}, status_code=404)
        pdf_path = build_deal_document_pdf(deal, document_kind)
        safe_title = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in deal.project_title.strip().replace(" ", "-")).strip("-") or "deal-document"
        filename = f"{safe_title}-{document_kind}.pdf"
        return FileResponse(pdf_path, filename=filename, media_type="application/pdf")

    @app.post("/deals/save")
    def deals_save(
        deal_id: str = "",
        client_name: str = "",
        client_email: str = "",
        client_phone: str = "",
        company: str = "",
        project_title: str = "",
        service_type: str = "",
        stage: str = "lead",
        document_kind: str = "proposal",
        document_status: str = "draft",
        document_title: str = "",
        summary: str = "",
        background_text: str = "",
        scope_notes: str = "",
        option_notes_text: str = "",
        tech_stack: str = "",
        timeline_text: str = "",
        payment_terms: str = "",
        line_items: str = "",
        exclusions_text: str = "",
        closing_note: str = "",
        payment_account_id: str = "",
        amount_ngn: str = "0",
        deposit_percent: str = "50",
        valid_until: str = "",
        due_date: str = "",
    ) -> Any:
        result = save_deal_document(
            deal_id=deal_id,
            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,
            company=company,
            project_title=project_title,
            service_type=service_type,
            stage=stage,
            document_kind=document_kind,
            document_status=document_status,
            document_title=document_title,
            summary=summary,
            background_text=background_text,
            scope_notes=scope_notes,
            option_notes_text=option_notes_text,
            tech_stack=tech_stack,
            timeline_text=timeline_text,
            payment_terms=payment_terms,
            line_items=line_items,
            exclusions_text=exclusions_text,
            closing_note=closing_note,
            payment_account_id=payment_account_id,
            amount_ngn=amount_ngn,
            deposit_percent=deposit_percent,
            valid_until=valid_until,
            due_date=due_date,
        )
        title_text = "Deal draft saved" if result.success else "Save not completed"
        return deal_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/deals/quick")
    def deals_quick_document_save(
        client_name: str = "",
        client_email: str = "",
        client_phone: str = "",
        company: str = "",
        project_title: str = "",
        document_kind: str = "invoice",
        document_status: str = "draft",
        document_title: str = "",
        summary: str = "",
        line_items: str = "",
        payment_terms: str = "",
        payment_account_id: str = "",
        amount_ngn: str = "0",
        deposit_percent: str = "100",
        valid_until: str = "",
        due_date: str = "",
    ) -> Any:
        result = save_quick_document(
            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,
            company=company,
            project_title=project_title,
            document_kind=document_kind,
            document_status=document_status,
            document_title=document_title,
            summary=summary,
            line_items=line_items,
            payment_terms=payment_terms,
            payment_account_id=payment_account_id,
            amount_ngn=amount_ngn,
            deposit_percent=deposit_percent,
            valid_until=valid_until,
            due_date=due_date,
        )
        title_text = "Quick document created" if result.success else "Quick document not created"
        actions = ""
        if result.success and result.deal_id:
            deal = get_deal(result.deal_id)
            document = next((item for item in deal.documents if item.kind == document_kind), deal.latest_document) if deal else None
            if document:
                actions = Div(
                    A("Open Client Link", href=f"/documents/{document.public_token}", target="_blank", cls="btn admin-module-btn mt-3"),
                    Button(
                        "Copy Client Link",
                        type="button",
                        cls="btn admin-install-btn mt-3",
                        data_copy_target=f"{settings.base_url.rstrip('/')}/documents/{document.public_token}",
                        data_copy_label="Copy Client Link",
                    ),
                    A("Download PDF", href=f"/deals/{result.deal_id}/documents/{document.kind}/pdf", target="_blank", cls="btn admin-install-btn mt-3"),
                    A("Open Deal Record", href=f"/deals?deal_id={result.deal_id}", cls="btn admin-install-btn mt-3"),
                    cls="d-flex flex-wrap gap-2",
                )
        return Div(deal_save_status_fragment(title_text, result.message, tone=result.tone), actions)

    @app.post("/deals/ai-draft")
    def deals_ai_draft(
        session,
        ai_draft_kind: str = "proposal",
        client_name: str = "",
        client_email: str = "",
        company: str = "",
        project_title: str = "",
        service_type: str = "",
        document_kind: str = "proposal",
        document_title: str = "",
        summary: str = "",
        background_text: str = "",
        scope_notes: str = "",
        option_notes_text: str = "",
        tech_stack: str = "",
        timeline_text: str = "",
        payment_terms: str = "",
        line_items: str = "",
        exclusions_text: str = "",
        closing_note: str = "",
        amount_ngn: str = "0",
        deposit_percent: str = "50",
        valid_until: str = "",
        due_date: str = "",
    ) -> Any:
        result = generate_document_draft(
            draft_kind=ai_draft_kind,
            actor_email=session.get("admin_login_email", ""),
            context={
                "client_name": client_name,
                "client_email": client_email,
                "company": company,
                "project_title": project_title,
                "service_type": service_type,
                "document_kind": document_kind,
                "document_title": document_title,
                "summary": summary,
                "background": background_text,
                "scope": scope_notes,
                "options": option_notes_text,
                "tech_stack": tech_stack,
                "timeline": timeline_text,
                "payment_terms": payment_terms,
                "line_items": line_items,
                "exclusions": exclusions_text,
                "closing_note": closing_note,
                "amount_ngn": amount_ngn,
                "deposit_percent": deposit_percent,
                "valid_until": valid_until,
                "due_date": due_date,
            },
        )
        title_text = "AI draft ready" if result.success else "AI draft not generated"
        return ai_draft_result_fragment(title_text, result.message, tone=result.tone, draft=result.draft)

    @app.post("/deals/documents/update")
    def deal_document_update(
        deal_id: str = "",
        document_id: str = "",
        document_kind: str = "",
        status: str = "",
    ) -> Any:
        success, tone, message = update_document_status(
            deal_id=deal_id,
            document_id=document_id,
            document_kind=document_kind,
            status=status,
        )
        title_text = "Document updated" if success else "Update not completed"
        return deal_save_status_fragment(title_text, message, tone=tone)

    @app.post("/deals/documents/link")
    def deal_document_link_action(
        deal_id: str = "",
        document_id: str = "",
        document_kind: str = "",
        action: str = "",
    ) -> Any:
        if action == "revoke":
            success, tone, message = revoke_document_link(deal_id=deal_id, document_id=document_id)
        elif action == "regenerate":
            success, tone, message = regenerate_document_link(deal_id=deal_id, document_id=document_id, document_kind=document_kind)
        elif action == "resend":
            success, tone, message = resend_document_link(document_id=document_id, document_kind=document_kind)
        else:
            success, tone, message = False, "warning", "Choose a valid document link action."
        title_text = "Document link updated" if success else "Link action not completed"
        return deal_save_status_fragment(title_text, message, tone=tone)
