"""
Optional third-party EDGAR library adapter (hybrid plan).

Install `edgartools` / `edgartools` or `edgartools` package separately if desired.
This module stays import-safe when the dependency is absent.
"""

from __future__ import annotations

from typing import Any


class OptionalEdgarLibraryAdapter:
    """Placeholder: wire to edgartools when the team pins a supported version."""

    def __init__(self) -> None:
        try:
            import edgar  # type: ignore  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "Optional EDGAR library not installed. Use DirectEdgarAdapter or pip install edgartools."
            ) from e

    def cik_for_ticker(self, ticker: str) -> dict[str, str]:
        raise NotImplementedError("Pin edgartools and implement mapping.")

    def submissions(self, cik_padded: str) -> dict[str, Any]:
        raise NotImplementedError

    def company_facts(self, cik_padded: str) -> dict[str, Any]:
        raise NotImplementedError

    def download_filing(self, url: str, path: str) -> None:
        raise NotImplementedError
