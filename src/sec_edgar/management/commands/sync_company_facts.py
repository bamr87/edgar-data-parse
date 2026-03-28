import logging

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from sec_edgar.services.company_facts import sync_company_facts_by_ticker

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch SEC companyfacts JSON and load into warehouse.Fact for a ticker."

    def add_arguments(self, parser):
        parser.add_argument("--ticker", required=True, type=str)

    def handle(self, *args, **options):
        with ingest_job_context(logger, "sync_company_facts") as fields:
            company, n = sync_company_facts_by_ticker(options["ticker"])
            fields["ticker"] = options["ticker"].upper()
            fields["facts_loaded"] = n
            self.stdout.write(
                self.style.SUCCESS(f"Loaded {n} facts for {company.ticker} ({company.cik})")
            )
