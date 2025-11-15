from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from warehouse.models import Company, Filing, Fact, Section, Table
from .serializers import (
    CompanySerializer,
    FilingSerializer,
    FactSerializer,
    SectionSerializer,
    TableSerializer,
)
from parse import parse_sec_htm
from fetch import cik_ticker, download_filing
import os


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('name')
    serializer_class = CompanySerializer
    filterset_fields = ['ticker', 'cik', 'industry']
    search_fields = ['name', 'ticker', 'cik']

    @action(detail=True, methods=['post'], url_path='suggest-schema')
    def suggest_schema(self, request, pk=None):
        company = self.get_object()
        # Simple heuristic-based suggestions (no external calls)
        base_fields = [
            'industry', 'management', 'headquarters', 'locations',
            'business_units', 'product_types', 'size'
        ]
        suggested = {
            'required': ['industry', 'headquarters'],
            'recommended': base_fields,
            'custom_candidates': [
                'esg_policies', 'risk_factors', 'major_customers', 'competitors',
                'supply_chain_regions', 'revenue_streams'
            ],
            'notes': 'Generated heuristically based on common SEC disclosures. Refine with AI later.'
        }
        return Response({'company': company.id, 'suggested_schema': suggested})


class FilingViewSet(viewsets.ModelViewSet):
    queryset = Filing.objects.all().order_by('-filing_date')
    serializer_class = FilingSerializer
    filterset_fields = ['form_type', 'company']

    @action(detail=False, methods=['post'], url_path='ingest-htm')
    def ingest_htm(self, request):
        url = request.data.get('url')
        ticker = request.data.get('ticker')
        cik = request.data.get('cik')
        if not url or (not ticker and not cik):
            return Response({'detail': 'url and ticker or cik are required'}, status=status.HTTP_400_BAD_REQUEST)

        if not cik and ticker:
            info = cik_ticker(ticker)
            cik = info['cik']
            name = info['name']
        else:
            name = ticker or cik

        company, _ = Company.objects.get_or_create(cik=cik, defaults={'ticker': ticker, 'name': name})
        filename = url.split('/')[-1]
        save_dir = os.path.join(os.getcwd(), 'data')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)
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

        return Response(FilingSerializer(filing).data, status=status.HTTP_201_CREATED)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    filterset_fields = ['filing', 'name']


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    filterset_fields = ['filing']


class FactViewSet(viewsets.ModelViewSet):
    queryset = Fact.objects.all()
    serializer_class = FactSerializer
    filterset_fields = ['company', 'taxonomy', 'concept']
    search_fields = ['concept']
