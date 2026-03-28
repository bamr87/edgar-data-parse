"""Merge US-GAAP account / label data from data/acct_facts* into reference/generated."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

ACCOUNT_MAP_FILENAME = "us_gaap_account_map.json"
GENERATED_SUBDIR = "generated"


def data_dir_default() -> Path:
    return Path(settings.BASE_DIR).parent / "data"


def reference_dir_default() -> Path:
    return Path(settings.BASE_DIR).parent / "data" / "reference"


def generated_map_path(reference_dir: Path | None = None) -> Path:
    root = reference_dir or reference_dir_default()
    return root / GENERATED_SUBDIR / ACCOUNT_MAP_FILENAME


def _merge_csv(path: Path, merged: dict[str, dict[str, Any]]) -> None:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            c = (row.get("us_gaap_list") or "").strip()
            if not c:
                continue
            rec = merged.setdefault(c, {})
            if row.get("acct_label"):
                rec["label"] = row["acct_label"].strip()
            if row.get("acct_description"):
                rec["description"] = row["acct_description"].strip()


def _merge_json_array(items: list[Any], merged: dict[str, dict[str, Any]]) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        c = item.get("us_gaap_list")
        if not c or not isinstance(c, str):
            continue
        c = c.strip()
        if not c:
            continue
        rec = merged.setdefault(c, {})
        if item.get("acct_label"):
            rec["label"] = str(item["acct_label"]).strip()
        if item.get("acct_description"):
            rec["description"] = str(item["acct_description"]).strip()
        ac = item.get("acct_category")
        if isinstance(ac, str) and ac.strip():
            rec["acct_category"] = ac.strip()


def merge_accounting_sources(data_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """
    Merge ``acct_facts.csv`` → ``acct_facts.json`` → ``acct_facts_updated.json`` (later wins per concept).
    """
    merged: dict[str, dict[str, Any]] = {}
    used: list[str] = []

    csv_path = data_dir / "acct_facts.csv"
    if csv_path.is_file():
        _merge_csv(csv_path, merged)
        used.append("acct_facts.csv")

    for name in ("acct_facts.json", "acct_facts_updated.json"):
        path = data_dir / name
        if not path.is_file():
            continue
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            _merge_json_array(payload, merged)
            used.append(name)
        else:
            logger.warning("Expected JSON array in %s, got %s", path, type(payload).__name__)

    return merged, used


def build_account_map_document(
    by_concept: dict[str, dict[str, Any]], *, sources: list[str]
) -> dict[str, Any]:
    return {
        "meta": {
            "schema_version": 1,
            "taxonomy": "us-gaap",
            "description": "Presentation labels and categories for US-GAAP concepts aligned with EDGAR companyfacts keys.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "concept_count": len(by_concept),
            "sources": sources,
        },
        "by_concept": by_concept,
    }


def sync_accounting_reference_to_disk(
    *,
    data_dir: Path | None = None,
    reference_dir: Path | None = None,
) -> Path:
    dd = data_dir or data_dir_default()
    rd = reference_dir or reference_dir_default()
    by_concept, sources = merge_accounting_sources(dd)
    doc = build_account_map_document(by_concept, sources=sources)
    out = generated_map_path(rd)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info("Wrote %s concepts to %s", len(by_concept), out)
    return out


def accounting_map_from_path(path: Path) -> dict[str, dict[str, Any]] | None:
    """Load ``by_concept`` from a normalized map file, JSON array, or CSV."""
    if not path.is_file():
        return None
    if path.suffix.lower() == ".csv":
        merged: dict[str, dict[str, Any]] = {}
        _merge_csv(path, merged)
        return merged
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "by_concept" in raw and isinstance(raw["by_concept"], dict):
        return dict(raw["by_concept"])
    if isinstance(raw, list):
        merged = {}
        _merge_json_array(raw, merged)
        return merged
    return None


def load_accounting_by_concept_resolved(
    *,
    data_dir: Path | None = None,
    reference_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Prefer merged ``generated/us_gaap_account_map.json``, then fall back to source files under ``data/``.
    """
    dd = data_dir or data_dir_default()
    rd = reference_dir or reference_dir_default()
    for p in (
        generated_map_path(rd),
        dd / "acct_facts_updated.json",
        dd / "acct_facts.json",
        dd / "acct_facts.csv",
    ):
        m = accounting_map_from_path(p)
        if m:
            return m
    return {}
