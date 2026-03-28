"""Direct SEC HTTP implementation of EdgarDataSource."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sec_edgar.client import SecEdgarClient


class DirectEdgarAdapter:
    def __init__(
        self,
        client: SecEdgarClient | None = None,
        *,
        user_agent_email: str | None = None,
    ) -> None:
        self._client = client or SecEdgarClient(user_agent_email=user_agent_email)

    def cik_for_ticker(self, ticker: str) -> dict[str, str]:
        return self._client.cik_for_ticker(ticker)

    def submissions(self, cik_padded: str) -> dict[str, Any]:
        return self._client.submissions(cik_padded)

    def company_facts(self, cik_padded: str) -> dict[str, Any]:
        return self._client.company_facts(cik_padded)

    def company_concept(self, cik_padded: str, taxonomy: str, tag: str) -> dict[str, Any]:
        return self._client.company_concept(cik_padded, taxonomy, tag)

    def download_filing(self, url: str, path: str) -> None:
        self._client.download_to_path(url, Path(path))
