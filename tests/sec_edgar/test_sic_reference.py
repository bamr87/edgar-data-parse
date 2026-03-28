from __future__ import annotations

import json

import pytest

from sec_edgar.services import sic_reference as sr


@pytest.fixture(autouse=True)
def clear_sic_cache():
    sr._sic_bundle = None
    yield
    sr._sic_bundle = None


SIC_HTML_FIXTURE = """<!DOCTYPE html><html><body>
<table class="list" width="100%">
  <thead><tr><th>SIC Code</th><th>Office</th><th>Industry Title</th></tr></thead>
  <tbody>
    <tr><td>7370</td><td>Office of Technology</td><td>SERVICES-COMPUTER PROGRAMMING SERVICES</td></tr>
    <tr><td>100</td><td>Industrial Applications</td><td>AGRICULTURAL PRODUCTION-CROPS</td></tr>
  </tbody>
</table>
</body></html>
"""


def test_parse_sic_table_html_extracts_rows() -> None:
    rows = sr.parse_sic_table_html(SIC_HTML_FIXTURE)
    assert len(rows) == 2
    assert rows[0] == {
        "code": "7370",
        "office": "Office of Technology",
        "industry_title": "SERVICES-COMPUTER PROGRAMMING SERVICES",
    }
    assert rows[1]["code"] == "100"


def test_search_sic_codes_by_q_prefix(tmp_path) -> None:
    p = tmp_path / "sic_codes.json"
    p.write_text(
        json.dumps(
            {
                "sic_codes": [
                    {"code": "7370", "office": "O1", "industry_title": "SOFTWARE SERVICES"},
                    {"code": "100", "office": "O2", "industry_title": "CROPS"},
                ]
            }
        ),
        encoding="utf-8",
    )
    sr._sic_bundle = None
    out = sr.search_sic_codes(q="737", limit=10, path=p)
    assert len(out) == 1
    assert out[0]["code"] == "7370"


def test_search_sic_codes_exact_code(tmp_path) -> None:
    p = tmp_path / "sic_codes.json"
    p.write_text(
        json.dumps(
            {
                "sic_codes": [
                    {"code": "7370", "office": "O1", "industry_title": "SERVICES"},
                ]
            }
        ),
        encoding="utf-8",
    )
    sr._sic_bundle = None
    out = sr.search_sic_codes(code="7370", limit=10, path=p)
    assert len(out) == 1


def test_industry_title_for_code(tmp_path) -> None:
    p = tmp_path / "sic_codes.json"
    p.write_text(
        json.dumps(
            {
                "sic_codes": [
                    {"code": "7370", "office": "O1", "industry_title": "SERVICES-COMPUTER"},
                ]
            }
        ),
        encoding="utf-8",
    )
    sr._sic_bundle = None
    assert sr.industry_title_for_code("7370", path=p) == "SERVICES-COMPUTER"
    assert sr.industry_title_for_code("07370", path=p) == "SERVICES-COMPUTER"
    assert sr.industry_title_for_code("9999", path=p) is None
