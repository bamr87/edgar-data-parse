"""Compute DerivedMetric rows from already-synced Facts (also the backfill path)."""

from django.core.management.base import BaseCommand, CommandError

from sec_edgar.cik import normalize_cik
from warehouse.models import Company
from warehouse.services.edgar.metrics import compute_derived_metrics


class Command(BaseCommand):
    help = "Compute/refresh DerivedMetric rows for one company or all companies."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--ticker", type=str)
        group.add_argument("--cik", type=str)
        group.add_argument("--all", action="store_true")

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

        total = 0
        for company in companies:
            written = compute_derived_metrics(company)
            total += written
            self.stdout.write(f"{company.cik} ({company.ticker or '-'}): {written} metrics")
        self.stdout.write(
            self.style.SUCCESS(f"Done. {total} metrics across {len(companies)} companies.")
        )
