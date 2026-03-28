import logging

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pull SEC submissions index for a company (CIK) into Filing rows."

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--ticker", type=str)
        g.add_argument("--cik", type=str)
        parser.add_argument(
            "--force-refresh",
            action="store_true",
            help="Ignore cached EdgarSecPayload and refetch from SEC.",
        )

    def handle(self, *args, **options):
        from sec_edgar.adapters.direct import DirectEdgarAdapter

        with ingest_job_context(logger, "sync_submissions") as fields:
            ad = DirectEdgarAdapter()
            if options.get("ticker"):
                info = ad.cik_for_ticker(options["ticker"])
                cik = info["cik"]
                name = info["name"]
                ticker = options["ticker"].upper()
            else:
                cik = str(options["cik"]).zfill(10)
                name = cik
                ticker = None

            company, _ = Company.objects.get_or_create(
                cik=cik, defaults={"ticker": ticker, "name": name}
            )
            n = sync_submissions_for_company(
                company, force_refresh=options["force_refresh"]
            )
            fields["cik"] = company.cik
            fields["filings_indexed"] = n
            self.stdout.write(self.style.SUCCESS(f"Processed {n} recent filings for {company}"))
