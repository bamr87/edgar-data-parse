from __future__ import annotations

import json
from pathlib import Path

import pytest

from sec_edgar.services.accounting_reference import (
    OVERLAY_JSON,
    accounting_map_from_path,
    merge_accounting_sources,
    sync_accounting_reference_to_disk,
)


def test_merge_order_overlay_overrides_csv(tmp_path: Path) -> None:
    sd = tmp_path / "sources" / "accounting"
    sd.mkdir(parents=True)
    (sd / "acct_facts.csv").write_text(
        "us_gaap_list,acct_label,acct_description\n"
        "Foo,FromCSV,DescCSV\n",
        encoding="utf-8",
    )
    (sd / OVERLAY_JSON).write_text(
        json.dumps(
            [
                {
                    "us_gaap_list": "Foo",
                    "acct_label": "FromOverlay",
                    "acct_description": "DescOverlay",
                }
            ]
        ),
        encoding="utf-8",
    )
    merged, used = merge_accounting_sources(sd)
    assert used == ["acct_facts.csv", OVERLAY_JSON]
    assert merged["Foo"]["label"] == "FromOverlay"
    assert merged["Foo"]["description"] == "DescOverlay"


def test_merge_overlay_adds_category(tmp_path: Path) -> None:
    sd = tmp_path / "sources" / "accounting"
    sd.mkdir(parents=True)
    (sd / "acct_facts.csv").write_text(
        "us_gaap_list,acct_label,acct_description\nFoo,CSV,DC\n", encoding="utf-8"
    )
    (sd / OVERLAY_JSON).write_text(
        json.dumps(
            [
                {
                    "us_gaap_list": "Foo",
                    "acct_label": "UPD",
                    "acct_description": "DU",
                    "acct_category": "liability",
                }
            ]
        ),
        encoding="utf-8",
    )
    merged, _ = merge_accounting_sources(sd)
    assert merged["Foo"]["label"] == "UPD"
    assert merged["Foo"]["acct_category"] == "liability"


def test_sync_writes_normalized_doc(tmp_path: Path) -> None:
    sd = tmp_path / "sources" / "accounting"
    sd.mkdir(parents=True)
    (sd / OVERLAY_JSON).write_text(
        json.dumps(
            [{"us_gaap_list": "Bar", "acct_label": "L", "acct_description": "D", "acct_category": "asset"}]
        ),
        encoding="utf-8",
    )
    ref = tmp_path / "reference"
    ref.mkdir()
    out = sync_accounting_reference_to_disk(accounting_sources_dir=sd, reference_dir=ref)
    assert out.name == "us_gaap_account_map.json"
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["meta"]["concept_count"] == 1
    assert raw["by_concept"]["Bar"]["acct_category"] == "asset"


def test_accounting_map_from_path_by_concept_file(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({"by_concept": {"X": {"label": "lx"}}}),
        encoding="utf-8",
    )
    m = accounting_map_from_path(p)
    assert m == {"X": {"label": "lx"}}


@pytest.mark.django_db
def test_reference_data_load_accounting_by_concept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sec_edgar.services.accounting_reference as ar
    from sec_edgar import reference_data as rd

    sd = tmp_path / "sources" / "accounting"
    sd.mkdir(parents=True)
    (sd / OVERLAY_JSON).write_text(
        json.dumps([{"us_gaap_list": "Zed", "acct_label": "ZLabel", "acct_description": ""}]),
        encoding="utf-8",
    )
    ref = tmp_path / "reference"
    ref.mkdir()

    monkeypatch.setattr(ar, "reference_dir_default", lambda: ref)
    monkeypatch.setattr(ar, "accounting_sources_dir_default", lambda: sd)
    rd.load_accounting_by_concept.cache_clear()
    m = rd.load_accounting_by_concept()
    assert m["Zed"]["label"] == "ZLabel"
