from __future__ import annotations

import json

import pytest

from sec_edgar.services import sic_reference as sr
from sec_edgar.services.company_facts import sync_company_facts_to_db
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company, EdgarEntitySyncState, Fact, Filing


@pytest.fixture
def company(db) -> Company:
    return Company.objects.create(cik="0000320193", ticker="AAPL", name="Apple Inc.")


SUBMISSIONS_PAYLOAD = {
    "cik": "320193",
    "name": "Apple Inc.",
    "sic": "3571",
    "sicDescription": "Electronic Computers",
    "filings": {
        "recent": {
            "form": ["10-K", "10-K"],
            "accessionNumber": ["0000320193-23-000106", "0000320193-22-000108"],
            "filingDate": ["2023-11-03", "2022-10-28"],
            "reportDate": ["2023-09-30", "2022-09-30"],
            "primaryDocument": ["a.htm", "b.htm"],
        }
    },
}

COMPANYFACTS_PAYLOAD = {
    "cik": "320193",
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {
                            "end": "2023-09-30",
                            "val": 1_000_000,
                            "form": "10-K",
                            "filed": "2023-11-03",
                        }
                    ]
                }
            },
            "CostOfRevenue": {
                "units": {
                    "USD": [
                        {
                            "end": "2023-09-30",
                            "val": 600_000,
                            "form": "10-K",
                        }
                    ]
                }
            },
        }
    },
}


@pytest.mark.django_db
def test_sync_submissions_idempotent(company: Company) -> None:
    n1 = sync_submissions_for_company(company, SUBMISSIONS_PAYLOAD)
    assert n1 == 2
    assert Filing.objects.filter(company=company).count() == 2

    n2 = sync_submissions_for_company(company, SUBMISSIONS_PAYLOAD)
    assert n2 == 2
    assert Filing.objects.filter(company=company).count() == 2


@pytest.mark.django_db
def test_sync_company_facts_replaces_rows(company: Company) -> None:
    count = sync_company_facts_to_db(company, COMPANYFACTS_PAYLOAD)
    assert count == 2
    assert Fact.objects.filter(company=company).count() == 2

    payload2 = {
        **COMPANYFACTS_PAYLOAD,
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "end": "2024-09-30",
                                "val": 2_000_000,
                                "form": "10-K",
                            }
                        ]
                    }
                }
            }
        },
    }
    count2 = sync_company_facts_to_db(company, payload2)
    assert count2 == 1
    assert Fact.objects.filter(company=company).count() == 1


@pytest.mark.django_db
def test_sync_submissions_sets_edgar_entity_sync_state(company: Company) -> None:
    sync_submissions_for_company(company, SUBMISSIONS_PAYLOAD)
    st = EdgarEntitySyncState.objects.get(company=company)
    assert st.submissions_synced_at is not None


@pytest.mark.django_db
def test_sync_submissions_backfills_sic_description_from_reference(
    company: Company, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("EDGAR_DATA_DIR", str(tmp_path))
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "sic_codes.json").write_text(
        json.dumps(
            {
                "sic_codes": [
                    {
                        "code": "3571",
                        "office": "Office of Manufacturing",
                        "industry_title": "ELECTRONIC COMPUTERS",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    sr._sic_bundle = None
    payload = {**SUBMISSIONS_PAYLOAD}
    del payload["sicDescription"]
    try:
        sync_submissions_for_company(company, payload)
        company.refresh_from_db()
        assert company.sic_code == "3571"
        assert company.sic_description == "ELECTRONIC COMPUTERS"
    finally:
        sr._sic_bundle = None


@pytest.mark.django_db
def test_sync_company_facts_sets_edgar_entity_sync_state(company: Company) -> None:
    sync_company_facts_to_db(company, COMPANYFACTS_PAYLOAD)
    st = EdgarEntitySyncState.objects.get(company=company)
    assert st.facts_synced_at is not None
