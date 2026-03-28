"""Pure helpers for SEC ``company_tickers.json`` shape (list or dict of rows)."""

from __future__ import annotations

from typing import Any

CACHE_KEY = "sec_edgar:company_tickers_json:v1"
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


def normalize_rows(raw: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        return [v for v in raw.values() if isinstance(v, dict)]
    return []


def row_to_flat(row: dict[str, Any]) -> dict[str, Any] | None:
    cik_str = row.get("cik_str")
    if cik_str is None:
        return None
    try:
        cik = str(int(str(cik_str))).zfill(10)
    except (TypeError, ValueError):
        return None
    ticker = row.get("ticker")
    title = row.get("title")
    t = str(ticker).strip().upper() if ticker not in (None, "") else None
    name = str(title).strip() if title is not None else ""
    if not name:
        name = f"CIK {cik}"
    return {"cik": cik, "ticker": t, "name": name[:255]}


def flat_records_from_payload(raw: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in normalize_rows(raw):
        rec = row_to_flat(row)
        if rec:
            out.append(rec)
    return out
