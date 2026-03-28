"""Match CRM company names to SEC company_tickers.json titles (exact normalized match)."""

from __future__ import annotations

import re
from typing import Any

from sec_edgar.services.company_tickers_catalog import iter_flat_company_records


def normalize_sec_title(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def build_title_index(
    *,
    user_agent_email: str | None,
) -> dict[str, list[dict[str, str]]]:
    """
    Map normalized SEC issuer title -> list of {cik, ticker, title}.
    Multiple CIKs can share a normalized title (ambiguous).
    """
    index: dict[str, list[dict[str, str]]] = {}
    for rec in iter_flat_company_records(user_agent_email=user_agent_email):
        title = str(rec.get("name") or "")
        key = normalize_sec_title(title)
        if not key:
            continue
        entry = {
            "cik": rec["cik"],
            "ticker": rec.get("ticker") or "",
            "title": title,
        }
        index.setdefault(key, []).append(entry)
    return index


def lookup_issuer_for_crm_name(
    name: str | None,
    index: dict[str, list[dict[str, str]]],
) -> tuple[str | None, str | None, str]:
    """
    Return (cik, ticker, status) where status is 'exact', 'ambiguous', or 'none'.
    """
    if not name or not str(name).strip():
        return None, None, "none"
    key = normalize_sec_title(str(name))
    if not key:
        return None, None, "none"
    hits = index.get(key) or []
    if len(hits) == 1:
        h = hits[0]
        return h["cik"], h["ticker"] or None, "exact"
    if len(hits) > 1:
        return None, None, "ambiguous"
    return None, None, "none"


def candidate_names_from_crm_row(row: dict[str, Any]) -> list[str]:
    """Ordered preference for matching against SEC titles."""
    out: list[str] = []
    for k in ("Unique Name", "Contract Name", "Global HQ Name", "Name"):
        v = row.get(k)
        if v is not None and str(v).strip():
            out.append(str(v).strip())
    # de-dupe preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for n in out:
        ln = n.lower()
        if ln not in seen:
            seen.add(ln)
            uniq.append(n)
    return uniq
