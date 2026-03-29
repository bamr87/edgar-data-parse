import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from sec_edgar.client import SecEdgarClient
from sec_edgar.reference_data import clear_reference_cache
from sec_edgar.services.accounting_reference import sync_accounting_reference_to_disk
from sec_edgar.services.reference_from_edgar import generate_reference_bundle

logger = logging.getLogger(__name__)

# Diverse large filers to widen taxonomy union in companyfacts (add --cik / --ticker as needed).
_DEFAULT_SAMPLE_CIK = ["0000320193", "0000789019"]


class Command(BaseCommand):
    help = (
        "Regenerate data/reference/*.json from SEC EDGAR APIs (companyfacts, submissions, companyconcept). "
        "Requires a valid User-Agent contact (USER_AGENT_EMAIL). "
        "Preserves hand-authored schema text; merges live observations and concept labels."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cik",
            action="append",
            dest="ciks",
            default=[],
            metavar="CIK",
            help="CIK for companyfacts sampling (repeatable). Union drives taxonomies.json and observed fact keys.",
        )
        parser.add_argument(
            "--ticker",
            action="append",
            dest="tickers",
            default=[],
            metavar="TICKER",
            help="Resolve CIK via company_tickers.json (repeatable).",
        )
        parser.add_argument(
            "--metadata-cik",
            type=str,
            default=None,
            metavar="CIK",
            help="CIK for submissions root keys + companyconcept metadata (default: first sample CIK).",
        )
        parser.add_argument(
            "--reference-dir",
            type=str,
            default=None,
            help="Output directory (default: <project>/data/reference).",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.12,
            help="Seconds between SEC calls (default: 0.12).",
        )
        parser.add_argument(
            "--with-accounting",
            action="store_true",
            help=(
                "After SEC refresh, run accounting merge "
                "(reference/sources/accounting → generated/us_gaap_account_map.json)."
            ),
        )

    def handle(self, *args, **options):
        ref = (
            Path(options["reference_dir"]).expanduser().resolve()
            if options["reference_dir"]
            else (Path(settings.BASE_DIR).parent / "data" / "reference")
        )
        if not ref.is_dir():
            self.stderr.write(self.style.ERROR(f"Reference directory not found: {ref}"))
            return

        client = SecEdgarClient()
        ciks: list[str] = [str(c).strip() for c in (options["ciks"] or []) if str(c).strip()]
        for t in options["tickers"] or []:
            info = client.cik_for_ticker(str(t).strip())
            ciks.append(info["cik"])

        if not ciks:
            ciks = list(_DEFAULT_SAMPLE_CIK)

        meta_cik = options["metadata_cik"] or ciks[0]
        delay = float(options["delay"])

        self.stdout.write(
            f"Generating reference under {ref} (sample_ciks={ciks}, metadata_cik={meta_cik}, delay={delay}s)"
        )
        try:
            generate_reference_bundle(
                ref,
                client,
                sample_ciks=ciks,
                metadata_cik=meta_cik,
                delay_s=delay,
            )
        except Exception as e:
            logger.exception("generate_edgar_reference failed")
            self.stderr.write(self.style.ERROR(str(e)))
            raise
        self.stdout.write(self.style.SUCCESS("Updated taxonomies.json, edgar_api_schema.json, financial_model.json"))

        if options.get("with_accounting"):
            out = sync_accounting_reference_to_disk(reference_dir=ref)
            clear_reference_cache()
            self.stdout.write(self.style.SUCCESS(f"Accounting map: {out}"))
