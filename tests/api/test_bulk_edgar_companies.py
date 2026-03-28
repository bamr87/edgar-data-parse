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
def test_bulk_from_edgar_tickers_inserts_missing(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple Inc.")

    r = api_client.post("/api/v1/companies/bulk-from-edgar-tickers/", {}, format="json")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["source_issuers"] == 3
    assert body["insert_attempted"] == 2
    assert body["warehouse_already_had"] == 1
    assert body["companies_updated"] == 0
    assert Company.objects.filter(cik="0000789019").exists()
    assert Company.objects.filter(cik="0001045810").exists()


@pytest.mark.django_db
@responses.activate
def test_bulk_from_edgar_tickers_idempotent(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    api_client.post("/api/v1/companies/bulk-from-edgar-tickers/", {}, format="json")
    r = api_client.post("/api/v1/companies/bulk-from-edgar-tickers/", {}, format="json")
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["insert_attempted"] == 0
    assert r.json()["warehouse_already_had"] == 3


@pytest.mark.django_db
@responses.activate
def test_bulk_from_edgar_tickers_update_existing(api_client) -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    Company.objects.create(cik="0000320193", ticker="AAPL", name="Wrong Name")

    r = api_client.post(
        "/api/v1/companies/bulk-from-edgar-tickers/",
        {"update_existing": True},
        format="json",
    )
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["companies_updated"] == 1
    assert Company.objects.get(cik="0000320193").name == "Apple Inc."
