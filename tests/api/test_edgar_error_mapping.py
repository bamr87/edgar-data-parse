"""EDGAR errors map to correct HTTP statuses (Phase 3 typed exceptions)."""

from __future__ import annotations

import pytest
import responses
from django.core.cache import cache
from rest_framework import status

from sec_edgar.exceptions import EdgarRateLimitError, EdgarResolutionError
from warehouse.services.edgar.sync import EdgarSyncService

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
MOCK_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.delete("sec_edgar:company_tickers_json:v1")


@pytest.mark.django_db
@responses.activate
def test_from_edgar_unknown_ticker_maps_to_404(admin_client) -> None:
    """End-to-end: an unresolvable ticker surfaces EdgarResolutionError -> 404."""
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    r = admin_client.post("/api/v1/companies/from-edgar/", {"ticker": "ZZZZ"}, format="json")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_edgar_search_rate_limit_maps_to_429(api_client, monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise EdgarRateLimitError("SEC rate limit (429)")

    monkeypatch.setattr(EdgarSyncService, "search_edgar_directory", staticmethod(_raise))
    r = api_client.get("/api/v1/companies/edgar-search/?q=apple")
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_from_edgar_rate_limit_maps_to_429(admin_client, monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise EdgarRateLimitError("SEC rate limit (429)")

    monkeypatch.setattr(
        EdgarSyncService, "get_or_create_company_from_edgar", staticmethod(_raise)
    )
    r = admin_client.post("/api/v1/companies/from-edgar/", {"ticker": "AAPL"}, format="json")
    assert r.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_from_edgar_resolution_error_maps_to_404(admin_client, monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise EdgarResolutionError("Could not resolve issuer")

    monkeypatch.setattr(
        EdgarSyncService, "get_or_create_company_from_edgar", staticmethod(_raise)
    )
    r = admin_client.post("/api/v1/companies/from-edgar/", {"ticker": "AAPL"}, format="json")
    assert r.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_anon_write_is_forbidden(api_client) -> None:
    """Unauthenticated writes are rejected by IsAdminOrReadOnly (no SEC call made)."""
    r = api_client.post("/api/v1/companies/from-edgar/", {"ticker": "AAPL"}, format="json")
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
