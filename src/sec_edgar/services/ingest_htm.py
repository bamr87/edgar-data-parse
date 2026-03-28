"""Persist HTM filing parse results into warehouse models."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

from sec_edgar.parsers.htm import parse_sec_htm
from warehouse.models import Company, Filing, Section, Table

if TYPE_CHECKING:
    from sec_edgar.adapters.direct import DirectEdgarAdapter


def _default_data_dir() -> Path:
    base = getattr(settings, "EDGAR_DATA_DIR", None)
    if base:
        return Path(base)
    return Path(settings.BASE_DIR).parent / "data"


def _accession_from_url_or_filename(url: str, filename: str) -> str:
    # SEC accession: 0001234567-23-000001
    m = re.search(r"(\d{10}-\d{2}-\d{6})", url)
    if m:
        return m.group(1)
    stem = filename.replace(".htm", "").replace(".txt", "")
    return stem[:30]


def ingest_htm_filing(
    *,
    url: str,
    ticker: str | None = None,
    cik: str | None = None,
    adapter: "DirectEdgarAdapter | None" = None,
    data_dir: Path | None = None,
    user_agent_email: str | None = None,
) -> Filing:
    from sec_edgar.adapters.direct import DirectEdgarAdapter as _DA

    ad = adapter or _DA(user_agent_email=user_agent_email)
    if not cik and ticker:
        info = ad.cik_for_ticker(ticker)
        cik = info["cik"]
        name = info["name"]
    elif cik:
        cik = str(cik).zfill(10)
        name = ticker or cik
    else:
        raise ValueError("ticker or cik required")

    company, _ = Company.objects.get_or_create(
        cik=cik, defaults={"ticker": ticker, "name": name}
    )
    if ticker and not company.ticker:
        company.ticker = ticker
        company.save(update_fields=["ticker", "updated_at"])

    filename = url.rstrip("/").split("/")[-1]
    out_dir = data_dir or _default_data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    save_path = out_dir / filename
    ad.download_filing(url, str(save_path))

    parsed = parse_sec_htm(save_path)
    accession = _accession_from_url_or_filename(url, filename)

    filing = Filing.objects.create(
        company=company,
        accession_number=accession,
        form_type="HTM",
        url=url,
        local_path=str(save_path),
        metadata={"source": "htm_ingest", "filename": filename},
    )
    for sec_name, content in parsed.get("sections", {}).items():
        Section.objects.create(filing=filing, name=sec_name, content=content)
    for table in parsed.get("tables", []):
        Table.objects.create(filing=filing, data=table)
    return filing
