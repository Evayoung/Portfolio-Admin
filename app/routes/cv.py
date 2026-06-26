"""CV routes — workspace page and save handler."""

from __future__ import annotations

from typing import Any

try:
    from ..infrastructure.cv_repository import save_cv_profile
    from ..presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page
except ImportError:
    from infrastructure.cv_repository import save_cv_profile
    from presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page


def setup_cv_routes(app: Any) -> None:
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
        work_history: str = "",
        education: str = "",
        certifications: str = "",
        tool_categories: str = "",
        languages: str = "",
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
            work_history=work_history,
            education=education,
            certifications=certifications,
            tool_categories=tool_categories,
            languages=languages,
        )
        title_text = "CV profile saved" if result.success else "Save not completed"
        return cv_save_status_fragment(title_text, result.message, tone=result.tone)
