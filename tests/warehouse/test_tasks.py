"""Celery sync tasks run eagerly in tests (Phase 7)."""

from __future__ import annotations

import datetime

import pytest
from rest_framework import status

from warehouse.models import Company, DerivedMetric, EdgarSecPayload, Fact
from warehouse.tasks import sync_facts_task

CIK = "0000320193"
COMPANY_FACTS_PAYLOAD = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "start": "2023-01-01", "val": 100, "accn": "x"}
                    ]
                }
            },
            "CostOfGoodsAndServicesSold": {
                "units": {
                    "USD": [
                        {"end": "2023-12-31", "start": "2023-01-01", "val": 60, "accn": "x"}
                    ]
                }
            },
        }
    },
}


def _seed_company_with_cached_facts() -> Company:
    company = Company.objects.create(cik=CIK, ticker="AAPL", name="Apple Inc.")
    EdgarSecPayload.objects.create(
        cik=CIK,
        kind=EdgarSecPayload.Kind.COMPANY_FACTS,
        payload=COMPANY_FACTS_PAYLOAD,
        fetched_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
    )
    return company


@pytest.mark.django_db
def test_sync_facts_task_loads_facts_and_metrics_eagerly():
    company = _seed_company_with_cached_facts()
    # DB-first read of the cached payload means no SEC HTTP call.
    result = sync_facts_task.delay(company.id)
    assert result.successful()
    assert Fact.objects.filter(company=company).count() == 2
    # compute_metrics defaults True on the async task.
    assert DerivedMetric.objects.filter(company=company, key="gross_margin").exists()


@pytest.mark.django_db
def test_sync_facts_endpoint_async_returns_202(admin_client):
    company = _seed_company_with_cached_facts()
    r = admin_client.post(f"/api/v1/companies/{company.id}/sync-facts/?async=true")
    assert r.status_code == status.HTTP_202_ACCEPTED
    body = r.json()
    assert body["status"] == "queued"
    assert body["task_id"]
    # Eager execution means the work completed before the response returned.
    assert Fact.objects.filter(company=company).count() == 2


@pytest.mark.django_db
def test_sync_facts_endpoint_sync_default(admin_client):
    company = _seed_company_with_cached_facts()
    r = admin_client.post(f"/api/v1/companies/{company.id}/sync-facts/")
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["facts_loaded"] == 2
