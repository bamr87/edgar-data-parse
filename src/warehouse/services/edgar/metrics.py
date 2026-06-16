"""Compute ``DerivedMetric`` rows from normalized ``Fact`` data.

Pure-Python and unit-testable against ``Fact`` fixtures (no SEC calls). KPI
definitions and concept groupings come from ``data/reference/financial_model.json``
via :mod:`sec_edgar.reference_data`. Formulas are evaluated with a small safe AST
walker (arithmetic over group names only — never ``eval``).
"""

from __future__ import annotations

import ast
import logging
import operator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils import timezone

from sec_edgar.reference_data import concept_groups_ordered, derived_kpi_definitions
from warehouse.models import Company, DerivedMetric, Fact

logger = logging.getLogger(__name__)

DEFAULT_TAXONOMY = "us-gaap"
# Provenance stamp on every computed row (consumed by the Phase-9 Company-360 layer).
METRIC_SOURCE = "computed:financial_model"
_QUANT = Decimal("0.000001")

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _safe_eval(formula: str, values: dict[str, Decimal]) -> Decimal | None:
    """Evaluate an arithmetic ``formula`` over ``values`` (group name -> Decimal).

    Supports + - * / and unary minus over names and numeric literals only. Returns
    None on a missing operand or division by zero.
    """

    def _ev(node: ast.AST) -> Decimal | None:
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = _ev(node.left), _ev(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Div) and right == 0:
                return None
            return _BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            val = _ev(node.operand)
            return None if val is None else -val
        if isinstance(node, ast.Name):
            return values.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    try:
        return _ev(ast.parse(formula, mode="eval"))
    except (ValueError, SyntaxError, InvalidOperation, ArithmeticError):
        return None


def resolve_group_facts_by_period(
    company: Company, *, taxonomy: str = DEFAULT_TAXONOMY
) -> dict[date, dict[str, Fact]]:
    """For each period_end, resolve every concept group to a single chosen ``Fact``.

    A group resolves to the highest-preference concept (per the ordered group list)
    that has a fact at that period_end; when a concept has several facts ending on the
    same date, the longest-duration one wins (full-year over quarter; instants are
    unique).
    """
    groups = concept_groups_ordered()
    all_concepts = {c for concepts in groups.values() for c in concepts}
    if not all_concepts:
        return {}

    facts = Fact.objects.filter(
        company=company,
        taxonomy=taxonomy,
        concept__in=all_concepts,
        period_end__isnull=False,
        value__isnull=False,
    )

    # (concept, period_end) -> (chosen Fact, duration_days); keep the longest duration.
    chosen: dict[tuple[str, date], tuple[Fact, int]] = {}
    for f in facts:
        if f.period_end is None:  # filtered out in the query; narrows for the key below
            continue
        duration = (f.period_end - f.period_start).days if f.period_start else -1
        key = (f.concept, f.period_end)
        prev = chosen.get(key)
        if prev is None or duration > prev[1]:
            chosen[key] = (f, duration)

    periods = {pe for (_concept, pe) in chosen}
    out: dict[date, dict[str, Fact]] = {}
    for pe in periods:
        resolved: dict[str, Fact] = {}
        for group, concepts in groups.items():
            for concept in concepts:  # preference order
                hit = chosen.get((concept, pe))
                if hit is not None:
                    resolved[group] = hit[0]
                    break
        out[pe] = resolved
    return out


def _evaluate_kpi(defn: dict[str, Any], group_values: dict[str, Decimal]) -> Decimal | None:
    requires = defn.get("requires") or []
    requires_any = defn.get("requires_any") or []
    if requires and not all(g in group_values for g in requires):
        return None
    values = dict(group_values)
    if requires_any:
        if not any(g in group_values for g in requires_any):
            return None
        # "Uses zero for missing operands when at least one present."
        for g in requires_any:
            values.setdefault(g, Decimal(0))
    formula = defn.get("formula")
    if not formula:
        return None
    result = _safe_eval(formula, values)
    if result is None:
        return None
    try:
        return result.quantize(_QUANT)
    except (InvalidOperation, ArithmeticError):
        return None


@transaction.atomic
def compute_derived_metrics(
    company: Company,
    *,
    taxonomy: str = DEFAULT_TAXONOMY,
    kpi_keys: list[str] | None = None,
) -> int:
    """Compute and upsert ``DerivedMetric`` rows for ``company``; returns rows written.

    Runs in its own transaction. Callers should invoke this AFTER the (separately
    atomic) facts sync has committed, never inside it.
    """
    kpis = derived_kpi_definitions()
    if kpi_keys:
        kpis = {k: v for k, v in kpis.items() if k in kpi_keys}
    facts_by_period = resolve_group_facts_by_period(company, taxonomy=taxonomy)
    now = timezone.now()
    written = 0
    for period_end, resolved in facts_by_period.items():
        group_values = {g: f.value for g, f in resolved.items() if f.value is not None}
        for name, defn in kpis.items():
            value = _evaluate_kpi(defn, group_values)
            if value is None:
                continue
            unit = "ratio" if "/" in (defn.get("formula") or "") else "USD"
            DerivedMetric.objects.update_or_create(
                company=company,
                key=name,
                period_end=period_end,
                defaults={
                    "value": value,
                    "unit": unit,
                    "extra": {
                        "formula": defn.get("formula"),
                        "source": METRIC_SOURCE,
                        "fetched_at": now.isoformat(),
                        "inputs": sorted(group_values.keys()),
                    },
                },
            )
            written += 1
    logger.info("Computed %d derived metrics for company=%s", written, company.cik)
    return written
