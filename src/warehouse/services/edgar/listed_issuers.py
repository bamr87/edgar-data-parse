"""Persist SEC company_tickers.json rows as ``ListedIssuer`` for DB-first search."""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils import timezone

from sec_edgar.client import SecEdgarClient
from sec_edgar.services.ticker_json import CACHE_KEY, CACHE_TTL_SECONDS, flat_records_from_payload
from warehouse.models import ListedIssuer

logger = logging.getLogger(__name__)


def _dedupe_records_by_cik(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """SEC company_tickers.json can list the same CIK more than once; Postgres ON CONFLICT rejects duplicate keys in one batch."""
    by_cik: dict[str, dict[str, object]] = {}
    for r in records:
        cik = str(r["cik"])
        by_cik[cik] = r
    return list(by_cik.values())


def bulk_upsert_listed_issuers(records: list[dict[str, object]]) -> int:
    if not records:
        return 0
    records = _dedupe_records_by_cik(records)
    now = timezone.now()
    objs = [
        ListedIssuer(
            cik=r["cik"],
            ticker=r.get("ticker"),
            name=(r["name"] or f"CIK {r['cik']}")[:255],
            synced_at=now,
        )
        for r in records
    ]
    ListedIssuer.objects.bulk_create(
        objs,
        batch_size=2000,
        update_conflicts=True,
        unique_fields=["cik"],
        update_fields=["ticker", "name", "synced_at"],
    )
    return len(objs)


def sync_listed_issuers_from_remote(*, user_agent_email: str | None) -> dict[str, object]:
    """Fetch company_tickers.json, refresh JSON cache, upsert all ``ListedIssuer`` rows."""
    cache.delete(CACHE_KEY)
    raw = SecEdgarClient(user_agent_email=user_agent_email).company_tickers()
    cache.set(CACHE_KEY, raw, CACHE_TTL_SECONDS)
    records = flat_records_from_payload(raw)
    n = bulk_upsert_listed_issuers(records)
    logger.info("sync_listed_issuers_from_remote: upserted %s issuers", n)
    return {"issuers_upserted": n}
