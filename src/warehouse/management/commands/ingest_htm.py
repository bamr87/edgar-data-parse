from django.core.management.base import BaseCommand
from warehouse.models import Company, Filing, Section, Table
from parse import parse_sec_htm
from fetch import cik_ticker, download_filing
import os

class Command(BaseCommand):
    help = 'Ingest an HTM filing into the warehouse models'

    def add_arguments(self, parser):
        parser.add_argument('--url', required=True, help='HTM filing URL')
        parser.add_argument('--ticker', required=False, help='Company ticker')
        parser.add_argument('--cik', required=False, help='Company CIK')

    def handle(self, *args, **options):
        url = options['url']
        ticker = options.get('ticker')
        cik = options.get('cik')

        if not cik and ticker:
            data = cik_ticker(ticker)
            cik = data['cik']
            company_name = data['name']
        elif cik:
            company_name = ticker or cik
        else:
            self.stderr.write('Provide either --ticker or --cik')
            return

        company, _ = Company.objects.get_or_create(cik=cik, defaults={'ticker': ticker, 'name': company_name})
        filename = url.split('/')[-1]
        save_path = os.path.join('data', filename)
        os.makedirs('data', exist_ok=True)
        download_filing(url, save_path)
        parsed = parse_sec_htm(save_path)

        filing = Filing.objects.create(
            company=company,
            accession_number=filename.replace('.htm', ''),
            form_type='HTM',
            url=url,
            local_path=save_path,
            metadata={'source': 'HTM-ingest'}
        )

        for name, content in parsed.get('sections', {}).items():
            Section.objects.create(filing=filing, name=name, content=content)

        for table in parsed.get('tables', []):
            Table.objects.create(filing=filing, data=table)

        self.stdout.write(self.style.SUCCESS(f'Ingested filing {filename} for company {company}'))
