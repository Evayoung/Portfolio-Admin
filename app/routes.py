"""Route registration for Neo Admin."""

from __future__ import annotations

from typing import Any
from fasthtml.common import A, Div, Redirect
from starlette.datastructures import UploadFile
from starlette.responses import FileResponse, JSONResponse

try:
    from .infrastructure.auth_repository import authenticate_admin, save_admin_access
    from .infrastructure.blog_repository import save_blog_post
    from .infrastructure.cv_repository import save_cv_profile
    from .infrastructure.deal_pdf import build_deal_document_pdf
    from .infrastructure.deal_repository import get_deal, save_deal_document, save_document_response, save_quick_document, update_document_status
    from .infrastructure.media_repository import upload_media_asset
    from .infrastructure.payment_account_repository import save_payment_account
    from .infrastructure.project_repository import save_project
    from .infrastructure.settings_repository import save_site_profile
    from .infrastructure.submission_repository import update_submission
    from .presentation.pages.auth import login_page
    from .presentation.pages.blog_admin import blog_save_status_fragment, blog_workspace_page
    from .presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page
    from .presentation.pages.dashboard import overview_page
    from .presentation.pages.deals import deal_save_status_fragment, deals_workspace_page
    from .presentation.pages.media import media_workspace_page
    from .presentation.pages.public_documents import document_portal_page
    from .presentation.pages.projects import project_save_status_fragment, projects_page
    from .presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
    from .presentation.pages.submissions import submission_save_status_fragment, submissions_workspace_page
except ImportError:
    from infrastructure.auth_repository import authenticate_admin, save_admin_access
    from infrastructure.blog_repository import save_blog_post
    from infrastructure.cv_repository import save_cv_profile
    from infrastructure.deal_pdf import build_deal_document_pdf
    from infrastructure.deal_repository import save_deal_document
    from infrastructure.deal_repository import get_deal
    from infrastructure.deal_repository import save_document_response
    from infrastructure.deal_repository import save_quick_document
    from infrastructure.deal_repository import update_document_status
    from infrastructure.media_repository import upload_media_asset
    from infrastructure.payment_account_repository import save_payment_account
    from infrastructure.project_repository import save_project
    from infrastructure.settings_repository import save_site_profile
    from infrastructure.submission_repository import update_submission
    from presentation.pages.auth import login_page
    from presentation.pages.blog_admin import blog_save_status_fragment, blog_workspace_page
    from presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page
    from presentation.pages.dashboard import overview_page
    from presentation.pages.deals import deal_save_status_fragment, deals_workspace_page
    from presentation.pages.media import media_workspace_page
    from presentation.pages.public_documents import document_portal_page
    from presentation.pages.projects import project_save_status_fragment, projects_page
    from presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
    from presentation.pages.submissions import submission_save_status_fragment, submissions_workspace_page


def setup_routes(app: Any) -> None:
    @app.get("/login")
    def login(session, next_path: str = "/") -> Any:
        if session.get("admin_authenticated"):
            return Redirect(_safe_next_path(next_path))
        return login_page(next_path=_safe_next_path(next_path))

    @app.post("/login")
    def login_submit(session, login_email: str = "", password: str = "", next_path: str = "/") -> Any:
        result = authenticate_admin(login_email, password)
        if not result.success:
            return login_page(next_path=_safe_next_path(next_path), message=result.message, tone=result.tone, login_email=login_email)
        session["admin_authenticated"] = True
        session["admin_login_email"] = result.login_email
        return Redirect(_safe_next_path(next_path))

    @app.get("/logout")
    def logout(session) -> Any:
        session.clear()
        return Redirect("/login")

    @app.get("/")
    def overview() -> Any:
        return overview_page()

    @app.get("/projects")
    def projects(slug: str = "", category: str = "all", featured: str = "0", search: str = "") -> Any:
        return projects_page(slug=slug, category=category, featured=featured, search=search)

    @app.post("/projects/save")
    def project_save(
        original_slug: str = "",
        slug: str = "",
        title: str = "",
        category: str = "",
        category_custom: str = "",
        summary: str = "",
        narrative: str = "",
        tech_stack: str = "",
        image_url: str = "",
        complexity: str = "0",
        satisfaction: str = "0",
        featured: str = "",
        published: str = "",
    ) -> Any:
        result = save_project(
            original_slug=original_slug,
            slug=slug,
            title=title,
            category=category,
            category_custom=category_custom,
            summary=summary,
            narrative=narrative,
            tech_stack=tech_stack,
            image_url=image_url,
            complexity=complexity,
            satisfaction=satisfaction,
            featured=bool(featured),
            published=bool(published),
        )
        title_text = "Project saved" if result.success else "Save not completed"
        return project_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.get("/blog")
    def blog(slug: str = "", category: str = "all", search: str = "") -> Any:
        return blog_workspace_page(slug=slug, category=category, search=search)

    @app.post("/blog/save")
    def blog_save(
        original_slug: str = "",
        slug: str = "",
        title: str = "",
        category: str = "",
        summary: str = "",
        content_html: str = "",
        image_url: str = "",
        read_minutes: str = "5",
        tags: str = "",
        published: str = "",
    ) -> Any:
        result = save_blog_post(
            original_slug=original_slug,
            slug=slug,
            title=title,
            category=category,
            summary=summary,
            content_html=content_html,
            image_url=image_url,
            read_minutes=read_minutes,
            tags=tags,
            published=bool(published),
        )
        title_text = "Blog post saved" if result.success else "Save not completed"
        return blog_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.get("/cv")
    def cv() -> Any:
        return cv_workspace_page()

    @app.post("/cv/save")
    def cv_save(
        name: str = "",
        role: str = "",
        email: str = "",
        phone: str = "",
        whatsapp: str = "",
        location: str = "",
        github: str = "",
        linkedin: str = "",
        summary: str = "",
        core_skills: str = "",
        competencies: str = "",
    ) -> Any:
        result = save_cv_profile(
            name=name,
            role=role,
            email=email,
            phone=phone,
            whatsapp=whatsapp,
            location=location,
            github=github,
            linkedin=linkedin,
            summary=summary,
            core_skills=core_skills,
            competencies=competencies,
        )
        title_text = "CV profile saved" if result.success else "Save not completed"
        return cv_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.get("/submissions")
    def submissions(entry_id: str = "", kind: str = "all", status: str = "all", search: str = "") -> Any:
        return submissions_workspace_page(entry_id=entry_id, kind=kind, status=status, search=search)

    @app.post("/submissions/save")
    def submissions_save(
        entry_id: str = "",
        kind: str = "",
        status: str = "",
        notes: str = "",
    ) -> Any:
        result = update_submission(entry_id=entry_id, kind=kind, status=status, notes=notes)
        title_text = "Submission updated" if result.success else "Update not completed"
        return submission_save_status_fragment(title_text, result.message, tone=result.tone)

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
                    A("Download PDF", href=f"/deals/{result.deal_id}/documents/{document.kind}/pdf", target="_blank", cls="btn admin-install-btn mt-3"),
                    A("Open Deal Record", href=f"/deals?deal_id={result.deal_id}", cls="btn admin-install-btn mt-3"),
                    cls="d-flex flex-wrap gap-2",
                )
        return Div(deal_save_status_fragment(title_text, result.message, tone=result.tone), actions)

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

    @app.get("/media")
    def media(kind: str = "all", search: str = "") -> Any:
        return media_workspace_page(kind=kind, search=search)

    @app.post("/media/upload")
    def media_upload(
        title: str = "",
        kind: str = "image",
        alt_text: str = "",
        current_kind: str = "all",
        current_search: str = "",
        asset_file: UploadFile | None = None,
    ) -> Any:
        result = upload_media_asset(title=title, kind=kind, alt_text=alt_text, asset_file=asset_file)
        return media_workspace_page(
            kind=current_kind,
            search=current_search,
            message=result.message,
            tone=result.tone,
            public_url=result.public_url or "",
        )

    @app.get("/settings")
    def settings_page() -> Any:
        return settings_workspace_page()

    @app.post("/settings/save")
    def settings_save(
        site_name: str = "",
        site_url: str = "",
        full_name: str = "",
        role: str = "",
        email: str = "",
        phone: str = "",
        whatsapp: str = "",
        location: str = "",
        github: str = "",
        linkedin: str = "",
        seo_title: str = "",
        seo_description: str = "",
    ) -> Any:
        result = save_site_profile(
            site_name=site_name,
            site_url=site_url,
            full_name=full_name,
            role=role,
            email=email,
            phone=phone,
            whatsapp=whatsapp,
            location=location,
            github=github,
            linkedin=linkedin,
            seo_title=seo_title,
            seo_description=seo_description,
        )
        title_text = "Settings saved" if result.success else "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/settings/access")
    def settings_access_save(
        login_email: str = "",
        password: str = "",
        confirm_password: str = "",
    ) -> Any:
        result = save_admin_access(login_email=login_email, password=password, confirm_password=confirm_password)
        title_text = "Admin access saved" if result.success else "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/settings/accounts")
    def settings_account_save(
        label: str = "",
        bank_name: str = "",
        account_name: str = "",
        account_number: str = "",
        note: str = "",
        is_default: str = "",
    ) -> Any:
        result = save_payment_account(
            label=label,
            bank_name=bank_name,
            account_name=account_name,
            account_number=account_number,
            note=note,
            is_default=bool(is_default),
        )
        title_text = "Payment account saved" if result.success else "Save not completed"
        return settings_save_status_fragment(title_text, result.message, tone=result.tone)


def _safe_next_path(next_path: str) -> str:
    candidate = (next_path or "/").strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return "/"
    return candidate
