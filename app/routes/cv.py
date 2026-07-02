"""CV routes — workspace page and save handler."""

from __future__ import annotations

import json
from typing import Any

from starlette.responses import Response

try:
    from ..infrastructure.cv_repository import (
        save_cv_profile,
        save_cv_section_certifications,
        save_cv_section_competencies,
        save_cv_section_core_skills,
        save_cv_section_education,
        save_cv_section_languages,
        save_cv_section_tool_categories,
        save_cv_section_work_history,
    )
    from ..presentation.page_helpers import toast_fragment
    from ..presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page
except ImportError:
    from infrastructure.cv_repository import (
        save_cv_profile,
        save_cv_section_certifications,
        save_cv_section_competencies,
        save_cv_section_core_skills,
        save_cv_section_education,
        save_cv_section_languages,
        save_cv_section_tool_categories,
        save_cv_section_work_history,
    )
    from presentation.page_helpers import toast_fragment
    from presentation.pages.cv_admin import cv_save_status_fragment, cv_workspace_page


def _section_save_response(result) -> Any:
    """Return HX-Refresh with toast on success, status alert on failure."""
    if result.success:
        return (
            Response("", status_code=200, headers={"HX-Refresh": "true"}),
            toast_fragment("Section saved", result.message),
        )
    return cv_save_status_fragment("Save not completed", result.message, tone=result.tone)


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
        if result.success:
            return (
                Response("", status_code=200, headers={"HX-Refresh": "true"}),
                toast_fragment("CV profile saved", result.message),
            )
        title_text = "Save not completed"
        return cv_save_status_fragment(title_text, result.message, tone=result.tone)

    @app.post("/cv/section/core_skills/save")
    def cv_section_core_skills_save(data: str = "") -> Any:
        labels = json.loads(data) if data else []
        result = save_cv_section_core_skills(labels)
        return _section_save_response(result)

    @app.post("/cv/section/competencies/save")
    def cv_section_competencies_save(data: str = "") -> Any:
        labels = json.loads(data) if data else []
        result = save_cv_section_competencies(labels)
        return _section_save_response(result)

    @app.post("/cv/section/work_history/save")
    def cv_section_work_history_save(data: str = "") -> Any:
        items = json.loads(data) if data else []
        result = save_cv_section_work_history(items)
        return _section_save_response(result)

    @app.post("/cv/section/education/save")
    def cv_section_education_save(data: str = "") -> Any:
        items = json.loads(data) if data else []
        result = save_cv_section_education(items)
        return _section_save_response(result)

    @app.post("/cv/section/certifications/save")
    def cv_section_certifications_save(data: str = "") -> Any:
        items = json.loads(data) if data else []
        result = save_cv_section_certifications(items)
        return _section_save_response(result)

    @app.post("/cv/section/tools/save")
    def cv_section_tools_save(data: str = "") -> Any:
        items = json.loads(data) if data else []
        result = save_cv_section_tool_categories(items)
        return _section_save_response(result)

    @app.post("/cv/section/languages/save")
    def cv_section_languages_save(data: str = "") -> Any:
        items = json.loads(data) if data else []
        result = save_cv_section_languages(items)
        return _section_save_response(result)
