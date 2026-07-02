"""Submission routes — workspace page and save handler."""

from __future__ import annotations

from typing import Any

from starlette.responses import Response

try:
    from ..infrastructure.submission_repository import update_submission
    from ..presentation.page_helpers import toast_fragment
    from ..presentation.pages.submissions import submission_save_status_fragment, submissions_workspace_page
except ImportError:
    from infrastructure.submission_repository import update_submission
    from presentation.page_helpers import toast_fragment
    from presentation.pages.submissions import submission_save_status_fragment, submissions_workspace_page


def setup_submission_routes(app: Any) -> None:
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
        if result.success:
            return (
                Response("", status_code=200, headers={"HX-Refresh": "true"}),
                toast_fragment("Submission updated", result.message),
            )
        title_text = "Update not completed"
        return submission_save_status_fragment(title_text, result.message, tone=result.tone)
