"""Financial-statement builder + statements/compute-metrics API (Phase 5)."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from rest_framework import status

from warehouse.models import Company, Fact
from warehouse.services.edgar.statements import (
    available_statement_types,
    build_financial_statement,
)

FY = {"period_start": datetime.date(2023, 1, 1), "period_end": datetime.date(2023, 12, 31)}


@pytest.mark.django_db
def test_income_statement_ordered_with_accession():
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple")
    Fact.objects.create(
        company=co, concept="Revenues", taxonomy="us-gaap", value=Decimal("500"),
        dimensions={"accn": "0000320193-24-000001"}, **FY,
    )
    Fact.objects.create(
        company=co, concept="CostOfGoodsAndServicesSold", taxonomy="us-gaap",
        value=Decimal("300"), **FY,
    )

    stmt = build_financial_statement(co, "income_statement")
    keys = [li["key"] for li in stmt["line_items"]]
    assert keys == ["revenue", "cost_of_revenue"]  # schema order preserved
    revenue = stmt["line_items"][0]
    assert revenue["value"] == 500.0
    assert revenue["accession"] == "0000320193-24-000001"
    assert stmt["period_end"] == "2023-12-31"


@pytest.mark.django_db
def test_unknown_statement_type_raises_keyerror():
    co = Company.objects.create(cik="0000000005", name="X")
    with pytest.raises(KeyError):
        build_financial_statement(co, "not_a_statement")


def test_available_statement_types():
    types = available_statement_types()
    assert "income_statement" in types
    assert "balance_sheet" in types
    assert "cash_flow_statement" in types


@pytest.mark.django_db
def test_statements_endpoint(api_client):
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple")
    Fact.objects.create(
        company=co, concept="Revenues", taxonomy="us-gaap", value=Decimal("500"), **FY
    )
    r = api_client.get(f"/api/v1/companies/{co.id}/statements/?statement_type=income_statement")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["statement_type"] == "income_statement"
    assert body["line_items"][0]["key"] == "revenue"
    assert body["line_items"][0]["value"] == 500.0


@pytest.mark.django_db
def test_statements_endpoint_requires_type(api_client):
    co = Company.objects.create(cik="0000000006", name="X")
    r = api_client.get(f"/api/v1/companies/{co.id}/statements/")
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert "available" in r.json()


@pytest.mark.django_db
def test_statements_endpoint_unknown_type(api_client):
    co = Company.objects.create(cik="0000000007", name="X")
    r = api_client.get(
        f"/api/v1/companies/{co.id}/statements/?statement_type=bogus"
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_compute_metrics_endpoint_requires_admin(api_client):
    co = Company.objects.create(cik="0000000008", name="X")
    r = api_client.post(f"/api/v1/companies/{co.id}/compute-metrics/")
    assert r.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_compute_metrics_endpoint_admin(admin_client):
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple")
    Fact.objects.create(
        company=co, concept="Revenues", taxonomy="us-gaap", value=Decimal("100"), **FY
    )
    Fact.objects.create(
        company=co, concept="CostOfGoodsAndServicesSold", taxonomy="us-gaap",
        value=Decimal("40"), **FY,
    )
    r = admin_client.post(f"/api/v1/companies/{co.id}/compute-metrics/")
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["metrics_written"] >= 1
