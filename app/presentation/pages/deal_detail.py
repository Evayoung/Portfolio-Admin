"""Deal detail page — thin dispatcher routing between Overview, Documents, and Edit views."""

from __future__ import annotations

from fasthtml.common import Div
from app.presentation.pages.deal_helpers import deal_generate_result_fragment
from app.presentation.pages.deal_overview import deal_overview_page
from app.presentation.pages.deal_documents import deal_documents_page
from app.presentation.pages.deal_edit import deal_edit_page


def deal_detail_page(*, deal_id: str = "", view: str = "documents") -> tuple:
    """Route requests to dedicated tab modules for clean separation of concerns."""
    if view == "documents":
        return deal_documents_page(deal_id=deal_id, view=view)
    if view == "edit":
        return deal_edit_page(deal_id=deal_id, view=view)
    if view == "overview":
        return deal_overview_page(deal_id=deal_id, view=view)
    return deal_documents_page(deal_id=deal_id, view="documents")
