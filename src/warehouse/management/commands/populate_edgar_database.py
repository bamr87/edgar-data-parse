"""
One-shot (or CI) population of Postgres after migrations: listed issuers, company rows,
reference data, and optionally SEC bulk ZIPs so EDGAR JSON is in-DB before live API use.

Usage (Docker / new database):

  python manage.py migrate
  python manage.py populate_edgar_database

With nightly bulk ZIPs (large download + CPU):

  python manage.py populate_edgar_database --bulk-zip --bulk-zip-limit 500

Environment: set USER_AGENT_EMAIL or DJANGO_SETTINGS SEC for SEC policy compliance.
"""

from __future__ import annotations

import logging
import os
from argparse import ArgumentParser

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def _user_agent_from_options(options: dict) -> str | None:
    ua = options.get("user_agent_email") or os.getenv("USER_AGENT_EMAIL")
    if ua is not None and isinstance(ua, str):
        ua = ua.strip() or None
    if ua is None:
        ua = getattr(settings, "SEC_USER_AGENT_EMAIL", None)
        if isinstance(ua, str):
            ua = ua.strip() or None
    return ua


class Command(BaseCommand):
    help = (
        "Populate Postgres with SEC directory data, warehouse Company rows, reference files, "
        "and optionally bulk ZIP ingestion. Run after migrate on new environments."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Do not run migrations (default runs migrate --noinput).",
        )
        parser.add_argument(
            "--skip-listed-issuers",
            action="store_true",
            help="Skip sync_listed_issuers (SEC company_tickers.json -> ListedIssuer).",
        )
        parser.add_argument(
            "--skip-companies",
            action="store_true",
            help="Skip bulk_load_edgar_companies (issuer rows -> Company).",
        )
        parser.add_argument(
            "--skip-reference",
            action="store_true",
            help="Skip sync_sic_reference and sync_accounting_reference.",
        )
        parser.add_argument(
            "--bulk-zip",
            action="store_true",
            help="Download and load submissions.zip + companyfacts.zip (heavy).",
        )
        parser.add_argument(
            "--bulk-zip-limit",
            type=int,
            default=None,
            metavar="N",
            help="Max CIK JSON files to process per ZIP (for dev/smoke tests).",
        )
        parser.add_argument(
            "--user-agent-email",
            type=str,
            default=None,
            help="Override SEC contact email for subcommands (default: USER_AGENT_EMAIL / settings).",
        )

    def handle(self, *args, **options):
        if not options["skip_migrate"]:
            self.stdout.write("Applying migrations…")
            call_command("migrate", interactive=False, verbosity=1)

        ua = _user_agent_from_options(options)
        if ua:
            os.environ["USER_AGENT_EMAIL"] = ua

        if not options["skip_listed_issuers"]:
            self.stdout.write("Syncing listed issuers (SEC company_tickers.json)…")
            call_command("sync_listed_issuers")

        if not options["skip_companies"]:
            self.stdout.write("Bulk loading Company rows from SEC directory…")
            call_command("bulk_load_edgar_companies")

        if not options["skip_reference"]:
            self.stdout.write("Refreshing SIC reference JSON…")
            call_command("sync_sic_reference")
            self.stdout.write("Building accounting reference map…")
            call_command("sync_accounting_reference")

        if options["bulk_zip"]:
            self.stdout.write(
                self.style.WARNING(
                    "Running bulk ZIP load (large download). This may take a long time."
                )
            )
            zip_kwargs: dict[str, object] = {"both": True}
            if options["bulk_zip_limit"] is not None:
                zip_kwargs["limit"] = options["bulk_zip_limit"]
            call_command("bulk_load_edgar_zip", **zip_kwargs)

        self.stdout.write(
            self.style.SUCCESS(
                "populate_edgar_database finished. "
                "API calls for submissions/facts now use Postgres (EdgarSecPayload) when present."
            )
        )
