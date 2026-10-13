"""CLI entrypoint for syncing NeoPortfolio content into Supabase."""

from __future__ import annotations

import argparse
from pprint import pprint
import sys

from app.infrastructure.content_sync import preview_content_sync


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview the bundled NeoPortfolio seed content. Database writes are currently disabled."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Request a database write. Currently refused because the legacy sync replaces editorial content.",
    )
    args = parser.parse_args(argv)

    if args.apply:
        print(
            "Refusing to apply seed content: the current sync replaces hand-managed records. "
            "Use the default preview until a non-destructive, idempotent importer is implemented.",
            file=sys.stderr,
        )
        return 2

    result = preview_content_sync()
    print("Seed content preview (read-only; no Supabase connection or writes):")
    pprint(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
