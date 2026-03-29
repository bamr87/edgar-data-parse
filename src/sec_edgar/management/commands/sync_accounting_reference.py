from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from sec_edgar.reference_data import clear_reference_cache
from sec_edgar.services.accounting_reference import sync_accounting_reference_to_disk


class Command(BaseCommand):
    help = (
        "Merge data/reference/sources/accounting/acct_facts.csv and acct_facts_overlay.json "
        "into data/reference/generated/us_gaap_account_map.json (overlay wins per concept)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--accounting-sources-dir",
            type=str,
            default=None,
            help=(
                "Directory with acct_facts.csv and acct_facts_overlay.json "
                "(default: <project>/data/reference/sources/accounting)."
            ),
        )
        parser.add_argument(
            "--reference-dir",
            type=str,
            default=None,
            help="Reference root (default: <project>/data/reference).",
        )

    def handle(self, *args, **options):
        ref_dir = (
            Path(options["reference_dir"]).expanduser().resolve()
            if options["reference_dir"]
            else Path(settings.BASE_DIR).parent / "data" / "reference"
        )
        sources_dir = (
            Path(options["accounting_sources_dir"]).expanduser().resolve()
            if options["accounting_sources_dir"]
            else ref_dir / "sources" / "accounting"
        )
        out = sync_accounting_reference_to_disk(
            accounting_sources_dir=sources_dir,
            reference_dir=ref_dir,
        )
        clear_reference_cache()
        self.stdout.write(self.style.SUCCESS(f"Wrote {out}"))
