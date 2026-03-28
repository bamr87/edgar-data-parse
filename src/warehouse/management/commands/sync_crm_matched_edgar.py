import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from warehouse.services.crm_edgar_sync import sync_crm_matched_edgar

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "For CRM rows with exact SEC title match (sec_cik), upsert Company and sync "
        "submissions + optional company facts. Uses delays between requests for SEC rate limits."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delay",
            type=float,
            default=float(os.getenv("SEC_SYNC_DELAY_SECONDS", "0.25")),
            help="Seconds to sleep after submissions before next company (default 0.25 or env).",
        )
        parser.add_argument(
            "--delay-after-facts",
            type=float,
            default=float(os.getenv("SEC_SYNC_DELAY_AFTER_FACTS_SECONDS", "0.35")),
            help="Extra pause after downloading company facts JSON (large payload).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Process at most N matched CRM rows (for testing).",
        )
        parser.add_argument(
            "--skip-facts",
            action="store_true",
            help="Only sync submissions index (skip companyfacts API).",
        )
        parser.add_argument(
            "--start-after-pk",
            type=int,
            default=0,
            help="Resume: only CRM rows with pk greater than this value.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Log which rows would sync without calling SEC or writing beyond logs.",
        )

    def handle(self, *args, **options):
        ua = getattr(settings, "SEC_USER_AGENT_EMAIL", None) or None
        if isinstance(ua, str) and not ua.strip():
            ua = None

        with ingest_job_context(logger, "sync_crm_matched_edgar") as fields:
            stats = sync_crm_matched_edgar(
                user_agent_email=ua,
                delay_seconds=options["delay"],
                delay_after_facts_seconds=options["delay_after_facts"],
                limit=options["limit"],
                skip_facts=options["skip_facts"],
                start_after_pk=options["start_after_pk"],
                dry_run=options["dry_run"],
            )
            fields["processed"] = stats["processed"]
            fields["error_count"] = stats["error_count"]
            self.stdout.write(self.style.SUCCESS(str(stats)))
            if stats["errors"]:
                for line in stats["errors"][:10]:
                    self.stderr.write(line)
