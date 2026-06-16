"""Compute the transparent stakeholder-orientation assessment for a company."""

from django.core.management.base import BaseCommand, CommandError

from sec_edgar.cik import normalize_cik
from warehouse.models import Company
from warehouse.services.stakeholder import compute_stakeholder_assessment


class Command(BaseCommand):
    help = "Compute the stakeholder-orientation (people-vs-profits) index from XBRL facts."

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
        for company in companies:
            r = compute_stakeholder_assessment(company)
            self.stdout.write(
                f"{company.cik} {company.ticker or '-'}: index={r['orientation_index']} "
                f"({r['label']}) from {len(r['signals'])} signal(s)"
            )
