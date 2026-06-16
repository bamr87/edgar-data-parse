"""Ingest a full SEC submission (.txt) into Filing + FilingDocument rows."""

import logging

from django.core.management.base import BaseCommand, CommandError

from config.job_logging import ingest_job_context
from sec_edgar.services.ingest_submission import ingest_submission

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Download a full SEC submission .txt and decompose it into FilingDocument rows."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="URL of the full submission .txt")
        parser.add_argument("--ticker", type=str)
        parser.add_argument("--cik", type=str)
        parser.add_argument(
            "--no-extract",
            action="store_true",
            help="Skip text extraction (store raw documents only).",
        )

    def handle(self, *args, **options):
        if not options.get("ticker") and not options.get("cik"):
            raise CommandError("Provide --ticker or --cik")
        with ingest_job_context(logger, "ingest_submission"):
            filing, n = ingest_submission(
                url=options["url"],
                ticker=options.get("ticker"),
                cik=options.get("cik"),
                extract=not options.get("no_extract"),
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Ingested {n} documents for filing {filing.accession_number} (id={filing.id})."
            )
        )
