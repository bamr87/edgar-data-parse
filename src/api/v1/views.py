import logging

from django.db import connection
from django.db.models import Count
from django.db.models.functions import TruncYear
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from public_data.models import ExternalSeries, SeriesBundle, SeriesObservation
from sec_edgar.services.company_tickers_catalog import search_company_tickers
from sec_edgar.services.ingest_htm import ingest_htm_filing
from sec_edgar.services.sic_reference import search_sic_codes
from warehouse.models import (
    Company,
    DerivedMetric,
    EdgarEntitySyncState,
    Fact,
    Filing,
    PeerGroup,
    Section,
    Table,
)
from warehouse.services.edgar.analytics import EdgarAnalyticsService
from warehouse.services.edgar.sync import EdgarSyncService

from ..filters import CompanyMetadataFilter, FactFilterSet
from ..sec_user_agent import sec_user_agent_email_from_request
from ..serializers import (
    CompanyMetadataSerializer,
    CompanySerializer,
    DerivedMetricSerializer,
    ExternalSeriesSerializer,
    FactSerializer,
    FilingSerializer,
    PeerGroupSerializer,
    SectionSerializer,
    SeriesBundleSerializer,
    SeriesObservationSerializer,
    TableSerializer,
)

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Liveness probe; does not check the database."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class HealthReadyView(APIView):
    """Readiness: verifies app can reach the default database."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            connection.ensure_connection()
        except Exception:
            return Response(
                {"status": "unready", "checks": {"database": False}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "checks": {"database": True}})


class SicCodesReferenceView(APIView):
    """SEC SIC master list (from ``data/reference/sic_codes.json``) for lookup and autocomplete."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        qp = request.query_params
        try:
            lim = int(qp.get("limit", 50))
        except ValueError:
            lim = 50
        lim = max(1, min(lim, 200))
        code = (qp.get("code") or "").strip() or None
        q = (qp.get("q") or "").strip() or None
        rows = search_sic_codes(q=q, code=code, limit=lim)
        return Response({"count": len(rows), "results": rows})


class CompanyViewSet(viewsets.ModelViewSet):
    """CRUD for ``Company`` plus EDGAR resolution, sync, and read-only analytics helpers."""

    queryset = Company.objects.all().order_by("name")
    serializer_class = CompanySerializer
    filterset_fields = ["ticker", "cik", "industry", "sic_code", "hq_state"]
    search_fields = ["name", "ticker", "cik"]

    @action(detail=False, methods=["get"], url_path="edgar-search")
    def edgar_search(self, request):
        """Search listed issuers (DB-backed ``ListedIssuer``; optional ``force_refresh`` refetches SEC file)."""
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response(
                {"detail": "Query must be at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            lim = int(request.query_params.get("limit", 50))
        except ValueError:
            lim = 50
        lim = max(1, min(lim, 100))
        force_refresh = request.query_params.get("force_refresh", "").lower() in (
            "1",
            "true",
            "yes",
        )
        ua = sec_user_agent_email_from_request(request)
        try:
            matches = search_company_tickers(
                q,
                user_agent_email=ua,
                limit=lim,
                force_refresh=force_refresh,
            )
        except Exception:
            logger.exception("edgar_search failed")
            return Response(
                {"detail": "Could not load SEC company directory."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        ciks = [m["cik"] for m in matches]
        existing = set(Company.objects.filter(cik__in=ciks).values_list("cik", flat=True))
        results = [{**m, "in_warehouse": m["cik"] in existing} for m in matches]
        return Response({"count": len(results), "results": results})

    @action(detail=False, methods=["post"], url_path="from-edgar")
    def from_edgar(self, request):
        """Create or return a warehouse Company from EDGAR directory (DB first, then SEC)."""
        ticker = (request.data.get("ticker") or "").strip().upper() or None
        cik_raw = request.data.get("cik")
        name_override = (request.data.get("name") or "").strip() or None
        if not ticker and not cik_raw:
            return Response(
                {"detail": "Provide cik and/or ticker."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ua = sec_user_agent_email_from_request(request)
        try:
            company, created = EdgarSyncService.get_or_create_company_from_edgar(
                ticker=ticker,
                cik_raw=cik_raw,
                name_override=name_override,
                user_agent_email=ua,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception("from_edgar failed")
            return Response(
                {"detail": "Could not resolve company from SEC."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            CompanySerializer(company).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="bulk-from-edgar-tickers")
    def bulk_from_edgar_tickers(self, request):
        """Insert missing ``Company`` rows from SEC company_tickers.json (bulk, no per-CIK API)."""
        update_existing = bool(request.data.get("update_existing"))
        refresh_sec_json = bool(request.data.get("refresh_sec_json"))
        ua = sec_user_agent_email_from_request(request)
        try:
            stats = EdgarSyncService.bulk_sync_companies_from_sec_tickers(
                user_agent_email=ua,
                update_existing=update_existing,
                refresh_sec_json=refresh_sec_json,
            )
        except Exception:
            logger.exception("bulk_from_edgar_tickers failed")
            return Response(
                {"detail": "Bulk load failed."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(stats)

    @action(detail=True, methods=["post"], url_path="suggest-schema")
    def suggest_schema(self, request, pk=None):
        """Return static CRM-style field hints until filing-driven schema inference exists."""
        company = self.get_object()
        base_fields = [
            "industry",
            "management",
            "headquarters",
            "locations",
            "business_units",
            "product_types",
            "size",
        ]
        suggested = {
            "required": ["industry", "headquarters"],
            "recommended": base_fields,
            "custom_candidates": [
                "esg_policies",
                "risk_factors",
                "major_customers",
                "competitors",
                "supply_chain_regions",
                "revenue_streams",
            ],
            "notes": "Heuristic schema hints; refine with filings + AI later.",
        }
        return Response({"company": company.id, "suggested_schema": suggested})

    @action(detail=True, methods=["post"], url_path="sync-submissions")
    def sync_submissions(self, request, pk=None):
        company = self.get_object()
        ua = sec_user_agent_email_from_request(request)
        n = EdgarSyncService.sync_submissions(company, user_agent_email=ua)
        return Response({"company": company.id, "filings_processed": n})

    @action(detail=True, methods=["post"], url_path="sync-facts")
    def sync_facts(self, request, pk=None):
        company = self.get_object()
        ua = sec_user_agent_email_from_request(request)
        count = EdgarSyncService.sync_facts(company, user_agent_email=ua)
        return Response({"company": company.id, "facts_loaded": count})

    @action(detail=True, methods=["get"], url_path="edgar-sync-status")
    def edgar_sync_status(self, request, pk=None):
        company = self.get_object()
        state = EdgarEntitySyncState.objects.filter(company_id=company.id).first()
        return Response(
            {
                "company": company.id,
                "submissions_synced_at": state.submissions_synced_at if state else None,
                "facts_synced_at": state.facts_synced_at if state else None,
                "last_error": (state.last_error[:500] if state and state.last_error else ""),
            }
        )

    @action(detail=True, methods=["get"], url_path="analytics/latest-by-concepts")
    def analytics_latest_by_concepts(self, request, pk=None):
        company = self.get_object()
        raw = (request.query_params.get("concepts") or "").strip()
        concepts = [c.strip() for c in raw.split(",") if c.strip()]
        if not concepts:
            return Response(
                {"detail": "Provide concepts as comma-separated XBRL tags."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        taxonomy = (request.query_params.get("taxonomy") or "us-gaap").strip() or "us-gaap"
        data = EdgarAnalyticsService.latest_by_concepts(company, concepts, taxonomy=taxonomy)
        return Response({"company": company.id, "taxonomy": taxonomy, "values": data})

    @action(detail=True, methods=["get"], url_path="analytics/timeseries")
    def analytics_timeseries(self, request, pk=None):
        company = self.get_object()
        concept = (request.query_params.get("concept") or "").strip()
        if not concept:
            return Response(
                {"detail": "concept query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        taxonomy = (request.query_params.get("taxonomy") or "us-gaap").strip() or "us-gaap"
        try:
            lim = int(request.query_params.get("limit", 80))
        except ValueError:
            lim = 80
        lim = max(1, min(lim, 500))
        series = EdgarAnalyticsService.timeseries_for_concept(
            company, concept, taxonomy=taxonomy, limit=lim
        )
        return Response(
            {"company": company.id, "concept": concept, "taxonomy": taxonomy, "series": series}
        )


class CompanyMetadataPagination(PageNumberPagination):
    page_size = 40
    page_size_query_param = "page_size"
    max_page_size = 200


class FilingPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class CompanyMetadataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Paginated company metadata for filtering, sorting, and dashboard-style facets.
    """

    queryset = Company.objects.all()
    serializer_class = CompanyMetadataSerializer
    pagination_class = CompanyMetadataPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CompanyMetadataFilter
    search_fields = [
        "name",
        "ticker",
        "cik",
        "industry",
        "sic_description",
        "headquarters",
        "sic_code",
        "naics_code",
        "crm_external_key",
        "customer_vertical",
        "customer_class",
        "contract_status",
        "hq_city",
    ]
    ordering_fields = [
        "name",
        "ticker",
        "cik",
        "industry",
        "sic_code",
        "sic_description",
        "hq_state",
        "hq_country",
        "hq_city",
        "customer_vertical",
        "contract_status",
        "created_at",
        "updated_at",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return Company.objects.all().only(
            "id",
            "cik",
            "ticker",
            "name",
            "industry",
            "sic_code",
            "sic_description",
            "naics_code",
            "hq_state",
            "hq_country",
            "hq_city",
            "headquarters",
            "size",
            "crm_external_key",
            "customer_class",
            "customer_type",
            "customer_vertical",
            "contract_status",
            "created_at",
            "updated_at",
        )

    @action(detail=False, methods=["get"], url_path="facets")
    def facets(self, request):
        """Aggregate counts for SIC, state, industry, and coverage stats."""
        qs = Company.objects.all()
        total = qs.count()
        with_sic = (
            qs.exclude(sic_code__isnull=True).exclude(sic_code="").count()
        )
        with_naics = (
            qs.exclude(naics_code__isnull=True).exclude(naics_code="").count()
        )
        with_industry = (
            qs.exclude(industry__isnull=True).exclude(industry="").count()
        )
        top_sic = list(
            qs.exclude(sic_description__isnull=True)
            .exclude(sic_description="")
            .values("sic_code", "sic_description")
            .annotate(count=Count("id"))
            .order_by("-count")[:30]
        )
        hq_state = list(
            qs.exclude(hq_state__isnull=True)
            .exclude(hq_state="")
            .values("hq_state")
            .annotate(count=Count("id"))
            .order_by("-count")[:30]
        )
        industry = list(
            qs.exclude(industry__isnull=True)
            .exclude(industry="")
            .values("industry")
            .annotate(count=Count("id"))
            .order_by("-count")[:25]
        )
        hq_country = list(
            qs.values("hq_country")
            .annotate(count=Count("id"))
            .order_by("-count")[:15]
        )
        return Response(
            {
                "totals": {
                    "companies": total,
                    "with_sic_code": with_sic,
                    "with_naics_code": with_naics,
                    "with_industry_text": with_industry,
                },
                "top_sic": top_sic,
                "hq_state": hq_state,
                "industry": industry,
                "hq_country": hq_country,
            }
        )


class FilingViewSet(viewsets.ModelViewSet):
    queryset = Filing.objects.all().order_by("-filing_date")
    serializer_class = FilingSerializer
    pagination_class = FilingPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["form_type", "company"]
    search_fields = ["form_type", "accession_number"]
    ordering_fields = [
        "filing_date",
        "form_type",
        "accession_number",
        "period_of_report",
        "id",
    ]
    ordering = ["-filing_date"]

    @action(detail=False, methods=["post"], url_path="ingest-htm")
    def ingest_htm(self, request):
        """Parse one HTM filing URL into ``Filing`` / related rows (same service as ``ingest_htm`` command)."""
        url = request.data.get("url")
        ticker = request.data.get("ticker")
        cik = request.data.get("cik")
        if not url or (not ticker and not cik):
            return Response(
                {"detail": "url and ticker or cik are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ua = sec_user_agent_email_from_request(request)
            filing = ingest_htm_filing(url=url, ticker=ticker, cik=cik, user_agent_email=ua)
        except Exception as e:
            logger.exception("ingest_htm failed")
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(FilingSerializer(filing).data, status=status.HTTP_201_CREATED)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    filterset_fields = ["filing", "name"]


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    filterset_fields = ["filing"]


class FactViewSet(viewsets.ModelViewSet):
    queryset = Fact.objects.all().order_by("-period_end", "concept")
    serializer_class = FactSerializer
    filterset_class = FactFilterSet
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["concept"]
    ordering_fields = [
        "id",
        "period_end",
        "period_start",
        "concept",
        "taxonomy",
        "value",
        "company",
    ]
    ordering = ["-period_end", "concept"]

    @action(detail=False, methods=["get"], url_path="facets")
    def facets(self, request):
        company_id = request.query_params.get("company")
        if not company_id:
            return Response(
                {"detail": "company query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = Fact.objects.filter(company_id=company_id)
        by_tax = list(qs.values("taxonomy").annotate(c=Count("id")).order_by("-c"))
        top_concepts = list(qs.values("concept").annotate(c=Count("id")).order_by("-c")[:50])
        by_year = list(
            qs.exclude(period_end__isnull=True)
            .annotate(y=TruncYear("period_end"))
            .values("y")
            .annotate(c=Count("id"))
            .order_by("-y")[:25]
        )
        year_rows = []
        for x in by_year:
            y = x["y"]
            year_rows.append(
                {"year": y.year if y is not None else None, "count": x["c"]}
            )
        return Response(
            {
                "company": int(company_id),
                "taxonomy_counts": by_tax,
                "top_concepts": top_concepts,
                "facts_by_period_year": year_rows,
            }
        )


class DerivedMetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DerivedMetric.objects.all().order_by("-period_end", "key")
    serializer_class = DerivedMetricSerializer
    filterset_fields = ["company", "key"]


class PeerGroupViewSet(viewsets.ModelViewSet):
    queryset = PeerGroup.objects.all().order_by("name")
    serializer_class = PeerGroupSerializer
    search_fields = ["name"]

    @action(detail=True, methods=["get"], url_path="analytics/peer-fact-compare")
    def analytics_peer_fact_compare(self, request, pk=None):
        """Latest fact for ``concept`` across members of this peer group."""
        pg = self.get_object()
        concept = (request.query_params.get("concept") or "").strip()
        if not concept:
            return Response(
                {"detail": "concept query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        taxonomy = (request.query_params.get("taxonomy") or "us-gaap").strip() or "us-gaap"
        rows = EdgarAnalyticsService.peer_group_latest_for_concept(
            pg, concept, taxonomy=taxonomy
        )
        return Response(
            {
                "peer_group": pg.id,
                "concept": concept,
                "taxonomy": taxonomy,
                "rows": rows,
            }
        )


class ExternalSeriesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExternalSeries.objects.all().order_by("provider", "external_id")
    serializer_class = ExternalSeriesSerializer
    filterset_fields = ["provider", "external_id"]


class SeriesObservationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeriesObservation.objects.all().order_by("-observation_date")
    serializer_class = SeriesObservationSerializer
    filterset_fields = ["series"]


class SeriesBundleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeriesBundle.objects.all().order_by("slug")
    serializer_class = SeriesBundleSerializer
    lookup_field = "slug"

    @action(detail=True, methods=["get"], url_path="observations")
    def observations(self, request, slug=None):
        """Flatten recent observations for all series in this bundle (optional ``limit``)."""
        bundle = self.get_object()
        series_ids = list(bundle.items.values_list("series_id", flat=True))
        qs = SeriesObservation.objects.filter(series_id__in=series_ids).select_related(
            "series"
        )
        lim = int(request.query_params.get("limit", 5000))
        qs = qs.order_by("series_id", "-observation_date")[:lim]
        data = [
            {
                "series": o.series.external_id,
                "provider": o.series.provider,
                "date": o.observation_date.isoformat(),
                "value": str(o.value),
                "source_url": o.source_url,
            }
            for o in qs
        ]
        return Response({"bundle": bundle.slug, "count": len(data), "observations": data})
