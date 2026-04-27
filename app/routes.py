"""Route registration for Neo Admin."""

from __future__ import annotations

from typing import Any

try:
    from .infrastructure.blog_repository import save_blog_post
    from .infrastructure.cv_repository import save_cv_profile
    from .infrastructure.project_repository import save_project
    from .infrastructure.settings_repository import save_site_profile
    from .infrastructure.submission_repository import update_submission
    from .presentation.pages.blog_admin import blog_save_status_fragment, blog_workspace_page
    from .presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page
    from .presentation.pages.dashboard import overview_page
    from .presentation.pages.projects import project_save_status_fragment, projects_page
    from .presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
    from .presentation.pages.submissions import submission_save_status_fragment, submissions_workspace_page
except ImportError:
    from infrastructure.blog_repository import save_blog_post
    from infrastructure.cv_repository import save_cv_profile
    from infrastructure.project_repository import save_project
    from infrastructure.settings_repository import save_site_profile
    from infrastructure.submission_repository import update_submission
    from presentation.pages.blog_admin import blog_save_status_fragment, blog_workspace_page
    from presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page
    from presentation.pages.dashboard import overview_page
    from presentation.pages.projects import project_save_status_fragment, projects_page
    from presentation.pages.settings_admin import settings_save_status_fragment, settings_workspace_page
    from presentation.pages.submissions import submission_save_status_fragment, submissions_workspace_page


def setup_routes(app: Any) -> None:
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
