from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CompanyMetadataViewSet,
    CompanyViewSet,
    DerivedMetricViewSet,
    ExternalSeriesViewSet,
    FactViewSet,
    FilingViewSet,
    HealthReadyView,
    HealthView,
    PeerGroupViewSet,
    SectionViewSet,
    SeriesBundleViewSet,
    SeriesObservationViewSet,
    SicCodesReferenceView,
    TableViewSet,
)

router = DefaultRouter()
router.register(r"companies", CompanyViewSet)
router.register(r"company-metadata", CompanyMetadataViewSet, basename="company-metadata")
router.register(r"filings", FilingViewSet)
router.register(r"facts", FactViewSet)
router.register(r"sections", SectionViewSet)
router.register(r"tables", TableViewSet)
router.register(r"derived-metrics", DerivedMetricViewSet)
router.register(r"peer-groups", PeerGroupViewSet)
router.register(r"public-series", ExternalSeriesViewSet)
router.register(r"public-observations", SeriesObservationViewSet)
router.register(r"series-bundles", SeriesBundleViewSet)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/ready/", HealthReadyView.as_view(), name="health-ready"),
    path("reference/sic-codes/", SicCodesReferenceView.as_view(), name="reference-sic-codes"),
    path("", include(router.urls)),
]
