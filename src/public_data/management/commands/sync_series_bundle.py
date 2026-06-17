import logging
import time

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from public_data.models import SeriesBundle
from public_data.services.sync import ensure_fred_series, sync_series_incremental

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch observations for all series in a named bundle (requires FRED_API_KEY for FRED)."

    def add_arguments(self, parser):
        parser.add_argument("--slug", type=str, default="macro")
        parser.add_argument(
            "--days-back",
            type=int,
            default=365 * 15,
            help="Observation window start (days back from today)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.4,
            help="Seconds between series (FRED allows 120 req/min).",
        )

    def handle(self, *args, **options):
        with ingest_job_context(logger, "sync_series_bundle") as fields:
            slug = options["slug"]
            bundle = SeriesBundle.objects.get(slug=slug)
            total = ok = failed = 0
            delay = max(0.0, options["delay"])
            for item in bundle.items.select_related("series").all():
                s = item.series
                # One bad series id must not abort the whole bundle.
                try:
                    if s.provider == "fred":
                        ensure_fred_series(s.external_id)
                        s.refresh_from_db()
                    n = sync_series_incremental(s, days_back=options["days_back"])
                    total += n
                    ok += 1
                    self.stdout.write(f"  {s.external_id}: {n} observations")
                except Exception as e:  # noqa: BLE001 - record + continue
                    failed += 1
                    self.stdout.write(self.style.WARNING(f"  {s.external_id}: FAILED ({str(e)[:120]})"))
                if delay:
                    time.sleep(delay)
            fields["bundle_slug"] = slug
            fields["observations_upserted"] = total
            fields["series_ok"] = ok
            fields["series_failed"] = failed
            self.stdout.write(
                self.style.SUCCESS(
                    f"Synced bundle {slug}: {ok} series ok, {failed} failed, ~{total} rows."
                )
            )
