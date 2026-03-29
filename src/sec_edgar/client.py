"""HTTP client for SEC hosts (data.sec.gov, www.sec.gov).

Uses a descriptive User-Agent (see ``user_agent_string``) and ``tenacity`` retries with
backoff on GETs. HTTP 429 raises ``RuntimeError`` so callers can back off; SEC fair-access
guidance applies across all machines sharing the same contact identity.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def _resolve_contact_email(user_agent_email: str | None) -> str:
    if user_agent_email and "@" in user_agent_email:
        return user_agent_email.strip()[:254]
    return (os.getenv("USER_AGENT_EMAIL") or "contact@example.com").strip()


def user_agent_string(user_agent_email: str | None = None) -> str:
    return f"edgar-data-parse/1.0 ({_resolve_contact_email(user_agent_email)})"


def default_headers(user_agent_email: str | None = None) -> dict[str, str]:
    return {
        "User-Agent": user_agent_string(user_agent_email),
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json,text/html,*/*",
    }


class SecEdgarClient:
    """JSON and binary GETs for ticker index, submissions, companyfacts, companyconcept, and filing downloads."""

    BASE_DATA = "https://data.sec.gov"
    BASE_WWW = "https://www.sec.gov"

    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        user_agent_email: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(default_headers(user_agent_email))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_json(self, url: str) -> dict[str, Any]:
        r = self.session.get(url, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("SEC rate limit (429)")
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_text(self, url: str) -> str:
        r = self.session.get(url, timeout=120)
        if r.status_code == 429:
            raise RuntimeError("SEC rate limit (429)")
        r.raise_for_status()
        return r.text

    def download_to_path(self, url: str, path: Path) -> None:
        text = self.get_text(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        logger.info("Downloaded %s -> %s", url, path)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def download_binary_to_path(
        self, url: str, path: Path, *, chunk_size: int = 1 << 20
    ) -> None:
        """Stream a binary response (e.g. nightly EDGAR ZIP) to disk."""
        r = self.session.get(url, stream=True, timeout=600)
        if r.status_code == 429:
            raise RuntimeError("SEC rate limit (429)")
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as out:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    out.write(chunk)
        logger.info("Downloaded binary %s -> %s", url, path)

    def company_tickers(self) -> dict[str, Any]:
        return self.get_json(f"{self.BASE_WWW}/files/company_tickers.json")

    def cik_for_ticker(self, ticker: str) -> dict[str, str]:
        ticker = ticker.upper().replace(".", "-")
        data = self.company_tickers()
        for row in data.values():
            if row.get("ticker") == ticker:
                return {
                    "cik": str(row["cik_str"]).zfill(10),
                    "name": str(row["title"]),
                }
        raise ValueError(f"Ticker {ticker} not found")

    def submissions(self, cik_padded: str) -> dict[str, Any]:
        cik = cik_padded.zfill(10)
        return self.get_json(f"{self.BASE_DATA}/submissions/CIK{cik}.json")

    def company_facts(self, cik_padded: str) -> dict[str, Any]:
        cik = cik_padded.zfill(10)
        return self.get_json(f"{self.BASE_DATA}/api/xbrl/companyfacts/CIK{cik}.json")

    def company_concept(self, cik_padded: str, taxonomy: str, tag: str) -> dict[str, Any]:
        """Single concept series for one issuer (label, description, units) — SEC companyconcept API."""
        cik = cik_padded.zfill(10)
        safe_tag = quote(tag, safe="")
        return self.get_json(
            f"{self.BASE_DATA}/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{safe_tag}.json"
        )


def cik_ticker(ticker: str) -> dict[str, str]:
    """Backward-compatible helper used by legacy scripts."""
    return SecEdgarClient().cik_for_ticker(ticker)


def download_filing(url: str, save_path: str) -> None:
    """Backward-compatible helper."""
    SecEdgarClient().download_to_path(url, Path(save_path))
