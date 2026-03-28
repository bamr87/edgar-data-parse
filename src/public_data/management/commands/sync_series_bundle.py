import logging

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

    def handle(self, *args, **options):
        with ingest_job_context(logger, "sync_series_bundle") as fields:
            slug = options["slug"]
            bundle = SeriesBundle.objects.get(slug=slug)
            total = 0
            for item in bundle.items.select_related("series").all():
                s = item.series
                if s.provider == "fred":
                    ensure_fred_series(s.external_id)
                    s.refresh_from_db()
                n = sync_series_incremental(s, days_back=options["days_back"])
                total += n
                self.stdout.write(f"  {s}: {n} observations")
            fields["bundle_slug"] = slug
            fields["observations_upserted"] = total
            self.stdout.write(
                self.style.SUCCESS(f"Synced bundle {slug}, total rows upserted ~{total}")
            )
