from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    CompanyViewSet,
                    FactViewSet,
                    FilingViewSet,
                    SectionViewSet,
                    TableViewSet,
)

router = DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'filings', FilingViewSet)
router.register(r'facts', FactViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'tables', TableViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
