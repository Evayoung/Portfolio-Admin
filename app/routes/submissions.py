"""Submission routes — workspace list, dedicated detail view, and save handler."""

from __future__ import annotations

from typing import Any

from starlette.responses import Response

try:
    from ..infrastructure.submission_repository import delete_submission, get_submission, get_submission_workspace_summary, list_submissions, update_submission
    from ..presentation.page_helpers import toast_fragment
    from ..presentation.pages.submissions import _submissions_list_panel, submission_detail_page, submission_save_status_fragment, submissions_workspace_page
except ImportError:
    from infrastructure.submission_repository import delete_submission, get_submission, get_submission_workspace_summary, list_submissions, update_submission
    from presentation.page_helpers import toast_fragment
    from presentation.pages.submissions import _submissions_list_panel, submission_detail_page, submission_save_status_fragment, submissions_workspace_page


def setup_submission_routes(app: Any) -> None:
    @app.get("/submissions")
    def submissions(kind: str = "all", status: str = "all", search: str = "") -> Any:
        return submissions_workspace_page(kind=kind, status=status, search=search)

    @app.get("/submissions/detail")
    def submission_detail(entry_id: str = "", kind: str = "all", status: str = "all", search: str = "") -> Any:
        return submission_detail_page(entry_id=entry_id, kind=kind, status=status, search=search)

    @app.get("/submissions/search")
    def submissions_search(kind: str = "all", status: str = "all", search: str = "") -> Any:
        """Return just the submissions list panel for HTMX live search."""
        items = list_submissions(kind=kind, status=status, search=search)
        summary = get_submission_workspace_summary()
        return _submissions_list_panel(items, kind=kind, status=status, search=search, summary=summary)

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

    @app.delete("/submissions/delete")
    def submissions_delete(
        entry_id: str = "",
        kind: str = "",
        current_kind: str = "all",
        current_status: str = "all",
        current_search: str = "",
    ) -> Any:
        result = delete_submission(entry_id=entry_id, kind=kind)
        items = list_submissions(kind=current_kind, status=current_status, search=current_search)
        summary = get_submission_workspace_summary()
        panel = _submissions_list_panel(items, kind=current_kind, status=current_status, search=current_search, summary=summary)
        toast = toast_fragment("Submission Record Deleted" if result.success else "Deletion Failed", result.message, variant="success" if result.success else "danger")
        return (panel, toast)


