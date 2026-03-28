"""Download SEC.gov SIC code list HTML and write data/reference/sic_codes.json."""

from __future__ import annotations

import json
import logging
from argparse import ArgumentParser
from pathlib import Path

from django.core.management.base import BaseCommand

from sec_edgar.client import SecEdgarClient
from sec_edgar.services.sic_reference import (
    SIC_CODE_LIST_URL,
    build_bundle_from_rows,
    default_sic_reference_path,
    parse_sic_table_html,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Fetch the SEC SIC code list page, parse the HTML table, and write sic_codes.json "
        "(default: <project>/data/reference/sic_codes.json). Requires a valid User-Agent contact."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Output path (default: EDGAR_DATA_DIR/reference/sic_codes.json)",
        )
        parser.add_argument(
            "--url",
            type=str,
            default=SIC_CODE_LIST_URL,
            help="Override SEC page URL (default: official SIC list page)",
        )

    def handle(self, *args, **options):
        out = Path(options["output"]).expanduser().resolve() if options["output"] else default_sic_reference_path()
        url = str(options["url"])
        client = SecEdgarClient()
        self.stdout.write(f"GET {url}")
        html = client.get_text(url)
        rows = parse_sic_table_html(html)
        bundle = build_bundle_from_rows(rows, source_url=url)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} SIC codes -> {out}"))
