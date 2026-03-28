"""Bulk insert/update ``warehouse.Company`` rows from SEC company_tickers.json."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from sec_edgar.services.company_tickers_catalog import iter_flat_company_records
from warehouse.models import Company

logger = logging.getLogger(__name__)

FETCH_BATCH = 800


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def sync_companies_from_sec_company_tickers(
    *,
    user_agent_email: str | None,
    update_existing: bool = False,
    refresh_sec_json: bool = False,
) -> dict[str, Any]:
    """
    Load SEC's public ticker file and upsert basic ``Company`` rows (CIK, name, ticker).

    Does not call per-company SEC APIs. Set ``refresh_sec_json`` to bypass the server
    cache and refetch ``company_tickers.json``.
    """
    raw_records = iter_flat_company_records(
        user_agent_email=user_agent_email,
        force_refresh=refresh_sec_json,
    )
    by_cik: dict[str, dict[str, Any]] = {}
    for rec in raw_records:
        by_cik[rec["cik"]] = rec

    ciks = list(by_cik.keys())
    existing: dict[str, Company] = {}
    for part in _chunks(ciks, FETCH_BATCH):
        for row in Company.objects.filter(cik__in=part):
            existing[row.cik] = row

    to_create: list[Company] = []
    to_update: list[Company] = []

    for cik, rec in by_cik.items():
        name = str(rec["name"])[:255]
        ticker = rec.get("ticker")
        if cik not in existing:
            to_create.append(Company(cik=cik, name=name, ticker=ticker))
        elif update_existing:
            obj = existing[cik]
            if obj.name != name or obj.ticker != ticker:
                obj.name = name
                obj.ticker = ticker
                to_update.append(obj)

    updated = 0
    with transaction.atomic():
        if to_create:
            Company.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
        if to_update:
            Company.objects.bulk_update(to_update, ["name", "ticker"], batch_size=500)
            updated = len(to_update)

    logger.info(
        "bulk_company_tickers: source=%s insert_attempted=%s updated=%s already_in_warehouse=%s",
        len(by_cik),
        len(to_create),
        updated,
        len(existing),
    )

    return {
        "source_issuers": len(by_cik),
        "insert_attempted": len(to_create),
        "companies_updated": updated,
        "warehouse_already_had": len(existing),
        "update_existing": update_existing,
        "refresh_sec_json": refresh_sec_json,
    }
