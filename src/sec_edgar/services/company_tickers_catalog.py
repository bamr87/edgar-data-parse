"""Load and search SEC's public company_tickers.json (listed issuers with tickers)."""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.db.models import Q

from sec_edgar.client import SecEdgarClient
from sec_edgar.services.ticker_json import (
    CACHE_KEY,
    CACHE_TTL_SECONDS,
    flat_records_from_payload,
)
from warehouse.models import ListedIssuer

logger = logging.getLogger(__name__)

# Backwards compatibility for imports of CACHE_KEY from this module
__all__ = [
    "CACHE_KEY",
    "CACHE_TTL_SECONDS",
    "clear_company_tickers_cache",
    "iter_flat_company_records",
    "load_company_tickers_json",
    "lookup_cik_record",
    "row_matches_query",
    "search_company_tickers",
]


def clear_company_tickers_cache() -> None:
    cache.delete(CACHE_KEY)


def load_company_tickers_json(*, user_agent_email: str | None) -> dict[str, Any] | list[Any]:
    """Fetch SEC company_tickers.json with process-wide caching."""
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    client = SecEdgarClient(user_agent_email=user_agent_email)
    data = client.company_tickers()
    cache.set(CACHE_KEY, data, CACHE_TTL_SECONDS)
    logger.info("Cached SEC company_tickers.json (%s)", CACHE_KEY)
    return data


def _ensure_listed_issuers_materialized(
    *,
    user_agent_email: str | None,
    force_refresh: bool = False,
) -> None:
    from warehouse.services.edgar.listed_issuers import bulk_upsert_listed_issuers

    if force_refresh:
        clear_company_tickers_cache()
        raw = load_company_tickers_json(user_agent_email=user_agent_email)
        records = flat_records_from_payload(raw)
        bulk_upsert_listed_issuers(records)
        return
    if ListedIssuer.objects.exists():
        return
    raw = load_company_tickers_json(user_agent_email=user_agent_email)
    records = flat_records_from_payload(raw)
    bulk_upsert_listed_issuers(records)


def iter_flat_company_records(
    *,
    user_agent_email: str | None,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    _ensure_listed_issuers_materialized(
        user_agent_email=user_agent_email, force_refresh=force_refresh
    )
    return [
        {"cik": li.cik, "ticker": li.ticker, "name": li.name}
        for li in ListedIssuer.objects.all().order_by("cik")
    ]


def lookup_cik_record(cik_padded: str, *, user_agent_email: str | None) -> dict[str, Any] | None:
    cik = str(cik_padded).zfill(10)
    try:
        norm = str(int(cik)).zfill(10)
    except ValueError:
        return None
    _ensure_listed_issuers_materialized(user_agent_email=user_agent_email)
    li = ListedIssuer.objects.filter(cik=norm).first()
    if li:
        return {"cik": li.cik, "ticker": li.ticker, "name": li.name}
    return None


def row_matches_query(rec: dict[str, Any], q: str) -> bool:
    q = q.strip()
    if len(q) < 2:
        return False
    q_lower = q.lower()
    cik = rec["cik"]
    ticker = (rec.get("ticker") or "").strip()
    name_l = rec["name"].lower()
    digits = "".join(c for c in q if c.isdigit())
    if len(digits) >= 3:
        try:
            if cik == str(int(digits)).zfill(10):
                return True
        except ValueError:
            pass
    if ticker:
        if q_lower == ticker.lower():
            return True
        if q_lower in ticker.lower():
            return True
    return q_lower in name_l


def _rank_match(rec: dict[str, Any], q: str) -> tuple[int, str]:
    """Lower tuple sorts first (better)."""
    q = q.strip()
    q_lower = q.lower()
    ticker = (rec.get("ticker") or "").strip()
    if ticker and q_lower == ticker.lower():
        return (0, rec["name"])
    digits = "".join(c for c in q if c.isdigit())
    if len(digits) >= 3:
        try:
            if rec["cik"] == str(int(digits)).zfill(10):
                return (1, rec["name"])
        except ValueError:
            pass
    if ticker and q_lower in ticker.lower():
        return (2, rec["name"])
    return (3, rec["name"])


def _issuer_search_filter_q(q: str) -> Q:
    q_strip = q.strip()
    digits = "".join(c for c in q_strip if c.isdigit())
    parts: list[Q] = [Q(name__icontains=q_strip)]
    if q_strip:
        parts.append(Q(ticker__icontains=q_strip))
    if len(digits) >= 3:
        try:
            cik_padded = str(int(digits)).zfill(10)
            parts.append(Q(cik=cik_padded))
        except ValueError:
            pass
    combined = parts[0]
    for p in parts[1:]:
        combined |= p
    return combined


def search_company_tickers(
    q: str,
    *,
    user_agent_email: str | None,
    limit: int = 50,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` issuers matching ``q`` (DB-backed after first materialization)."""
    _ensure_listed_issuers_materialized(
        user_agent_email=user_agent_email, force_refresh=force_refresh
    )
    hits: list[dict[str, Any]] = []
    for li in ListedIssuer.objects.filter(_issuer_search_filter_q(q)).order_by("cik"):
        rec = {"cik": li.cik, "ticker": li.ticker, "name": li.name}
        if row_matches_query(rec, q):
            hits.append(rec)
    hits.sort(key=lambda r: _rank_match(r, q))
    return hits[:limit]
