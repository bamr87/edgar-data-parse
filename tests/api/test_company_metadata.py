from __future__ import annotations

import pytest
from rest_framework import status

from warehouse.models import Company


@pytest.mark.django_db
def test_company_metadata_facets_shape(api_client) -> None:
    Company.objects.create(
        cik="0000000001",
        ticker="TST",
        name="TestCo",
        sic_code="7370",
        sic_description="Services-Computer Programming Services",
        industry="Software",
        hq_state="CA",
        hq_country="US",
    )
    r = api_client.get("/api/v1/company-metadata/facets/")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["totals"]["companies"] >= 1
    assert "top_sic" in body
    assert "hq_state" in body
    assert "industry" in body
    assert "hq_country" in body


@pytest.mark.django_db
def test_company_metadata_list_paginated(api_client) -> None:
    Company.objects.create(cik="0000000002", ticker="A", name="Alpha Inc")
    Company.objects.create(cik="0000000003", ticker="B", name="Beta LLC")
    r = api_client.get("/api/v1/company-metadata/?page_size=1")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] >= 2
    assert len(body["results"]) == 1


@pytest.mark.django_db
def test_company_metadata_filter_sic(api_client) -> None:
    Company.objects.create(
        cik="0000000004",
        ticker="X",
        name="X",
        sic_code="7711",
        sic_description="Custom unique SIC for test",
    )
    Company.objects.create(cik="0000000005", ticker="Y", name="Y", sic_code="9999")
    r = api_client.get("/api/v1/company-metadata/?sic_code=7711")
    assert r.status_code == status.HTTP_200_OK
    ids = {row["cik"] for row in r.json()["results"]}
    assert "0000000004" in ids
    assert "0000000005" not in ids


@pytest.mark.django_db
def test_company_metadata_ordering(api_client) -> None:
    Company.objects.create(cik="0000000006", name="Zebra", sic_code="8888")
    Company.objects.create(cik="0000000007", name="Apple", sic_code="8888")
    r = api_client.get("/api/v1/company-metadata/?sic_code=8888&ordering=name")
    names = [row["name"] for row in r.json()["results"]]
    assert names == ["Apple", "Zebra"]
