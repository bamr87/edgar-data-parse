"""SEC Standard Industrial Classification (SIC) reference table (from www.sec.gov HTML list)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from django.conf import settings

SIC_CODE_LIST_URL = (
    "https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list"
)

_sic_bundle: dict[str, Any] | None = None


def default_sic_reference_path() -> Path:
    """JSON under project ``data/reference/`` (see ``EDGAR_DATA_DIR``)."""
    base = Path(os.getenv("EDGAR_DATA_DIR", str(Path(settings.BASE_DIR).parent / "data")))
    return (base / "reference" / "sic_codes.json").resolve()


def parse_sic_table_html(html: str) -> list[dict[str, str]]:
    """
    Parse the SEC.gov SIC list page: table with columns SIC Code, Office, Industry Title.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="list")
    if table is None:
        raise ValueError("No table.list found in SIC page HTML")
    rows: list[dict[str, str]] = []
    tbody = table.find("tbody")
    if not tbody:
        raise ValueError("SIC table has no tbody")
    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 3:
            continue
        code = cells[0].get_text(strip=True)
        office = cells[1].get_text(strip=True)
        industry_title = cells[2].get_text(strip=True)
        if not code or not re.match(r"^\d+$", code):
            continue
        rows.append(
            {
                "code": code,
                "office": office,
                "industry_title": industry_title,
            }
        )
    if not rows:
        raise ValueError("Parsed zero SIC rows from HTML")
    return rows


def sic_codes_from_bundle(data: Any) -> list[dict[str, str]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "sic_codes" in data:
        return data["sic_codes"]
    raise ValueError("sic_codes.json must be a list or an object with key sic_codes")


def load_sic_bundle(path: Path | None = None, *, force_reload: bool = False) -> dict[str, Any]:
    """Load full JSON document (metadata + sic_codes). Cached per process."""
    global _sic_bundle
    p = path or default_sic_reference_path()
    if _sic_bundle is not None and not force_reload:
        return _sic_bundle
    if not p.is_file():
        _sic_bundle = {"sic_codes": [], "source_url": SIC_CODE_LIST_URL, "missing_file": str(p)}
        return _sic_bundle
    raw = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        bundle = {"sic_codes": raw, "source_url": SIC_CODE_LIST_URL}
    elif isinstance(raw, dict):
        bundle = dict(raw)
        if "sic_codes" not in bundle:
            raise ValueError("sic_codes.json dict must contain sic_codes")
    else:
        raise ValueError("sic_codes.json must be a list or object")
    _sic_bundle = bundle
    return _sic_bundle


def load_sic_codes(path: Path | None = None, *, force_reload: bool = False) -> list[dict[str, str]]:
    return sic_codes_from_bundle(load_sic_bundle(path, force_reload=force_reload))


def sic_code_index(codes: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Map normalized SIC code string -> row."""
    out: dict[str, dict[str, str]] = {}
    for row in codes:
        c = row.get("code", "").strip()
        if c:
            out[c] = row
    return out


def industry_title_for_code(code: str | None, path: Path | None = None) -> str | None:
    """Resolve industry title from reference; ``code`` may include leading zeros or not."""
    if not code or not str(code).strip():
        return None
    normalized = str(code).strip()
    idx = sic_code_index(load_sic_codes(path))
    if normalized in idx:
        return idx[normalized]["industry_title"]
    no_zeros = normalized.lstrip("0") or "0"
    if no_zeros in idx:
        return idx[no_zeros]["industry_title"]
    return None


def _row_matches_query(row: dict[str, str], q: str) -> bool:
    ql = q.lower()
    rc = row["code"]
    if rc.startswith(q):
        return True
    if ql in row["office"].lower() or ql in row["industry_title"].lower():
        return True
    if q.isdigit() and q in rc:
        return True
    return False


def search_sic_codes(
    *,
    q: str | None = None,
    code: str | None = None,
    limit: int = 50,
    path: Path | None = None,
) -> list[dict[str, str]]:
    """
    Filter reference rows. ``q`` matches code prefix, digits substring in code, or substring of
    office/industry_title (case-insensitive). ``code`` returns at most one exact SIC match.
    """
    codes = load_sic_codes(path)
    lim = max(1, min(limit, 200))
    if code is not None and str(code).strip():
        c = str(code).strip()
        idx = sic_code_index(codes)
        if c in idx:
            return [idx[c]]
        alt = c.lstrip("0") or "0"
        if alt in idx:
            return [idx[alt]]
        return []
    q = (q or "").strip()
    if not q:
        return codes[:lim]
    out = [row for row in codes if _row_matches_query(row, q)]
    return out[:lim]


def build_bundle_from_rows(
    rows: list[dict[str, str]],
    *,
    source_url: str = SIC_CODE_LIST_URL,
) -> dict[str, Any]:
    return {
        "source_url": source_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sic_codes": rows,
    }
