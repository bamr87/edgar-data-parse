import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from config.job_logging import ingest_job_context
from warehouse.services.crm_import import load_crm_json_path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Load data/local/companies-clean.json (or path) into CrmCompanyRecord staging rows. "
        "Does not call SEC."
    )

    def add_arguments(self, parser):
        default = Path(settings.BASE_DIR).parent / "data" / "local" / "companies-clean.json"
        parser.add_argument(
            "json_path",
            nargs="?",
            type=str,
            default=str(default),
            help=f"Path to CRM JSON array (default: {default})",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all CrmCompanyRecord rows before loading.",
        )

    def handle(self, *args, **options):
        path = Path(options["json_path"]).expanduser().resolve()
        if not path.is_file():
            self.stderr.write(self.style.ERROR(f"File not found: {path}"))
            return

        with ingest_job_context(logger, "load_crm_companies_json") as fields:
            stats = load_crm_json_path(path, clear_existing=options["clear"])
            fields.update(stats)
            self.stdout.write(self.style.SUCCESS(str(stats)))
