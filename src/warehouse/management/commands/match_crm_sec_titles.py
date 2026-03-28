import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from warehouse.services.crm_match_apply import match_crm_records_to_sec

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Match CrmCompanyRecord names to SEC company_tickers.json titles (exact normalized). "
        "Sets sec_cik / sec_ticker where unambiguous."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear prior match fields on all CRM rows before matching.",
        )

    def handle(self, *args, **options):
        ua = getattr(settings, "SEC_USER_AGENT_EMAIL", None) or None
        if isinstance(ua, str) and not ua.strip():
            ua = None

        with ingest_job_context(logger, "match_crm_sec_titles") as fields:
            stats = match_crm_records_to_sec(
                user_agent_email=ua,
                reset=options["reset"],
            )
            fields.update(stats)
            self.stdout.write(self.style.SUCCESS(str(stats)))
