"""Shim: use ``sec_edgar.client`` (SEC direct API)."""

from sec_edgar.client import SecEdgarClient, cik_ticker, default_headers, download_filing

headers = default_headers()


def get_facts(ticker: str) -> dict:
    """Return raw SEC companyfacts JSON for ticker's CIK."""
    client = SecEdgarClient()
    info = client.cik_for_ticker(ticker)
    return client.company_facts(info["cik"])
