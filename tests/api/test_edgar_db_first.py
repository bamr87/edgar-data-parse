from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework import status

from warehouse.models import Company, Fact, ListedIssuer


@pytest.mark.django_db
def test_edgar_search_db_only_no_sec_http(api_client) -> None:
    ListedIssuer.objects.create(
        cik="0000320193",
        ticker="AAPL",
        name="Apple Inc.",
        synced_at=timezone.now(),
    )
    r = api_client.get("/api/v1/companies/edgar-search/?q=apple")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] >= 1
    assert any(x["cik"] == "0000320193" for x in body["results"])


@pytest.mark.django_db
def test_fact_facets_requires_company(api_client) -> None:
    r = api_client.get("/api/v1/facts/facets/")
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_fact_facets_taxonomy_and_concepts(api_client) -> None:
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    Fact.objects.create(
        company=co,
        taxonomy="us-gaap",
        concept="Revenues",
        period_end="2023-09-30",
        value="100.0000",
    )
    r = api_client.get(f"/api/v1/facts/facets/?company={co.id}")
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert data["company"] == co.id
    assert any(x["taxonomy"] == "us-gaap" for x in data["taxonomy_counts"])
    assert any(x["concept"] == "Revenues" for x in data["top_concepts"])


@pytest.mark.django_db
def test_company_analytics_latest_by_concepts(api_client) -> None:
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    Fact.objects.create(
        company=co,
        taxonomy="us-gaap",
        concept="Revenues",
        period_end="2023-09-30",
        value="100.0000",
    )
    r = api_client.get(
        f"/api/v1/companies/{co.id}/analytics/latest-by-concepts/"
        "?concepts=Revenues,MissingTag"
    )
    assert r.status_code == status.HTTP_200_OK
    vals = r.json()["values"]
    assert "Revenues" in vals
    assert vals["Revenues"]["value"] == 100.0
    assert "MissingTag" not in vals
