from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from sec_edgar.services.bulk_zip_load import (
    ensure_company_for_bulk,
    parse_cik_from_zip_member,
    process_companyfacts_zip,
    process_submissions_zip,
)
from warehouse.models import Company, EdgarEntitySyncState, Fact, Filing

SUBMISSIONS_PAYLOAD = {
    "cik": "320193",
    "name": "Apple Inc.",
    "sic": "3571",
    "sicDescription": "Electronic Computers",
    "filings": {
        "recent": {
            "form": ["10-K"],
            "accessionNumber": ["0000320193-23-000106"],
            "filingDate": ["2023-11-03"],
            "reportDate": ["2023-09-30"],
            "primaryDocument": ["a.htm"],
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
        }
    },
}


def _write_zip(path: Path, members: dict[str, dict]) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, payload in members.items():
            zf.writestr(arcname, json.dumps(payload))
    path.write_bytes(buf.getvalue())


@pytest.mark.parametrize(
    "name,expected",
    [
        ("CIK0000320193.json", "0000320193"),
        ("subdir/CIK0000320193.json", "0000320193"),
        ("readme.txt", None),
    ],
)
def test_parse_cik_from_zip_member(name: str, expected: str | None) -> None:
    assert parse_cik_from_zip_member(name) == expected


@pytest.mark.django_db
def test_ensure_company_creates_when_not_only_existing(tmp_path: Path) -> None:
    c = ensure_company_for_bulk(
        "0000320193",
        COMPANYFACTS_PAYLOAD,
        kind="facts",
        only_existing=False,
    )
    assert c is not None
    assert c.cik == "0000320193"
    assert "Apple" in c.name


@pytest.mark.django_db
def test_process_submissions_zip_only_existing_skips_without_company(
    tmp_path: Path,
) -> None:
    z = tmp_path / "sub.zip"
    _write_zip(z, {"CIK0000320193.json": SUBMISSIONS_PAYLOAD})
    stats = process_submissions_zip(
        z,
        only_existing_companies=True,
        dry_run=False,
    )
    assert stats["processed"] == 0
    assert stats["skipped"] >= 1
    assert Filing.objects.count() == 0


@pytest.mark.django_db
def test_process_submissions_zip_loads(tmp_path: Path) -> None:
    Company.objects.create(cik="0000320193", name="Apple Inc.")
    z = tmp_path / "sub.zip"
    _write_zip(z, {"CIK0000320193.json": SUBMISSIONS_PAYLOAD})
    stats = process_submissions_zip(
        z,
        only_existing_companies=True,
    )
    assert stats["processed"] == 1
    assert Filing.objects.count() == 1
    c = Company.objects.get(cik="0000320193")
    state = EdgarEntitySyncState.objects.get(company=c)
    assert state.submissions_synced_at is not None


@pytest.mark.django_db
def test_process_companyfacts_zip_creates_company_and_facts(tmp_path: Path) -> None:
    z = tmp_path / "cf.zip"
    _write_zip(z, {"CIK0000320193.json": COMPANYFACTS_PAYLOAD})
    stats = process_companyfacts_zip(z, only_existing_companies=False)
    assert stats["processed"] == 1
    assert Company.objects.filter(cik="0000320193").exists()
    assert Fact.objects.count() == 1


@pytest.mark.django_db
def test_dry_run_counts_without_db_writes(tmp_path: Path) -> None:
    z = tmp_path / "cf.zip"
    _write_zip(z, {"CIK0000320193.json": COMPANYFACTS_PAYLOAD})
    stats = process_companyfacts_zip(z, dry_run=True, only_existing_companies=False)
    assert stats["processed"] == 1
    assert Company.objects.count() == 0
