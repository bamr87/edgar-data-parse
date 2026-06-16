"""DerivedMetric computation from Facts (Phase 5)."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from warehouse.models import Company, DerivedMetric, Fact
from warehouse.services.edgar.metrics import compute_derived_metrics

FY = {"period_start": datetime.date(2023, 1, 1), "period_end": datetime.date(2023, 12, 31)}


def _fact(company, concept, value, **kw):
    base = {"taxonomy": "us-gaap", "value": Decimal(value), **FY}
    base.update(kw)
    return Fact.objects.create(company=company, concept=concept, **base)


@pytest.mark.django_db
def test_gross_margin_computed():
    co = Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple")
    _fact(co, "Revenues", "100", dimensions={"accn": "0000320193-24-000001"})
    _fact(co, "CostOfGoodsAndServicesSold", "60")

    written = compute_derived_metrics(co)
    assert written >= 1

    gm = DerivedMetric.objects.get(company=co, key="gross_margin", period_end=FY["period_end"])
    # (100 - 60) / 100 = 0.4
    assert gm.value == Decimal("0.400000")
    assert gm.unit == "ratio"
    assert gm.extra["source"] == "computed:financial_model"
    assert "fetched_at" in gm.extra


@pytest.mark.django_db
def test_zero_revenue_skips_gross_margin():
    co = Company.objects.create(cik="0000000001", name="ZeroCo")
    _fact(co, "Revenues", "0")
    _fact(co, "CostOfGoodsAndServicesSold", "10")

    compute_derived_metrics(co)
    assert not DerivedMetric.objects.filter(company=co, key="gross_margin").exists()


@pytest.mark.django_db
def test_missing_operand_skips_metric():
    co = Company.objects.create(cik="0000000002", name="NoCostCo")
    _fact(co, "Revenues", "100")  # no cost_of_revenue fact

    compute_derived_metrics(co)
    # gross_margin requires both revenue and cost_of_revenue
    assert not DerivedMetric.objects.filter(company=co, key="gross_margin").exists()


@pytest.mark.django_db
def test_concept_preference_order():
    """The first concept in a group's preference list wins."""
    co = Company.objects.create(cik="0000000003", name="PrefCo")
    # "Revenues" is preferred over "SalesRevenueNet" in the revenue group.
    _fact(co, "Revenues", "200")
    _fact(co, "SalesRevenueNet", "999")
    _fact(co, "CostOfGoodsAndServicesSold", "100")

    compute_derived_metrics(co)
    gm = DerivedMetric.objects.get(company=co, key="gross_margin")
    # (200 - 100) / 200 = 0.5  (uses Revenues=200, not SalesRevenueNet)
    assert gm.value == Decimal("0.500000")


@pytest.mark.django_db
def test_recompute_is_idempotent():
    co = Company.objects.create(cik="0000000004", name="IdemCo")
    _fact(co, "Revenues", "100")
    _fact(co, "CostOfGoodsAndServicesSold", "40")

    compute_derived_metrics(co)
    first = DerivedMetric.objects.filter(company=co).count()
    compute_derived_metrics(co)
    assert DerivedMetric.objects.filter(company=co).count() == first
