"""Smoke tests for Neo Admin."""

from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import sys

from starlette.testclient import TestClient

os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_ANON_KEY"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["NEO_ADMIN_LOGIN_EMAIL"] = "admin@neoportfolio.dev"
os.environ["NEO_ADMIN_LOGIN_PASSWORD"] = "ChangeMe123!"

APP_PATH = Path(__file__).with_name("main.py")
ROOT = APP_PATH.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.config import settings

SPEC = importlib.util.spec_from_file_location("neo_admin_main", APP_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
app = MODULE.app

client = TestClient(app)


def sign_in() -> None:
    response = client.post(
        "/login",
        data={
            "login_email": settings.admin_login_email,
            "password": settings.admin_login_password,
            "next_path": "/",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_login_page_renders() -> None:
    response = client.get("/login")
    html = response.text
    assert response.status_code == 200
    assert "Sign In" in html
    assert "Login Email" in html
    assert "Password" in html
    assert "Use the seeded admin credentials first" not in html


def test_core_routes_render() -> None:
    sign_in()
    for route in ["/", "/projects", "/blog", "/cv", "/submissions", "/deals", "/media", "/settings"]:
        response = client.get(route)
        assert response.status_code == 200


def test_overview_contains_admin_shell_markers() -> None:
    sign_in()
    response = client.get("/")
    html = response.text
    assert "Neo Admin" in html
    assert "Overview" in html
    assert "Content Modules" in html
    assert 'class="admin-sidebar' in html
    assert 'id="admin-bottom-nav"' in html
    assert 'data-bs-target="#adminMobileDrawer"' in html
    assert "Published Projects" in html
    assert "GitHub Pulse" in html


def test_settings_workspace_renders_live_profile_shell() -> None:
    sign_in()
    response = client.get("/settings")
    html = response.text
    assert response.status_code == 200
    assert "Settings Workspace" in html
    assert "Settings Editor" in html
    assert "Public identity" in html


def test_projects_workspace_renders_real_project_data() -> None:
    sign_in()
    response = client.get("/projects")
    html = response.text
    assert response.status_code == 200
    assert "Projects Workspace" in html
    assert "BackendForge - Multi-Agent FastAPI Builder" in html
    assert "Local" in html or "Supabase" in html
    assert "Project Editor" in html
    assert "Save Project" in html
    assert "New Category" in html


def test_blog_workspace_renders_real_blog_data() -> None:
    sign_in()
    response = client.get("/blog")
    html = response.text
    assert response.status_code == 200
    assert "Blog Workspace" in html
    assert "BackendForge: What Happens When 18 AI Agents Write Your FastAPI Backend" in html
    assert "Save Post" in html
    assert "HTML Content" in html


def test_cv_workspace_renders_real_cv_data() -> None:
    sign_in()
    response = client.get("/cv")
    html = response.text
    assert response.status_code == 200
    assert "CV Workspace" in html
    assert "Olorundare Micheal Babawale" in html
    assert "Save CV Profile" in html
    assert "Experience" in html


def test_submissions_workspace_renders_real_inbox_shell() -> None:
    sign_in()
    response = client.get("/submissions")
    html = response.text
    assert response.status_code == 200
    assert "Submissions Workspace" in html
    assert "Inbox Records" in html
    assert "Supabase" in html or "Pending" in html
    if "Verification Contact" in html or "Verification Booking" in html:
        assert "Convert to Deal" in html or "/deals?from_submission=" in html


def test_deals_workspace_renders_pipeline_shell() -> None:
    sign_in()
    response = client.get("/deals")
    html = response.text
    assert response.status_code == 200
    assert "Deals Workspace" in html
    assert "Pipeline Records" in html
    assert "Deal Studio" in html
    assert "Quick Document Studio" in html
    assert "Generate Quick Document" in html
    assert "Farm Operations Dashboard" in html


def test_deals_workspace_can_prefill_from_submission_query() -> None:
    sign_in()
    inbox = client.get("/submissions")
    html = inbox.text
    if "Convert to Deal" not in html:
        return
    marker = '/deals?from_submission='
    start = html.find(marker)
    assert start != -1
    end = html.find('"', start)
    href = html[start:end]
    response = client.get(href)
    detail = response.text
    assert response.status_code == 200
    assert "Deals Workspace" in detail
    assert "New client pipeline record" in detail or "Selected deal" in detail


def test_media_workspace_renders_library_shell() -> None:
    sign_in()
    response = client.get("/media")
    html = response.text
    assert response.status_code == 200
    assert "Media Workspace" in html
    assert "Asset Library" in html
    assert "Upload Workspace" in html


def test_project_save_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/projects/save",
        data={
            "original_slug": "backendforge",
            "slug": "backendforge",
            "title": "BackendForge - Multi-Agent FastAPI Builder",
            "category": "ai-ml",
            "summary": "Updated summary",
            "narrative": "Updated narrative",
            "tech_stack": "Python, FastAPI",
            "image_url": "/assets/images/hero-bg.jpg",
            "complexity": "95",
            "satisfaction": "97",
            "featured": "on",
            "published": "on",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Save not completed" in html
    assert "Supabase write path is not configured yet" in html or "Could not reach Supabase" in html or "Supabase rejected the save request" in html


def test_blog_save_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/blog/save",
        data={
            "original_slug": "backendforge-multi-agent-fastapi",
            "slug": "backendforge-multi-agent-fastapi",
            "title": "BackendForge: What Happens When 18 AI Agents Write Your FastAPI Backend",
            "category": "project",
            "summary": "Updated summary",
            "content_html": "<p>Updated body</p>",
            "image_url": "/assets/images/hero-bg.jpg",
            "read_minutes": "8",
            "tags": "FastAPI, AI Agents",
            "published": "on",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Save not completed" in html
    assert "Supabase write path is not configured yet" in html or "Could not reach Supabase" in html or "Supabase rejected the save request" in html


def test_cv_save_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/cv/save",
        data={
            "name": "Olorundare Micheal Babawale",
            "role": "Full-Stack & AI Systems Architect",
            "email": "meshelleva@gmail.com",
            "phone": "+2348064676590",
            "whatsapp": "+2349029952120",
            "location": "Ilorin, Kwara State, Nigeria",
            "github": "https://github.com/Evayoung",
            "linkedin": "https://linkedin.com/in/michealolorundare",
            "summary": "Updated summary",
            "core_skills": "Skill one\nSkill two",
            "competencies": "Competency one\nCompetency two",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Save not completed" in html
    assert "Supabase write path is not configured yet" in html or "Could not reach Supabase" in html or "Supabase rejected the save request" in html


def test_cv_delete_helper_uses_safe_scoped_query() -> None:
    from app.infrastructure import cv_repository

    calls: list[tuple[str, str, str]] = []

    def fake_rest_request(method: str, path: str, **kwargs):
        calls.append((method, path, kwargs.get("query", "")))
        return None

    original = cv_repository._rest_request
    cv_repository._rest_request = fake_rest_request
    try:
        cv_repository._delete_all_rows("cv_core_skills")
    finally:
        cv_repository._rest_request = original

    assert calls == [("DELETE", "cv_core_skills", "?id=not.is.null")]


def test_submissions_update_route_handles_missing_or_read_only_state() -> None:
    sign_in()
    response = client.post(
        "/submissions/save",
        data={
            "entry_id": "",
            "kind": "contact",
            "status": "new",
            "notes": "Follow up tomorrow",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Update not completed" in html


def test_deals_save_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/deals/save",
        data={
            "deal_id": "",
            "client_name": "Acme Labs",
            "client_email": "hello@acmelabs.dev",
            "client_phone": "+2348000000000",
            "company": "Acme Labs",
            "project_title": "Internal Ops Portal",
            "service_type": "custom-saas",
            "stage": "proposal",
            "document_kind": "proposal",
            "document_status": "draft",
            "document_title": "Internal Ops Portal Proposal",
            "summary": "A structured summary",
            "background_text": "Client background and objective",
            "scope_notes": "Scope notes",
            "option_notes_text": "Option A | Focused build | 100000",
            "tech_stack": "FastHTML, Supabase",
            "timeline_text": "3 weeks",
            "payment_terms": "50% upfront",
            "line_items": "Discovery | Workshop | 1 | 100000",
            "exclusions_text": "No ecommerce",
            "closing_note": "Ready to proceed after approval",
            "amount_ngn": "100000",
            "deposit_percent": "50",
            "valid_until": "2026-05-12",
            "due_date": "",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Save not completed" in html
    assert "Supabase write path is not configured yet" in html or "Could not reach Supabase" in html or "Supabase rejected the deal save request" in html


def test_quick_document_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/deals/quick",
        data={
            "client_name": "Friendly Client",
            "client_email": "friend@example.com",
            "client_phone": "+2348000000001",
            "company": "",
            "project_title": "Quick Invoice Task",
            "document_kind": "invoice",
            "document_status": "draft",
            "document_title": "Quick Invoice",
            "summary": "A lightweight invoice without a full lead workflow.",
            "line_items": "",
            "payment_terms": "Due on receipt",
            "amount_ngn": "50000",
            "deposit_percent": "100",
            "valid_until": "",
            "due_date": "2026-05-15",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Quick document not created" in html
    assert "Supabase write path is not configured yet" in html or "Could not reach Supabase" in html or "Supabase rejected the deal save request" in html


def test_deal_document_update_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/deals/documents/update",
        data={
            "deal_id": "deal-olivette",
            "document_id": "doc-olivette-invoice",
            "document_kind": "invoice",
            "status": "paid",
        },
    )
    html = response.text
    assert response.status_code == 200
    assert "Update not completed" in html
    assert "cannot be saved from this environment" in html or "Could not reach Supabase" in html or "Supabase rejected the document workflow update" in html


def test_deal_document_pdf_route_serves_pdf() -> None:
    sign_in()
    response = client.get("/deals/deal-farmtech/documents/proposal/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")


def test_public_document_route_is_accessible_without_login() -> None:
    response = client.get("/documents/farmtech-proposal-demo", follow_redirects=False)
    html = response.text
    assert response.status_code == 200
    assert "Farm Operations Dashboard Proposal" in html
    assert "Background &amp; Objective" in html or "Background & Objective" in html
    assert "Your Response" in html or "Respond" in html
    assert "Download PDF" in html


def test_public_invoice_route_shows_payment_account_actions() -> None:
    response = client.get("/documents/olivette-invoice-demo", follow_redirects=False)
    html = response.text
    assert response.status_code == 200
    assert "Payment Account" in html
    assert "Copy Account Number" in html
    assert "I Have Paid" in html


def test_public_document_response_route_reports_read_only_without_supabase_service_role() -> None:
    response = client.post(
        "/documents/farmtech-proposal-demo/respond",
        data={
            "responder_name": "Client Reviewer",
            "responder_email": "client@example.com",
            "comment": "Looks good so far.",
            "action": "accepted",
        },
        follow_redirects=False,
    )
    html = response.text
    assert response.status_code == 200
    assert "cannot be recorded from this environment" in html or "Could not reach Supabase" in html or "Supabase rejected the document response" in html


def test_media_upload_route_reports_read_only_without_supabase_service_role() -> None:
    sign_in()
    response = client.post(
        "/media/upload",
        data={
            "title": "Homepage Hero",
            "kind": "image",
            "alt_text": "Hero visual",
            "current_kind": "all",
            "current_search": "",
        },
        files={"asset_file": ("hero.png", io.BytesIO(b"fake-image"), "image/png")},
    )
    html = response.text
    assert response.status_code == 200
    assert "Media Workspace" in html
    assert "Supabase write path is not configured yet" in html or "Could not reach Supabase" in html or "Supabase rejected the media upload" in html


def test_supabase_schema_file_exists() -> None:
    schema_path = Path(__file__).parent / "app" / "infrastructure" / "sql" / "001_initial_schema.sql"
    access_schema = Path(__file__).parent / "app" / "infrastructure" / "sql" / "002_admin_access.sql"
    pipeline_schema = Path(__file__).parent / "app" / "infrastructure" / "sql" / "003_client_pipeline.sql"
    media_schema = Path(__file__).parent / "app" / "infrastructure" / "sql" / "004_media_assets.sql"
    document_schema = Path(__file__).parent / "app" / "infrastructure" / "sql" / "005_document_links_and_accounts.sql"
    hardening_schema = Path(__file__).parent / "app" / "infrastructure" / "sql" / "006_production_hardening.sql"
    assert schema_path.exists()
    assert access_schema.exists()
    assert pipeline_schema.exists()
    assert media_schema.exists()
    assert document_schema.exists()
    assert hardening_schema.exists()
    schema = schema_path.read_text(encoding="utf-8")
    access = access_schema.read_text(encoding="utf-8")
    pipeline = pipeline_schema.read_text(encoding="utf-8")
    media = media_schema.read_text(encoding="utf-8")
    document_links = document_schema.read_text(encoding="utf-8")
    hardening = hardening_schema.read_text(encoding="utf-8")
    assert "create table if not exists public.projects" in schema
    assert "create table if not exists public.blog_posts" in schema
    assert "create table if not exists public.cv_meta" in schema
    assert "create table if not exists public.contact_submissions" in schema
    assert "create table if not exists public.booking_requests" in schema
    assert "create table if not exists public.admin_access" in access
    assert "create table if not exists public.client_deals" in pipeline
    assert "create table if not exists public.client_documents" in pipeline
    assert "create table if not exists public.media_assets" in media
    assert "create table if not exists public.payment_accounts" in document_links
    assert "create table if not exists public.client_document_responses" in document_links
    assert "alter table public.client_deals enable row level security" in pipeline
    assert "alter table public.client_documents enable row level security" in pipeline
    assert "idx_client_documents_public_token" in pipeline
    assert "alter table public.media_assets enable row level security" in media
    assert "alter table public.payment_accounts enable row level security" in document_links
    assert "alter table public.client_document_responses enable row level security" in document_links
    assert "Neo Admin production hardening migration" in hardening
    assert "Service role manages client deals" in hardening
    assert "Public can read portfolio media objects" in hardening


def test_admin_deploy_files_exist() -> None:
    root = Path(__file__).parent
    assert (root / ".env.example").exists()
    assert (root / "requirements.txt").exists()
    assert (root / "vercel.json").exists()
    assert (root / "sync_supabase_seed.py").exists()


def test_pwa_assets_are_exposed() -> None:
    sign_in()
    home = client.get("/")
    manifest = client.get("/manifest.json")
    script = client.get("/assets/admin.js")
    worker = client.get("/sw.js")

    assert home.status_code == 200
    assert 'rel="manifest"' in home.text
    assert "Install App" in home.text

    assert manifest.status_code == 200
    manifest_json = manifest.json()
    assert manifest_json["display"] == "standalone"
    assert manifest_json["start_url"] == "/"
    assert manifest_json["short_name"] == "NeoAdmin"

    assert script.status_code == 200
    assert "adminInstallDrawer" in script.text

    assert worker.status_code == 200
    assert "CACHE_NAME" in worker.text
    assert "neo-admin-shell-v3" in worker.text


def test_pwa_routes_are_publicly_accessible() -> None:
    manifest = client.get("/manifest.json", follow_redirects=False)
    worker = client.get("/sw.js", follow_redirects=False)
    offline = client.get("/offline", follow_redirects=False)

    assert manifest.status_code == 200
    assert worker.status_code == 200
    assert offline.status_code == 200
