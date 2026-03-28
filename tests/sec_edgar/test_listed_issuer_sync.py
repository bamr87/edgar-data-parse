from __future__ import annotations

import pytest
import responses

from warehouse.models import ListedIssuer
from warehouse.services.edgar.listed_issuers import (
    bulk_upsert_listed_issuers,
    sync_listed_issuers_from_remote,
)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

MOCK_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
}


@pytest.mark.django_db
def test_bulk_upsert_dedupes_duplicate_cik_in_batch() -> None:
    """Same CIK twice in one payload must not break Postgres ON CONFLICT (CardinalityViolation)."""
    n = bulk_upsert_listed_issuers(
        [
            {"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc."},
            {"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc. (dup)"},
        ]
    )
    assert n == 1
    assert ListedIssuer.objects.filter(cik="0000320193").count() == 1


@pytest.mark.django_db
@responses.activate
def test_sync_listed_issuers_from_remote_upserts_rows() -> None:
    responses.add(responses.GET, SEC_TICKERS_URL, json=MOCK_TICKERS, status=200)
    stats = sync_listed_issuers_from_remote(user_agent_email="dev@example.com")
    assert stats["issuers_upserted"] == 2
    assert ListedIssuer.objects.filter(cik="0000320193").exists()
    assert ListedIssuer.objects.get(cik="0000789019").ticker == "MSFT"
