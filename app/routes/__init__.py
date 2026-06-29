"""Route package — register all area route modules."""

from __future__ import annotations

from typing import Any


def setup_routes(app: Any) -> None:
    """Register all area route handlers on the FastHTML app."""
    # Order matters: auth first, then dashboard (root "/"), then content areas
    from .auth import setup_auth_routes
    from .dashboard import setup_dashboard_routes
    from .projects import setup_project_routes
    from .blog import setup_blog_routes
    from .cv import setup_cv_routes
    from .submissions import setup_submission_routes
    from .deals import setup_deal_routes
    from .media import setup_media_routes
    from .documents import setup_document_routes
    from .settings import setup_settings_routes
    from .ai_assistant import setup_ai_assistant_routes

    setup_auth_routes(app)
    setup_dashboard_routes(app)
    setup_project_routes(app)
    setup_blog_routes(app)
    setup_cv_routes(app)
    setup_submission_routes(app)
    setup_deal_routes(app)
    setup_media_routes(app)
    setup_document_routes(app)
    setup_settings_routes(app)
    setup_ai_assistant_routes(app)
