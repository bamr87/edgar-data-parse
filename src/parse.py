"""Shim: HTM parsing lives in ``sec_edgar.parsers.htm``."""

from __future__ import annotations

import pandas as pd

from sec_edgar.client import default_headers
from sec_edgar.parsers.htm import parse_sec_htm

headers = default_headers()


def facts_DF(ticker: str, hdrs=None) -> tuple:
    """
    Build a long-format DataFrame from SEC companyfacts (minimal columns).
    """
    from sec_edgar.client import SecEdgarClient

    client = SecEdgarClient()
    info = client.cik_for_ticker(ticker)
    payload = client.company_facts(info["cik"])
    rows = []
    facts_root = (payload or {}).get("facts") or {}
    for taxonomy, concepts in facts_root.items():
        if not isinstance(concepts, dict):
            continue
        for concept, meta in concepts.items():
            if not isinstance(meta, dict):
                continue
            for unit_label, series in (meta.get("units") or {}).items():
                if not isinstance(series, list):
                    continue
                for pt in series:
                    if not isinstance(pt, dict):
                        continue
                    rows.append(
                        {
                            "taxonomy": taxonomy,
                            "concept": concept,
                            "unit": unit_label,
                            "end": pt.get("end"),
                            "val": pt.get("val"),
                            "form": pt.get("form"),
                        }
                    )
    df = pd.DataFrame(rows)
    labels_dict = {"entityName": payload.get("entityName"), "cik": payload.get("cik")}
    return df, labels_dict


def facts_to_csv(facts: dict, filename: str) -> None:
    """Write companyfacts JSON to a simple CSV via facts_DF."""
    import csv

    cik = str(facts.get("cik", ""))
    rows = []
    facts_root = (facts or {}).get("facts") or {}
    for taxonomy, concepts in facts_root.items():
        if not isinstance(concepts, dict):
            continue
        for concept, meta in concepts.items():
            if not isinstance(meta, dict):
                continue
            for unit_label, series in (meta.get("units") or {}).items():
                if not isinstance(series, list):
                    continue
                for pt in series:
                    if isinstance(pt, dict):
                        rows.append(
                            {
                                "taxonomy": taxonomy,
                                "concept": concept,
                                "unit": unit_label,
                                **pt,
                            }
                        )
    if not rows:
        return
    keys = sorted({k for r in rows for k in r})
    with open(filename, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
