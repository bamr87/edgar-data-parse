import logging

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from sec_edgar.services.ingest_htm import ingest_htm_filing

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ingest an HTM filing into the warehouse (shared service with API)."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="HTM filing URL")
        parser.add_argument("--ticker", required=False, help="Company ticker")
        parser.add_argument("--cik", required=False, help="Company CIK")

    def handle(self, *args, **options):
        with ingest_job_context(logger, "ingest_htm") as fields:
            filing = ingest_htm_filing(
                url=options["url"],
                ticker=options.get("ticker"),
                cik=options.get("cik"),
            )
            fields["accession_number"] = filing.accession_number
            fields["company_cik"] = filing.company.cik
            self.stdout.write(
                self.style.SUCCESS(
                    f"Ingested filing {filing.accession_number} for {filing.company}"
                )
            )
