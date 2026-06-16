"""Extract company leadership (officers/directors) from SEC Forms 3/4/5."""

from django.core.management.base import BaseCommand, CommandError

from sec_edgar.cik import normalize_cik
from warehouse.models import Company
from warehouse.services.leadership import sync_leadership


class Command(BaseCommand):
    help = "Extract leadership positions from a company's recent SEC ownership filings."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--ticker", type=str)
        group.add_argument("--cik", type=str)
        parser.add_argument("--limit", type=int, default=25, help="Max ownership filings to read")

    def handle(self, *args, **options):
        if options.get("cik"):
            company = Company.objects.filter(cik=normalize_cik(options["cik"])).first()
        else:
            company = Company.objects.filter(ticker=options["ticker"].upper()).first()
        if not company:
            raise CommandError("Company not found — run sync_submissions first.")
        result = sync_leadership(company, limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{company.cik}: read {result['filings_processed']} filings -> "
                f"{result['people']} people, {result['positions']} positions"
            )
        )
