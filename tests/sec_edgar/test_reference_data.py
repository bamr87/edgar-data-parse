from __future__ import annotations

from sec_edgar.reference_data import concept_group_frozensets, load_reference_json, reference_root


def test_reference_root_exists() -> None:
    root = reference_root()
    assert root.is_dir()
    assert (root / "financial_model.json").is_file()


def test_financial_model_concept_groups() -> None:
    g = concept_group_frozensets()
    assert "revenue" in g
    assert "Revenues" in g["revenue"]
    assert "CostOfRevenue" in g["cost_of_revenue"]


def test_load_edgar_api_schema() -> None:
    doc = load_reference_json("edgar_api_schema.json")
    assert doc["meta"]["schema_version"] == 1
    assert "fact_point" in doc["company_facts"]
