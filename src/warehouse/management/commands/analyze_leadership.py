"""Run the optional LLM narrative analysis of company leadership.

Gated behind ``ENABLE_AI_ANALYSIS`` (default off). When disabled, prints a clear
hint instead of calling any model. Output is strictly grounded in the company's
ingested SEC filing text — see docs/leadership-methodology.md.
"""

from django.core.management.base import BaseCommand, CommandError

from sec_edgar.cik import normalize_cik
from warehouse.models import Company
from warehouse.services.leadership_ai import analyze_company_leadership


class Command(BaseCommand):
    help = "LLM analysis of leadership initiatives/quotes from SEC filing text (gated)."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--ticker", type=str)
        group.add_argument("--cik", type=str)
        group.add_argument("--all", action="store_true")
        parser.add_argument(
            "--no-persist", action="store_true", help="Do not store the result."
        )

    def handle(self, *args, **options):
        if options.get("cik"):
            qs = Company.objects.filter(cik=normalize_cik(options["cik"]))
        elif options.get("ticker"):
            qs = Company.objects.filter(ticker=options["ticker"].upper())
        else:
            qs = Company.objects.all()
        companies = list(qs)
        if not companies:
            raise CommandError("No matching companies found.")

        for company in companies:
            result = analyze_company_leadership(
                company, persist=not options["no_persist"]
            )
            if not result["enabled"]:
                self.stdout.write(
                    f"{company.cik} {company.ticker or '-'}: AI analysis disabled "
                    "(set ENABLE_AI_ANALYSIS=true and install requirements-ai.txt)."
                )
                continue
            if result["error"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"{company.cik} {company.ticker or '-'}: {result['error']}"
                    )
                )
                continue
            self.stdout.write(
                f"{company.cik} {company.ticker or '-'}: "
                f"{len(result['initiatives'])} initiative(s), {len(result['quotes'])} "
                f"quote(s) from {len(result['used_sources'])} source passage(s)."
            )
