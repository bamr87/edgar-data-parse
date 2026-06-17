"""Load every bundle JSON in the bundles directory and sync their observations.

Convenience over running ``load_series_bundle`` + ``sync_series_bundle`` per file.
Resilient: a failing series is skipped (see sync_series_bundle), so one bad id never
aborts the run. Requires ``FRED_API_KEY`` for FRED series.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

BUNDLES_DIR = Path(__file__).resolve().parent.parent.parent / "bundles"


class Command(BaseCommand):
    help = "Load all bundle JSONs in the bundles dir and sync their observations."

    def add_arguments(self, parser):
        parser.add_argument("--dir", type=str, default=None, help="Bundles dir (default: app bundles/).")
        parser.add_argument("--no-sync", action="store_true", help="Register bundles only, skip FRED sync.")
        parser.add_argument("--delay", type=float, default=0.4, help="Seconds between series during sync.")
        parser.add_argument("--days-back", type=int, default=365 * 20, help="Observation window.")

    def handle(self, *args, **options):
        bundles_dir = Path(options["dir"]) if options["dir"] else BUNDLES_DIR
        files = sorted(bundles_dir.glob("*.json"))
        if not files:
            self.stdout.write(self.style.WARNING(f"No bundle JSONs found in {bundles_dir}"))
            return

        slugs: list[str] = []
        for f in files:
            call_command("load_series_bundle", file=str(f))
            try:
                slugs.append(json.loads(f.read_text(encoding="utf-8"))["slug"])
            except (json.JSONDecodeError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"  skipping sync for {f.name}: {e}"))

        if not options["no_sync"]:
            for slug in slugs:
                call_command(
                    "sync_series_bundle", slug=slug, delay=options["delay"], days_back=options["days_back"]
                )

        self.stdout.write(self.style.SUCCESS(f"Refreshed {len(files)} bundle(s): {', '.join(slugs)}"))
