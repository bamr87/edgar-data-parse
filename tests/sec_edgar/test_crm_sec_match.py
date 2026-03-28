from __future__ import annotations

from sec_edgar.services.crm_sec_match import (
    lookup_issuer_for_crm_name,
    normalize_sec_title,
)


def test_normalize_sec_title() -> None:
    assert normalize_sec_title("  Apple   Inc.  ") == "apple inc."


def test_lookup_exact_single_hit() -> None:
    index = {"apple inc.": [{"cik": "0000320193", "ticker": "AAPL", "title": "Apple Inc."}]}
    cik, ticker, st = lookup_issuer_for_crm_name("Apple Inc.", index)
    assert st == "exact"
    assert cik == "0000320193"
    assert ticker == "AAPL"


def test_lookup_ambiguous() -> None:
    index = {
        "foo corp": [
            {"cik": "0000000001", "ticker": "FOO", "title": "Foo Corp"},
            {"cik": "0000000002", "ticker": "FOO2", "title": "Foo Corp"},
        ]
    }
    cik, ticker, st = lookup_issuer_for_crm_name("Foo Corp", index)
    assert st == "ambiguous"
    assert cik is None


def test_lookup_none() -> None:
    assert lookup_issuer_for_crm_name("No Such Issuer", {}) == (None, None, "none")
