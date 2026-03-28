from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from sec_edgar.services.reference_from_edgar import (
    build_taxonomies_document,
    enrich_financial_model_from_edgar,
    generate_reference_bundle,
    iter_unique_concept_tags,
    merge_edgar_api_schema,
    observed_fact_point_keys,
    observed_taxonomy_ids,
)


def test_observed_taxonomy_ids() -> None:
    doc = {"facts": {"us-gaap": {"Assets": {}}, "dei": {"EntityCentralIndexKey": {}}}}
    assert observed_taxonomy_ids(doc) == {"us-gaap", "dei"}


def test_observed_fact_point_keys() -> None:
    doc = {
        "facts": {
            "us-gaap": {
                "X": {
                    "units": {
                        "USD": [
                            {"end": "2020-01-01", "val": 1, "extra_field": 9},
                            {"start": "2019-01-01", "end": "2019-12-31"},
                        ]
                    }
                }
            }
        }
    }
    keys = observed_fact_point_keys(doc, max_facts=10)
    assert "end" in keys and "val" in keys and "start" in keys and "extra_field" in keys


def test_iter_unique_concept_tags_order() -> None:
    groups = {"a": ["Z", "Y"], "b": ["Y", "X"]}
    pairs = iter_unique_concept_tags(groups)
    assert pairs == [("us-gaap", "Z"), ("us-gaap", "Y"), ("us-gaap", "X")]


def test_build_taxonomies_document() -> None:
    doc = build_taxonomies_document({"us-gaap", "custom-tx"}, source_ciks=["1"])
    assert doc["meta"]["generated_from_edgar"]["source_ciks"] == ["0000000001"]
    ids = [t["id"] for t in doc["taxonomies"]]
    assert ids == ["custom-tx", "us-gaap"]
    assert doc["taxonomies"][-1]["label"] == "US GAAP Financial Reporting Taxonomy"


def test_merge_edgar_api_schema() -> None:
    base = {"meta": {"schema_version": 1}, "company_facts": {}}
    merged = merge_edgar_api_schema(
        base,
        observed_fact_point_keys={"end", "val"},
        submissions_root_keys=["cik", "name"],
        source_ciks_facts=["320193"],
        submissions_sample_cik="320193",
    )
    gen = merged["meta"]["generated_from_edgar"]
    assert gen["observed_fact_point_keys"] == ["end", "val"]
    assert gen["observed_submissions_root_keys"] == ["cik", "name"]


def test_enrich_financial_model_from_edgar_mock() -> None:
    client = MagicMock()
    client.company_concept.return_value = {
        "label": "Revenues",
        "description": "Aggregate revenue.",
    }
    base = {"meta": {"schema_version": 1}, "concept_groups": {"revenue": ["Revenues"]}}
    out = enrich_financial_model_from_edgar(
        base, client, metadata_cik="0000320193", delay_s=0.0
    )
    cat = out["meta"]["generated_from_edgar"]["concept_catalog"]["us-gaap"]["Revenues"]
    assert cat["label"] == "Revenues"
    assert "description" in cat


def test_generate_reference_bundle_writes(tmp_path: Path) -> None:
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "edgar_api_schema.json").write_text('{"meta":{"schema_version":1},"company_facts":{}}\n', encoding="utf-8")
    (ref / "financial_model.json").write_text(
        '{"meta":{"schema_version":1},"concept_groups":{"revenue":["Revenues"]},"derived_kpis":{}}\n',
        encoding="utf-8",
    )

    client = MagicMock()
    client.company_facts.side_effect = [
        {
            "facts": {
                "us-gaap": {
                    "Revenues": {"units": {"USD": [{"end": "2020-01-01", "val": 1, "z_only": True}]}}
                }
            }
        },
    ]
    client.submissions.return_value = {"cik": "1", "name": "Co"}
    client.company_concept.return_value = {"label": "L", "description": "D"}

    generate_reference_bundle(
        ref,
        client,
        sample_ciks=["1"],
        metadata_cik="1",
        delay_s=0.0,
    )

    tax = json.loads((ref / "taxonomies.json").read_text(encoding="utf-8"))
    assert any(t["id"] == "us-gaap" for t in tax["taxonomies"])

    schema = json.loads((ref / "edgar_api_schema.json").read_text(encoding="utf-8"))
    assert "z_only" in schema["meta"]["generated_from_edgar"]["observed_fact_point_keys"]
