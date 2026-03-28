"""Abstract EDGAR data source (hybrid: direct API vs optional library)."""

from __future__ import annotations

from typing import Any, Protocol


class EdgarDataSource(Protocol):
    def cik_for_ticker(self, ticker: str) -> dict[str, str]: ...

    def submissions(self, cik_padded: str) -> dict[str, Any]: ...

    def company_facts(self, cik_padded: str) -> dict[str, Any]: ...

    def download_filing(self, url: str, path: str) -> None: ...
