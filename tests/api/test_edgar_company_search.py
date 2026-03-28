from __future__ import annotations

import pytest
import responses
from django.core.cache import cache
from rest_framework import status

from warehouse.models import Company

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

MOCK_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    "2": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
}


@pytest.fixture(autouse=True)
def clear_sec_cache() -> None:
    cache.delete("sec_edgar:company_tickers_json:v1")


@pytest.mark.django_db
@responses.activate
def test_edgar_search_requires_min_length(api_client) -> None:
    r = api_client.get("/api/v1/companies/edgar-search/?q=a")
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@responses.activate
def test_edgar_search_returns_matches_and_in_warehouse(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple Inc.")

    r = api_client.get("/api/v1/companies/edgar-search/?q=apple")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] >= 1
    apple = next(x for x in body["results"] if x["cik"] == "0000320193")
    assert apple["in_warehouse"] is True

    r2 = api_client.get("/api/v1/companies/edgar-search/?q=microsoft")
    assert r2.status_code == status.HTTP_200_OK
    msft = next(x for x in r2.json()["results"] if x["cik"] == "0000789019")
    assert msft["in_warehouse"] is False


@pytest.mark.django_db
@responses.activate
def test_edgar_search_by_cik_digits(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    r = api_client.get("/api/v1/companies/edgar-search/?q=320193")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert any(x["cik"] == "0000320193" for x in body["results"])


@pytest.mark.django_db
@responses.activate
def test_from_edgar_creates_company(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    r = api_client.post(
        "/api/v1/companies/from-edgar/",
        {"ticker": "NVDA"},
        format="json",
    )
    assert r.status_code == status.HTTP_201_CREATED
    data = r.json()
    assert data["cik"] == "0001045810"
    assert data["ticker"] == "NVDA"
    assert Company.objects.filter(cik="0001045810").exists()


@pytest.mark.django_db
@responses.activate
def test_from_edgar_existing_returns_200(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    r = api_client.post(
        "/api/v1/companies/from-edgar/",
        {"cik": "0000320193"},
        format="json",
    )
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["id"] is not None
