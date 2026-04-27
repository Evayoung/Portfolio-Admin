"""Entrypoint for the Neo Admin dashboard."""

from fasthtml.common import serve

from app.config import settings
from app.main import app

__all__ = ["app"]


if __name__ == "__main__":
    serve(port=settings.port)
