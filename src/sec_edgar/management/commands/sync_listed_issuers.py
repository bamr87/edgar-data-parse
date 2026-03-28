import logging

from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from warehouse.services.edgar.listed_issuers import sync_listed_issuers_from_remote

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Fetch SEC company_tickers.json and upsert all rows into warehouse.ListedIssuer "
        "(DB-first issuer directory)."
    )

    def handle(self, *args, **options):
        from django.conf import settings

        ua = getattr(settings, "SEC_USER_AGENT_EMAIL", None) or None
        if isinstance(ua, str) and not ua.strip():
            ua = None

        with ingest_job_context(logger, "sync_listed_issuers") as fields:
            stats = sync_listed_issuers_from_remote(user_agent_email=ua)
            fields.update(stats)
            self.stdout.write(self.style.SUCCESS(str(stats)))
