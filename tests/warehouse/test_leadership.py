"""Leadership extraction + stakeholder-orientation analysis."""

from __future__ import annotations

import datetime
import decimal

import pytest
from rest_framework import status

from warehouse.models import Company, Fact, LeadershipPosition, Person, StakeholderAssessment
from warehouse.services.leadership import normalize_name, upsert_owner
from warehouse.services.stakeholder import compute_stakeholder_assessment

FY = {"period_start": datetime.date(2023, 1, 1), "period_end": datetime.date(2023, 12, 31)}

OWNER = {
    "cik": "0001494730", "name": "Musk Elon", "is_director": True, "is_officer": True,
    "is_ten_percent_owner": True, "officer_title": "Chief Executive Officer",
}


def test_normalize_name():
    assert normalize_name("  Musk   Elon ") == "musk elon"


@pytest.mark.django_db
def test_upsert_owner_creates_and_accumulates():
    co = Company.objects.create(cik="0001318605", ticker="TSLA", name="Tesla")
    person, pos, created = upsert_owner(
        co, OWNER, filing_date=datetime.date(2024, 1, 2), net_shares=-700, source_url="u"
    )
    assert created is True
    assert person.cik == "0001494730"
    assert pos.title == "Chief Executive Officer"
    assert pos.is_director and pos.is_officer and pos.is_ten_percent_owner
    assert pos.filings_count == 1
    assert pos.net_insider_shares == decimal.Decimal("-700")

    # Second filing for the same person+company: idempotent identity, accumulated signal.
    _, pos2, created2 = upsert_owner(co, OWNER, filing_date=datetime.date(2024, 2, 1), net_shares=100)
    assert created2 is False
    assert Person.objects.count() == 1
    assert LeadershipPosition.objects.filter(company=co).count() == 1
    assert pos2.filings_count == 2
    assert pos2.net_insider_shares == decimal.Decimal("-600")
    assert pos2.last_seen == datetime.date(2024, 2, 1)


def _annual_fact(co, concept, value):
    Fact.objects.create(
        company=co, taxonomy="us-gaap", concept=concept, value=decimal.Decimal(value), **FY
    )


@pytest.mark.django_db
def test_stakeholder_assessment_reinvestment_tilted():
    co = Company.objects.create(cik="0001318605", ticker="TSLA", name="Tesla")
    _annual_fact(co, "PaymentsToAcquirePropertyPlantAndEquipment", "10000000000")  # capex 10B
    _annual_fact(co, "ResearchAndDevelopmentExpense", "5000000000")  # R&D 5B
    _annual_fact(co, "PaymentsForRepurchaseOfCommonStock", "1000000000")  # buyback 1B
    _annual_fact(co, "Revenues", "100000000000")  # revenue 100B

    r = compute_stakeholder_assessment(co)
    names = {s["name"] for s in r["signals"]}
    assert "allocation_balance" in names
    assert "capex_intensity" in names
    assert r["orientation_index"] > 0.33
    assert r["label"] == "Reinvestment / stakeholder-tilted"
    assert "Heuristic model" in r["caveats"]
    # allocation signal discloses its source concepts
    alloc = next(s for s in r["signals"] if s["name"] == "allocation_balance")
    concepts = {i["concept"] for i in alloc["inputs"]}
    assert "PaymentsToAcquirePropertyPlantAndEquipment" in concepts
    # persisted
    assert StakeholderAssessment.objects.filter(company=co).exists()


@pytest.mark.django_db
def test_stakeholder_assessment_payout_tilted():
    co = Company.objects.create(cik="0000000002", name="PayoutCo")
    _annual_fact(co, "PaymentsToAcquirePropertyPlantAndEquipment", "1000000000")  # capex 1B
    _annual_fact(co, "PaymentsForRepurchaseOfCommonStock", "20000000000")  # buyback 20B
    _annual_fact(co, "PaymentsOfDividendsCommon", "10000000000")  # dividends 10B
    _annual_fact(co, "Revenues", "100000000000")
    r = compute_stakeholder_assessment(co)
    assert r["orientation_index"] < 0
    assert r["label"] == "Payout / shareholder-tilted"


@pytest.mark.django_db
def test_leadership_api(api_client):
    co = Company.objects.create(cik="0001318605", ticker="TSLA", name="Tesla")
    upsert_owner(co, OWNER, filing_date=datetime.date(2024, 1, 2), net_shares=-700)
    r = api_client.get(f"/api/v1/companies/{co.id}/leadership/")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] == 1
    assert body["leadership"][0]["name"] == "Musk Elon"
    assert body["leadership"][0]["title"] == "Chief Executive Officer"


@pytest.mark.django_db
def test_stakeholder_assessment_api(api_client):
    co = Company.objects.create(cik="0001318605", ticker="TSLA", name="Tesla")
    _annual_fact(co, "PaymentsToAcquirePropertyPlantAndEquipment", "10000000000")
    _annual_fact(co, "Revenues", "100000000000")
    r = api_client.get(f"/api/v1/companies/{co.id}/stakeholder-assessment/")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert "orientation_index" in body
    assert "caveats" in body and body["caveats"]
    assert isinstance(body["signals"], list)


@pytest.mark.django_db
def test_leadership_compare_api(api_client):
    for cik, name in [("0001318605", "Tesla"), ("0000037996", "Ford")]:
        co = Company.objects.create(cik=cik, name=name)
        _annual_fact(co, "Revenues", "100000000000")
        _annual_fact(co, "PaymentsToAcquirePropertyPlantAndEquipment", "8000000000")
    r = api_client.get("/api/v1/companies/leadership-compare/?cik=0001318605&cik=0000037996")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] == 2
    assert {row["name"] for row in body["results"]} == {"Tesla", "Ford"}
    assert "caveats" in body
