"""FilingDocument ingest + full-text search (Phase 8)."""

from __future__ import annotations

import pytest
from rest_framework import status

from sec_edgar.services.ingest_submission import ingest_submission_documents
from sec_edgar.storage import LocalStorage
from warehouse.models import Company, Filing

SAMPLE = """<SEC-DOCUMENT>
<DOCUMENT>
<TYPE>10-K
<SEQUENCE>1
<FILENAME>doc1.htm
<TEXT>
<html><body>Annual report discussing revenue growth and inventory.</body></html>
</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-21.1
<SEQUENCE>2
<FILENAME>doc2.htm
<TEXT>
<html><body>List of subsidiaries of the registrant.</body></html>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""


def _filing() -> Filing:
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple")
    return Filing.objects.create(company=co, accession_number="0000320193-23-000106", form_type="10-K")


@pytest.mark.django_db
def test_ingest_submission_documents(tmp_path):
    filing = _filing()
    n = ingest_submission_documents(filing, SAMPLE, storage=LocalStorage(tmp_path))
    assert n == 2
    docs = list(filing.documents.order_by("sequence"))
    assert [d.type for d in docs] == ["10-K", "EX-21.1"]
    assert docs[0].is_processed is True
    assert "revenue growth" in docs[0].text
    assert docs[0].raw_key  # raw stored content-addressed
    # raw written to storage
    assert (tmp_path / docs[0].raw_key).exists()


@pytest.mark.django_db
def test_reingest_is_idempotent(tmp_path):
    filing = _filing()
    ingest_submission_documents(filing, SAMPLE, storage=LocalStorage(tmp_path))
    ingest_submission_documents(filing, SAMPLE, storage=LocalStorage(tmp_path))
    assert filing.documents.count() == 2  # unique_together (filing, sequence)


@pytest.mark.django_db
def test_document_search_endpoint(api_client, tmp_path):
    filing = _filing()
    ingest_submission_documents(filing, SAMPLE, storage=LocalStorage(tmp_path))

    r = api_client.get("/api/v1/filings/search/?q=revenue")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] >= 1
    assert any("revenue" in row["snippet"].lower() for row in body["results"])

    # Filter by form_type narrows results.
    r2 = api_client.get("/api/v1/filings/search/?q=subsidiaries&form_type=10-K")
    assert r2.status_code == status.HTTP_200_OK
    assert all(row["form_type"] == "10-K" for row in r2.json()["results"])


@pytest.mark.django_db
def test_document_search_requires_min_length(api_client):
    r = api_client.get("/api/v1/filings/search/?q=a")
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_ingest_submission_endpoint_requires_admin(api_client):
    r = api_client.post(
        "/api/v1/filings/ingest-submission/",
        {"url": "https://example.com/x.txt", "cik": "320193"},
        format="json",
    )
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
