import django_filters

from warehouse.models import Company, Fact


class CompanyMetadataFilter(django_filters.FilterSet):
    """Filter companies for the metadata explorer (industry, SIC, HQ, etc.)."""

    class Meta:
        model = Company
        fields = {
            "industry": ["exact", "icontains"],
            "sic_code": ["exact", "icontains"],
            "sic_description": ["icontains"],
            "naics_code": ["exact", "icontains"],
            "hq_state": ["exact"],
            "hq_country": ["exact"],
            "customer_class": ["exact", "icontains"],
            "customer_type": ["exact", "icontains"],
            "customer_vertical": ["exact", "icontains"],
            "contract_status": ["exact", "icontains"],
        }


class FactFilterSet(django_filters.FilterSet):
    concept = django_filters.CharFilter(field_name="concept", lookup_expr="icontains")
    period_end_after = django_filters.DateFilter(field_name="period_end", lookup_expr="gte")
    period_end_before = django_filters.DateFilter(field_name="period_end", lookup_expr="lte")

    class Meta:
        model = Fact
        fields = {
            "company": ["exact"],
            "taxonomy": ["exact"],
            "unit": ["exact"],
        }
