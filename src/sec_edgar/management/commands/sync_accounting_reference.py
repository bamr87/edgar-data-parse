from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from sec_edgar.reference_data import clear_reference_cache
from sec_edgar.services.accounting_reference import sync_accounting_reference_to_disk


class Command(BaseCommand):
    help = (
        "Merge data/acct_facts.csv, acct_facts.json, and acct_facts_updated.json into "
        "data/reference/generated/us_gaap_account_map.json (later sources override per concept)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Directory containing acct_facts* (default: <project>/data).",
        )
        parser.add_argument(
            "--reference-dir",
            type=str,
            default=None,
            help="Reference root (default: <project>/data/reference).",
        )

    def handle(self, *args, **options):
        data_dir = (
            Path(options["data_dir"]).expanduser().resolve()
            if options["data_dir"]
            else Path(settings.BASE_DIR).parent / "data"
        )
        ref_dir = (
            Path(options["reference_dir"]).expanduser().resolve()
            if options["reference_dir"]
            else Path(settings.BASE_DIR).parent / "data" / "reference"
        )
        out = sync_accounting_reference_to_disk(data_dir=data_dir, reference_dir=ref_dir)
        clear_reference_cache()
        self.stdout.write(self.style.SUCCESS(f"Wrote {out}"))
