from __future__ import annotations

import datetime

import pytest
from rest_framework import status

from warehouse.models import Company, Filing


@pytest.mark.django_db
def test_filings_list_paginated(api_client) -> None:
    co = Company.objects.create(cik="0000000999", ticker="ZZZ", name="PagerCo")
    for i in range(28):
        Filing.objects.create(
            company=co,
            accession_number=f"0000999999-24-{i:06d}",
            form_type="8-K",
            filing_date=datetime.date(2024, 1, 1) + datetime.timedelta(days=i),
        )
    r = api_client.get(f"/api/v1/filings/?company={co.id}&page_size=10&page=1")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["count"] == 28
    assert len(body["results"]) == 10
    r2 = api_client.get(f"/api/v1/filings/?company={co.id}&page_size=10&page=3")
    assert r2.status_code == status.HTTP_200_OK
    assert len(r2.json()["results"]) == 8


@pytest.mark.django_db
def test_filings_search_and_ordering(api_client) -> None:
    co = Company.objects.create(cik="0000000888", ticker="SRC", name="SearchCo")
    Filing.objects.create(
        company=co,
        accession_number="0000888888-24-000001",
        form_type="10-K",
        filing_date=datetime.date(2024, 6, 1),
    )
    Filing.objects.create(
        company=co,
        accession_number="0000888888-24-000088",
        form_type="8-K",
        filing_date=datetime.date(2024, 3, 1),
    )
    r = api_client.get(f"/api/v1/filings/?company={co.id}&search=8-K")
    assert r.status_code == status.HTTP_200_OK
    forms = {row["form_type"] for row in r.json()["results"]}
    assert forms == {"8-K"}
    r2 = api_client.get(f"/api/v1/filings/?company={co.id}&ordering=form_type")
    assert r2.status_code == status.HTTP_200_OK
    types = [row["form_type"] for row in r2.json()["results"]]
    assert types == sorted(types)
