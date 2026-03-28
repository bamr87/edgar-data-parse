"""Build data/reference/*.json content from live SEC EDGAR JSON APIs."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from sec_edgar.client import SecEdgarClient

logger = logging.getLogger(__name__)

# Human-readable rows merged with taxonomy ids observed in companyfacts.
KNOWN_TAXONOMY_META: dict[str, dict[str, str]] = {
    "us-gaap": {
        "label": "US GAAP Financial Reporting Taxonomy",
        "role": "primary_financial_statements",
        "notes": "Most issuer financial statement facts.",
    },
    "dei": {
        "label": "Document and Entity Information",
        "role": "filing_metadata",
        "notes": "Entity identifiers, document period end, shares outstanding context, etc.",
    },
    "ifrs-full": {
        "label": "IFRS Taxonomy",
        "role": "primary_financial_statements",
        "notes": "Used by some foreign private issuers and dual reporters.",
    },
    "srt": {
        "label": "SEC Reporting Taxonomy",
        "role": "schedules_and_supplemental",
        "notes": "Often used for segment, revenue disaggregation, and other supplemental disclosures.",
    },
    "invest": {
        "label": "SEC Investment Taxonomy",
        "role": "investment_companies",
        "notes": "Registered investment companies and similar filers.",
    },
}


def observed_taxonomy_ids(facts_payload: dict[str, Any]) -> set[str]:
    root = facts_payload.get("facts") or {}
    if not isinstance(root, dict):
        return set()
    return {str(k) for k in root.keys()}


def observed_fact_point_keys(
    facts_payload: dict[str, Any], *, max_facts: int = 2000
) -> set[str]:
    keys: set[str] = set()
    n = 0
    facts_root = facts_payload.get("facts") or {}
    if not isinstance(facts_root, dict):
        return keys
    for _tax, concepts in facts_root.items():
        if not isinstance(concepts, dict):
            continue
        for _concept, meta in concepts.items():
            if not isinstance(meta, dict):
                continue
            units = meta.get("units") or {}
            if not isinstance(units, dict):
                continue
            for _unit_label, series in units.items():
                if not isinstance(series, list):
                    continue
                for pt in series:
                    if isinstance(pt, dict):
                        keys.update(pt.keys())
                    n += 1
                    if n >= max_facts:
                        return keys
    return keys


def build_taxonomies_document(
    observed_ids: set[str],
    *,
    source_ciks: list[str],
) -> dict[str, Any]:
    rows = []
    for tid in sorted(observed_ids):
        base = KNOWN_TAXONOMY_META.get(
            tid,
            {
                "label": tid,
                "role": "observed_only",
                "notes": "Present in sampled SEC companyfacts; add KNOWN_TAXONOMY_META entry to describe.",
            },
        )
        rows.append({"id": tid, **base})
    return {
        "meta": {
            "description": "XBRL taxonomy namespaces observed in SEC company facts (merged with project descriptors).",
            "schema_version": 1,
            "generated_from_edgar": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_ciks": [c.zfill(10) for c in source_ciks],
            },
        },
        "taxonomies": rows,
    }


def merge_edgar_api_schema(
    base: dict[str, Any],
    *,
    observed_fact_point_keys: set[str],
    submissions_root_keys: list[str],
    source_ciks_facts: list[str],
    submissions_sample_cik: str,
) -> dict[str, Any]:
    out = json.loads(json.dumps(base))
    out.setdefault("meta", {})
    out["meta"]["generated_from_edgar"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "companyfacts_sample_ciks": [c.zfill(10) for c in source_ciks_facts],
        "submissions_sample_cik": submissions_sample_cik.zfill(10),
        "observed_fact_point_keys": sorted(observed_fact_point_keys),
        "observed_submissions_root_keys": submissions_root_keys,
    }
    return out


def iter_unique_concept_tags(concept_groups: dict[str, Any]) -> list[tuple[str, str]]:
    """(taxonomy, tag) pairs; default taxonomy us-gaap."""
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for _group, tags in (concept_groups or {}).items():
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if not isinstance(tag, str):
                continue
            key = ("us-gaap", tag)
            if key not in seen:
                seen.add(key)
                ordered.append(key)
    return ordered


def enrich_financial_model_from_edgar(
    base: dict[str, Any],
    client: SecEdgarClient,
    *,
    metadata_cik: str,
    delay_s: float = 0.12,
) -> dict[str, Any]:
    """Attach concept_catalog (label, description) from companyconcept for tags in concept_groups."""
    out = json.loads(json.dumps(base))
    meta = out.setdefault("meta", {})
    meta.pop("generated_from_edgar", None)

    groups = out.get("concept_groups") or {}
    catalog: dict[str, dict[str, dict[str, str]]] = {}
    cik = metadata_cik.zfill(10)
    for taxonomy, tag in iter_unique_concept_tags(groups):
        try:
            payload = client.company_concept(cik, taxonomy, tag)
        except requests.RequestException as e:
            logger.warning("companyconcept skip %s/%s: %s", taxonomy, tag, e)
            time.sleep(delay_s)
            continue
        label = payload.get("label")
        desc = payload.get("description")
        if label or desc:
            catalog.setdefault(taxonomy, {})[tag] = {
                k: v
                for k, v in (("label", label), ("description", desc))
                if isinstance(v, str) and v.strip()
            }
        time.sleep(delay_s)

    meta["generated_from_edgar"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata_source_cik": cik,
        "concept_catalog": catalog,
    }
    return out


def load_json_path(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json_path(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def generate_reference_bundle(
    reference_dir: Path,
    client: SecEdgarClient,
    *,
    sample_ciks: list[str],
    metadata_cik: str,
    delay_s: float = 0.12,
) -> None:
    """
    Refresh reference JSON under ``reference_dir`` using SEC APIs.

    - taxonomies.json — union of taxonomy keys from companyfacts for each sample CIK.
    - edgar_api_schema.json — preserves existing doc; adds meta.generated_from_edgar observations.
    - financial_model.json — preserves concept_groups / derived_kpis; adds concept_catalog from companyconcept.
    """
    sample_ciks = [c.zfill(10) for c in sample_ciks]
    meta_cik = metadata_cik.zfill(10)

    schema_path = reference_dir / "edgar_api_schema.json"
    fm_path = reference_dir / "financial_model.json"
    base_schema = load_json_path(schema_path)
    fm_base = load_json_path(fm_path)

    observed_tax: set[str] = set()
    observed_keys: set[str] = set()
    for cik in sample_ciks:
        doc = client.company_facts(cik)
        observed_tax |= observed_taxonomy_ids(doc)
        observed_keys |= observed_fact_point_keys(doc)
        time.sleep(delay_s)

    submissions = client.submissions(meta_cik)
    sub_keys = sorted(submissions.keys()) if isinstance(submissions, dict) else []
    time.sleep(delay_s)

    tax_path = reference_dir / "taxonomies.json"
    write_json_path(
        tax_path,
        build_taxonomies_document(observed_tax, source_ciks=sample_ciks),
    )

    write_json_path(
        schema_path,
        merge_edgar_api_schema(
            base_schema,
            observed_fact_point_keys=observed_keys,
            submissions_root_keys=sub_keys,
            source_ciks_facts=sample_ciks,
            submissions_sample_cik=meta_cik,
        ),
    )

    write_json_path(
        fm_path,
        enrich_financial_model_from_edgar(
            fm_base,
            client,
            metadata_cik=meta_cik,
            delay_s=delay_s,
        ),
    )
