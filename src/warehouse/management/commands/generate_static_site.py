"""Generate a static HTML site of company financials (copy/download friendly)."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from sec_edgar.cik import normalize_cik
from warehouse.models import Company
from warehouse.services.static_site import generate_site


class Command(BaseCommand):
    help = "Render a static, browsable site of company financials with copy/download data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", default=None, help="Output directory (default: <repo>/site)"
        )
        parser.add_argument("--ticker", action="append", help="Limit to ticker(s)")
        parser.add_argument("--cik", action="append", help="Limit to CIK(s)")
        parser.add_argument("--all", action="store_true", help="Include all companies")
        parser.add_argument("--limit", type=int, help="Max number of companies")

    def handle(self, *args, **options):
        qs = Company.objects.all().order_by("name")
        if options.get("ticker"):
            qs = qs.filter(ticker__in=[t.upper() for t in options["ticker"]])
        elif options.get("cik"):
            qs = qs.filter(cik__in=[normalize_cik(c) for c in options["cik"]])
        elif not options.get("all"):
            raise CommandError("Provide --ticker, --cik, or --all")
        if options.get("limit"):
            qs = qs[: options["limit"]]

        companies = list(qs)
        if not companies:
            raise CommandError("No matching companies found.")

        output = options.get("output") or str(Path(settings.BASE_DIR).parent / "site")
        summary = generate_site(companies, output)
        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {summary['pages']} page(s) -> {summary['output_dir']} "
                f"(as of {summary['generated_at']})"
            )
        )
        self.stdout.write(f"Open {summary['output_dir']}/index.html in a browser.")
