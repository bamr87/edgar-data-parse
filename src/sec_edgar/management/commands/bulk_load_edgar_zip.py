import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from sec_edgar.services.bulk_zip_load import (
    URL_COMPANYFACTS_ZIP,
    URL_SUBMISSIONS_ZIP,
    run_bulk_load,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Load SEC nightly bulk ZIPs (submissions.zip, companyfacts.zip) into warehouse "
        "Filing and Fact rows. Submissions are applied before facts when both are selected."
    )

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument(
            "--submissions-only",
            action="store_true",
            help="Only load submissions.zip.",
        )
        g.add_argument(
            "--facts-only",
            action="store_true",
            help="Only load companyfacts.zip.",
        )
        g.add_argument(
            "--both",
            action="store_true",
            help="Load submissions.zip then companyfacts.zip.",
        )
        parser.add_argument(
            "--submissions-zip",
            type=str,
            default=None,
            help="Local path to submissions.zip (skip download).",
        )
        parser.add_argument(
            "--facts-zip",
            type=str,
            default=None,
            help="Local path to companyfacts.zip (skip download).",
        )
        parser.add_argument(
            "--submissions-url",
            type=str,
            default=URL_SUBMISSIONS_ZIP,
            help="Override SEC submissions bulk ZIP URL.",
        )
        parser.add_argument(
            "--facts-url",
            type=str,
            default=URL_COMPANYFACTS_ZIP,
            help="Override SEC companyfacts bulk ZIP URL.",
        )
        parser.add_argument(
            "--cache-dir",
            type=str,
            default=None,
            help="Directory for downloaded ZIPs (default: temp/edgar_bulk_zips).",
        )
        parser.add_argument(
            "--only-existing-companies",
            action="store_true",
            help="Only load CIKs that already exist in warehouse.Company.",
        )
        parser.add_argument(
            "--cik",
            action="append",
            default=[],
            metavar="CIK",
            help="Restrict to this 10-digit CIK (repeatable).",
        )
        parser.add_argument(
            "--start-after-cik",
            type=str,
            default=None,
            help="Skip CIKs lexically <= this value (resume).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after this many CIKs processed per selected ZIP phase.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Iterate and count matches without loading JSON or writing DB.",
        )
        parser.add_argument(
            "--delay-seconds",
            type=float,
            default=0.0,
            help="Sleep this long after each CIK (reduce DB load).",
        )

    def handle(self, *args, **options):
        ua = getattr(settings, "SEC_USER_AGENT_EMAIL", None) or None
        if isinstance(ua, str) and not ua.strip():
            ua = None

        load_submissions = options["both"] or options["submissions_only"]
        load_facts = options["both"] or options["facts_only"]

        cik_allowlist = None
        raw_ciks = options["cik"] or []
        if raw_ciks:
            cik_allowlist = {c.zfill(10) for c in raw_ciks}

        cache_dir = Path(options["cache_dir"]) if options["cache_dir"] else None
        submissions_zip = (
            Path(options["submissions_zip"]) if options["submissions_zip"] else None
        )
        facts_zip = Path(options["facts_zip"]) if options["facts_zip"] else None

        with ingest_job_context(logger, "bulk_load_edgar_zip") as fields:
            stats = run_bulk_load(
                load_submissions=load_submissions,
                load_facts=load_facts,
                submissions_zip=submissions_zip,
                facts_zip=facts_zip,
                submissions_url=options["submissions_url"],
                facts_url=options["facts_url"],
                cache_dir=cache_dir,
                user_agent_email=ua,
                only_existing_companies=options["only_existing_companies"],
                cik_allowlist=cik_allowlist,
                start_after_cik=options["start_after_cik"],
                limit=options["limit"],
                dry_run=options["dry_run"],
                delay_seconds=options["delay_seconds"],
            )
            fields["result_json"] = json.dumps(stats, default=str)[:2000]
            self.stdout.write(json.dumps(stats, indent=2, default=str))
            self.stdout.write(self.style.SUCCESS("bulk_load_edgar_zip finished"))
