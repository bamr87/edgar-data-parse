import json
import logging
from pathlib import Path

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from public_data.models import ExternalSeries, SeriesBundle, SeriesBundleItem

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load a JSON bundle definition into SeriesBundle + ExternalSeries registry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Path to bundle JSON (default: macro bundle in app)",
        )

    def handle(self, *args, **options):
        with ingest_job_context(logger, "load_series_bundle") as fields:
            if options["file"]:
                path = Path(options["file"])
            else:
                path = (
                    Path(__file__).resolve().parent.parent.parent
                    / "bundles"
                    / "macro.json"
                )
            data = json.loads(path.read_text(encoding="utf-8"))
            bundle, _ = SeriesBundle.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": data.get("description", ""),
                },
            )
            SeriesBundleItem.objects.filter(bundle=bundle).delete()
            order = 0
            for row in data.get("series", []):
                prov = row["provider"]
                sid = row["id"]
                es, _ = ExternalSeries.objects.get_or_create(
                    provider=prov,
                    external_id=sid,
                    defaults={"title": sid, "metadata": {"note": row.get("note", "")}},
                )
                SeriesBundleItem.objects.create(
                    bundle=bundle, series=es, sort_order=order
                )
                order += 1
            fields["bundle_slug"] = bundle.slug
            fields["series_count"] = order
            self.stdout.write(
                self.style.SUCCESS(f"Loaded bundle {bundle.slug} ({order} series)")
            )
