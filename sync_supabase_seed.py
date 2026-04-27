"""CLI entrypoint for syncing NeoPortfolio content into Supabase."""

from __future__ import annotations

from pprint import pprint

from app.infrastructure.content_sync import sync_all_content


if __name__ == "__main__":
    result = sync_all_content()
    print("Supabase content sync completed.")
    pprint(result)
