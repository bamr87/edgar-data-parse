"""Company-360: identity resolution, content chunks, profile, cohort compare (Phase 9)."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from rest_framework import status

from warehouse.models import (
    Company,
    ContentChunk,
    DerivedMetric,
    ExternalIdentifier,
    Fact,
    Filing,
    FilingDocument,
)
from warehouse.services.chunks import chunk_text, index_filing_document
from warehouse.services.identity import index_company_identifiers, resolve_company

FY_END = datetime.date(2023, 12, 31)


# --- entity resolution ---


@pytest.mark.django_db
def test_index_and_resolve_identifiers():
    co = Company.objects.create(
        cik="0000320193", ticker="aapl", name="Apple", crm_external_key="CRM-1"
    )
    n = index_company_identifiers(co)
    assert n == 3
    assert ExternalIdentifier.objects.filter(company=co).count() == 3
    assert resolve_company("cik", "0000320193") == co
    assert resolve_company("ticker", "AAPL") == co  # normalized to upper
    assert resolve_company("crm", "CRM-1") == co
    assert resolve_company("ticker", "ZZZZ") is None


# --- chunking / AI foundation ---


def test_chunk_text_windows():
    text = "x" * 2500
    windows = list(chunk_text(text, size=1000, overlap=100))
    assert windows[0][0] == 0 and windows[0][1] == 1000
    assert all(len(c) <= 1000 for _, _, c in windows)
    assert windows[-1][1] == 2500


def test_chunk_text_empty():
    assert list(chunk_text("")) == []
    assert list(chunk_text("   ")) == []


@pytest.mark.django_db
def test_index_filing_document_creates_chunks():
    co = Company.objects.create(cik="0000320193", name="Apple")
    filing = Filing.objects.create(company=co, accession_number="a-1", form_type="10-K")
    doc = FilingDocument.objects.create(
        filing=filing, sequence=1, sha1="x", text="Revenue grew. " * 200
    )
    n = index_filing_document(doc)
    assert n >= 1
    chunks = ContentChunk.objects.filter(filing_document=doc)
    assert chunks.count() == n
    # Embeddings off by default -> no vectors, but text is retrievable.
    assert chunks.first().embedding is None
    assert chunks.first().company_id == co.id


# --- Company-360 profile ---


@pytest.mark.django_db
def test_company_profile_endpoint(api_client):
    co = Company.objects.create(
        cik="0000320193", ticker="AAPL", name="Apple", sic_code="3571",
        customer_vertical="Tech",
    )
    index_company_identifiers(co)
    DerivedMetric.objects.create(
        company=co, key="gross_margin", period_end=FY_END, value=Decimal("0.4"), unit="ratio"
    )
    f = Filing.objects.create(
        company=co, accession_number="a-1", form_type="10-K", filing_date=FY_END
    )
    FilingDocument.objects.create(
        filing=f, sequence=1, sha1="x", type="10-K", text="Annual report text."
    )

    r = api_client.get(f"/api/v1/companies/{co.id}/profile/")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["identity"]["cik"] == "0000320193"
    assert any(i["system"] == "ticker" for i in body["identity"]["identifiers"])
    assert body["financials"]["derived_metrics"]["gross_margin"]["value"] == 0.4
    assert body["financials"]["filing_count"] == 1
    assert body["filings"]["recent"][0]["form_type"] == "10-K"
    assert body["documents"]["recent"][0]["type"] == "10-K"
    assert body["crm"]["customer_vertical"] == "Tech"
    # Every panel is provenance-tagged.
    assert "provenance" in body["identity"]
    assert "provenance" in body["financials"]


# --- cohort compare ---


@pytest.mark.django_db
def test_cohort_compare_endpoint(api_client):
    for cik, rev in [("0000000001", 100), ("0000000002", 300)]:
        co = Company.objects.create(cik=cik, name=f"Co {cik}", sic_code="3571")
        Fact.objects.create(
            company=co, taxonomy="us-gaap", concept="Revenues",
            period_start=datetime.date(2023, 1, 1), period_end=FY_END, value=Decimal(rev),
        )
    r = api_client.get("/api/v1/companies/compare/?group_by=sic_code&concept=Revenues")
    assert r.status_code == status.HTTP_200_OK
    groups = r.json()["groups"]
    g = next(x for x in groups if x["group"] == "3571")
    assert g["company_count"] == 2
    assert g["avg"] == 200.0
    assert g["min"] == 100.0 and g["max"] == 300.0


@pytest.mark.django_db
def test_cohort_compare_requires_concept(api_client):
    r = api_client.get("/api/v1/companies/compare/?group_by=sic_code")
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cohort_compare_invalid_group_by(api_client):
    r = api_client.get("/api/v1/companies/compare/?group_by=evil&concept=Revenues")
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "allowed_group_by" in r.json()
