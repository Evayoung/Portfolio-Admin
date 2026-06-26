"""Dashboard routes — overview, metrics partials."""

from __future__ import annotations

from typing import Any

try:
    from ..presentation.pages.dashboard import _metrics_ring, _workspace_status_partial, overview_page
except ImportError:
    from presentation.pages.dashboard import _metrics_ring, _workspace_status_partial, overview_page


def setup_dashboard_routes(app: Any) -> None:
    @app.get("/")
    def overview() -> Any:
        return overview_page()

    @app.get("/dashboard/metrics")
    def dashboard_metrics() -> Any:
        return _metrics_ring()

    @app.get("/dashboard/workspace-status")
    def dashboard_workspace_status() -> Any:
        return _workspace_status_partial()
