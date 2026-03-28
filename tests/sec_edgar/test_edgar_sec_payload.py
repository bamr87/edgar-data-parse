from __future__ import annotations

import pytest
import responses
from django.utils import timezone

from sec_edgar.services.company_facts import sync_company_facts_to_db
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company, EdgarSecPayload

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK0000320193.json"


@pytest.mark.django_db
def test_submissions_uses_db_without_second_http_call() -> None:
    EdgarSecPayload.objects.create(
        cik="0000320193",
        kind=EdgarSecPayload.Kind.SUBMISSIONS,
        payload={"cik": "0000320193", "name": "Cached", "filings": {"recent": {}}},
        fetched_at=timezone.now(),
    )
    company = Company.objects.create(cik="0000320193", name="Apple", ticker="AAPL")
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        n = sync_submissions_for_company(company, payload=None, user_agent_email="t@example.com")
    assert n == 0
    assert len(rsps.calls) == 0


@pytest.mark.django_db
@responses.activate
def test_submissions_fetches_when_cache_missing() -> None:
    responses.add(
        responses.GET,
        SEC_SUBMISSIONS,
        json={"cik": "0000320193", "name": "Apple Inc.", "filings": {"recent": {}}},
        status=200,
    )
    company = Company.objects.create(cik="0000320193", name="Apple", ticker="AAPL")
    sync_submissions_for_company(company, payload=None, user_agent_email="t@example.com")
    assert EdgarSecPayload.objects.filter(
        cik="0000320193", kind=EdgarSecPayload.Kind.SUBMISSIONS
    ).exists()


@pytest.mark.django_db
def test_zip_payload_persisted_for_future_reads() -> None:
    payload = {"cik": "0000320193", "name": "From ZIP", "filings": {"recent": {}}}
    company = Company.objects.create(cik="0000320193", name="X", ticker="AAPL")
    with responses.RequestsMock(assert_all_requests_are_fired=False):
        sync_submissions_for_company(company, payload=payload, user_agent_email="t@example.com")
    row = EdgarSecPayload.objects.get(cik="0000320193", kind=EdgarSecPayload.Kind.SUBMISSIONS)
    assert row.payload["name"] == "From ZIP"


@pytest.mark.django_db
def test_company_facts_uses_db_cache() -> None:
    EdgarSecPayload.objects.create(
        cik="0000320193",
        kind=EdgarSecPayload.Kind.COMPANY_FACTS,
        payload={
            "cik": 320193,
            "entityName": "Apple Inc.",
            "facts": {},
        },
        fetched_at=timezone.now(),
    )
    company = Company.objects.create(cik="0000320193", name="Apple", ticker="AAPL")
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        n = sync_company_facts_to_db(company, facts_payload=None, user_agent_email="t@example.com")
    assert n == 0
    assert len(rsps.calls) == 0
