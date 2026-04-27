"""Smoke tests for Neo Admin."""

from __future__ import annotations

import importlib.util
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
    for route in ["/", "/projects", "/blog", "/cv", "/submissions", "/settings"]:
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


def test_supabase_schema_file_exists() -> None:
    schema_path = Path(__file__).parent / "app" / "infrastructure" / "sql" / "001_initial_schema.sql"
    access_schema = Path(__file__).parent / "app" / "infrastructure" / "sql" / "002_admin_access.sql"
    assert schema_path.exists()
    assert access_schema.exists()
    schema = schema_path.read_text(encoding="utf-8")
    access = access_schema.read_text(encoding="utf-8")
    assert "create table if not exists public.projects" in schema
    assert "create table if not exists public.blog_posts" in schema
    assert "create table if not exists public.cv_meta" in schema
    assert "create table if not exists public.contact_submissions" in schema
    assert "create table if not exists public.booking_requests" in schema
    assert "create table if not exists public.admin_access" in access


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
