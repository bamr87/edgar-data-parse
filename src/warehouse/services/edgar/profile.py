"""Company-360 read model + cross-company cohort analytics (Phase 9).

Composes structured (facts, derived metrics, filings) and unstructured (filing
documents) data into one provenance-tagged view per company, and compares a
concept across cohorts grouped by industry/region/size.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from warehouse.models import (
    Company,
    DerivedMetric,
    ExternalIdentifier,
    Fact,
    Filing,
    FilingDocument,
)

# Fields a cohort may be grouped by (allowlist guards the ORM lookup).
COHORT_GROUP_FIELDS = {
    "sic_code",
    "sic_description",
    "hq_state",
    "hq_country",
    "industry",
    "customer_vertical",
}


def build_company_profile(company: Company) -> dict[str, Any]:
    """Assemble a consolidated, provenance-tagged 360 view for one company."""
    latest_metrics: dict[str, Any] = {}
    for m in (
        DerivedMetric.objects.filter(company=company)
        .order_by("key", "-period_end")
        .values("key", "period_end", "value", "unit")
    ):
        if m["key"] not in latest_metrics:
            latest_metrics[m["key"]] = {
                "value": float(m["value"]) if m["value"] is not None else None,
                "unit": m["unit"],
                "period_end": m["period_end"].isoformat() if m["period_end"] else None,
            }

    filings_qs = Filing.objects.filter(company=company).order_by("-filing_date")
    recent_filings = [
        {
            "accession_number": f.accession_number,
            "form_type": f.form_type,
            "filing_date": f.filing_date.isoformat() if f.filing_date else None,
        }
        for f in filings_qs[:5]
    ]

    docs = [
        {"type": d.type, "file_name": d.file_name, "snippet": (d.text or "")[:200]}
        for d in FilingDocument.objects.filter(filing__company=company)
        .order_by("-filing__filing_date")[:5]
    ]

    identifiers = list(
        ExternalIdentifier.objects.filter(company=company).values("system", "value", "confidence")
    )
    sync = getattr(company, "edgar_sync", None)
    facts_as_of = sync.facts_synced_at.isoformat() if sync and sync.facts_synced_at else None

    return {
        "company": company.id,
        "identity": {
            "cik": company.cik,
            "ticker": company.ticker,
            "name": company.name,
            "sic_code": company.sic_code,
            "sic_description": company.sic_description,
            "hq_state": company.hq_state,
            "hq_country": company.hq_country,
            "industry": company.industry,
            "identifiers": identifiers,
            "provenance": {"source": "sec_edgar+crm"},
        },
        "financials": {
            "derived_metrics": latest_metrics,
            "filing_count": filings_qs.count(),
            "provenance": {"source": "computed:financial_model", "as_of": facts_as_of},
        },
        "filings": {
            "recent": recent_filings,
            "provenance": {"source": "sec_edgar:submissions", "as_of": facts_as_of},
        },
        "documents": {
            "recent": docs,
            "provenance": {"source": "sec_edgar:filing_documents"},
        },
        "crm": {
            "customer_class": company.customer_class,
            "customer_type": company.customer_type,
            "customer_vertical": company.customer_vertical,
            "contract_status": company.contract_status,
            "provenance": {"source": "crm"},
        },
    }


def cohort_compare(
    *, group_by: str, concept: str, taxonomy: str = "us-gaap", limit: int = 200
) -> dict[str, Any]:
    """Compare the latest value of ``concept`` across companies grouped by a field.

    Raises ``ValueError`` for an unsupported ``group_by`` (callers map to HTTP 400).
    """
    if group_by not in COHORT_GROUP_FIELDS:
        raise ValueError(f"Unsupported group_by '{group_by}'")

    companies = (
        Company.objects.exclude(**{f"{group_by}__isnull": True})
        .exclude(**{group_by: ""})
    )
    group_of = dict(companies.values_list("id", group_by))

    latest: dict[int, float] = {}
    for f in (
        Fact.objects.filter(
            company_id__in=group_of.keys(),
            taxonomy=taxonomy,
            concept=concept,
            period_end__isnull=False,
            value__isnull=False,
        )
        .order_by("company_id", "-period_end", "-id")
        .values("company_id", "value")
    ):
        fact_value = f["value"]
        if fact_value is not None:  # value__isnull=False already excludes None
            latest.setdefault(f["company_id"], float(fact_value))

    buckets: dict[str, list[float]] = defaultdict(list)
    for company_id, value in latest.items():
        group = group_of.get(company_id)
        if group:
            buckets[group].append(value)

    rows: list[dict[str, Any]] = [
        {
            "group": group,
            "company_count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "sum": sum(values),
        }
        for group, values in buckets.items()
    ]
    rows.sort(key=lambda r: -r["company_count"])
    return {"group_by": group_by, "concept": concept, "taxonomy": taxonomy, "groups": rows[:limit]}
