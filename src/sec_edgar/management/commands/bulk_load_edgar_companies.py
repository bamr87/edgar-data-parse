import logging

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from sec_edgar.services.bulk_company_tickers import sync_companies_from_sec_company_tickers
from sec_edgar.services.company_tickers_catalog import iter_flat_company_records
from warehouse.models import Company

logger = logging.getLogger(__name__)

FETCH_BATCH = 800


class Command(BaseCommand):
    help = (
        "Bulk load basic company rows (CIK, ticker, name) from SEC company_tickers.json "
        "into the warehouse."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Overwrite name/ticker on existing Company rows when SEC data differs.",
        )
        parser.add_argument(
            "--refresh-sec-json",
            action="store_true",
            help="Drop cached ticker JSON and refetch from www.sec.gov before loading.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch SEC list and report how many rows would be inserted (no writes).",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        ua = getattr(settings, "SEC_USER_AGENT_EMAIL", None) or None
        if isinstance(ua, str) and not ua.strip():
            ua = None

        update_existing = options["update_existing"]
        refresh = options["refresh_sec_json"]
        dry = options["dry_run"]

        with ingest_job_context(logger, "bulk_load_edgar_companies") as fields:
            if dry:
                recs = iter_flat_company_records(
                    user_agent_email=ua,
                    force_refresh=refresh,
                )
                ciks = list({r["cik"] for r in recs})
                existing_total = 0
                for i in range(0, len(ciks), FETCH_BATCH):
                    existing_total += Company.objects.filter(
                        cik__in=ciks[i : i + FETCH_BATCH]
                    ).count()
                would_insert = len(ciks) - existing_total
                self.stdout.write(
                    f"Dry run: SEC issuers={len(ciks)} already in warehouse={existing_total} "
                    f"would attempt insert={would_insert}"
                )
                fields["dry_run"] = True
                fields["source_issuers"] = len(ciks)
                return

            stats = sync_companies_from_sec_company_tickers(
                user_agent_email=ua,
                update_existing=update_existing,
                refresh_sec_json=refresh,
            )
            fields.update(
                {
                    "source_issuers": stats["source_issuers"],
                    "insert_attempted": stats["insert_attempted"],
                    "companies_updated": stats["companies_updated"],
                    "warehouse_already_had": stats["warehouse_already_had"],
                }
            )
            self.stdout.write(self.style.SUCCESS(str(stats)))
