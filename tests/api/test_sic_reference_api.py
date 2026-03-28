from __future__ import annotations

import json

import pytest

from sec_edgar.services import sic_reference as sr


@pytest.mark.django_db
def test_reference_sic_codes_q(api_client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EDGAR_DATA_DIR", str(tmp_path))
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "sic_codes.json").write_text(
        json.dumps(
            {
                "sic_codes": [
                    {"code": "7370", "office": "O1", "industry_title": "SOFTWARE"},
                    {"code": "100", "office": "O2", "industry_title": "CROPS"},
                ]
            }
        ),
        encoding="utf-8",
    )
    sr._sic_bundle = None
    r = api_client.get("/api/v1/reference/sic-codes/?q=737")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["results"][0]["code"] == "7370"


@pytest.mark.django_db
def test_reference_sic_codes_code_exact(api_client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EDGAR_DATA_DIR", str(tmp_path))
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "sic_codes.json").write_text(
        json.dumps(
            {
                "sic_codes": [
                    {"code": "2834", "office": "Life", "industry_title": "PHARMACEUTICALS"},
                ]
            }
        ),
        encoding="utf-8",
    )
    sr._sic_bundle = None
    r = api_client.get("/api/v1/reference/sic-codes/?code=2834")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["results"][0]["industry_title"] == "PHARMACEUTICALS"
