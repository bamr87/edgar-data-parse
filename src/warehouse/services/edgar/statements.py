"""Build financial-statement views from normalized ``Fact`` data.

Pure read-side composition (no SEC calls): maps the ordered ``statement_schemas``
line items to the latest resolved fact per concept group, with each value linked to
its source filing accession for auditability.
"""

from __future__ import annotations

from typing import Any

from sec_edgar.reference_data import statement_schemas
from warehouse.models import Company

from .metrics import DEFAULT_TAXONOMY, resolve_group_facts_by_period


def _accession_of(fact) -> str | None:
    dims = fact.dimensions or {}
    return dims.get("accn")


def build_financial_statement(
    company: Company,
    statement_type: str,
    *,
    taxonomy: str = DEFAULT_TAXONOMY,
) -> dict[str, Any]:
    """Return one statement's ordered line items with the latest value per line.

    Raises ``KeyError`` if ``statement_type`` is unknown (callers map to HTTP 400).
    """
    schemas = statement_schemas()
    if statement_type not in schemas:
        raise KeyError(statement_type)

    facts_by_period = resolve_group_facts_by_period(company, taxonomy=taxonomy)
    # Latest period that has any resolved facts.
    latest_period = max(facts_by_period, default=None)
    resolved = facts_by_period.get(latest_period, {}) if latest_period else {}

    line_items = []
    for item in schemas[statement_type]:
        group = item["key"]
        fact = resolved.get(group)
        line_items.append(
            {
                "key": group,
                "label": item.get("label", group),
                "value": float(fact.value) if fact and fact.value is not None else None,
                "unit": fact.unit if fact else None,
                "accession": _accession_of(fact) if fact else None,
            }
        )
    return {
        "company": company.id,
        "statement_type": statement_type,
        "taxonomy": taxonomy,
        "period_end": latest_period.isoformat() if latest_period else None,
        "line_items": line_items,
    }


def available_statement_types() -> list[str]:
    return list(statement_schemas().keys())
