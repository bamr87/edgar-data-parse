"""Transparent 'stakeholder orientation' analysis — the people-vs-profits signal.

A HEURISTIC over public XBRL facts: does a company's capital allocation lean toward
reinvestment in the business (capex, R&D — proxies for building/people/local capacity)
or toward shareholder payout (buybacks, dividends)? Every signal is disclosed with its
source concept and period. This is a model of *company behavior over a period*, NOT a
personal approval rating, a character judgment of any executive, an endorsement, or
investment/HR advice. Real outsourcing/offshoring is NOT directly observable from XBRL;
``capex_intensity`` is only a *local-investment proxy* (see the per-signal note).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction

from warehouse.models import Company, LeadershipPosition, StakeholderAssessment

METHOD_VERSION = "1.0"

CAVEATS = (
    "Heuristic model over public SEC XBRL facts. Signals describe capital allocation "
    "during the period, not the character, competence, or 'approval' of any individual. "
    "capex_intensity is a proxy for physical/local investment, NOT a direct measure of "
    "outsourcing/offshoring (which XBRL does not disclose). Verify against the original "
    "filings. Not investment, financial, or HR advice."
)

# Concept preference lists (us-gaap local names).
_OCF = ["NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
_CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsForCapitalImprovements"]
_RND = ["ResearchAndDevelopmentExpense"]
_BUYBACK = ["PaymentsForRepurchaseOfCommonStock"]
_DIVIDEND = ["PaymentsOfDividendsCommon", "PaymentsOfDividends"]
_REVENUE = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"]


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _latest_annual(company: Company, concepts: list[str], taxonomy: str):
    """Return (value, period_end, concept) for the latest annual (~full-year) fact."""
    from warehouse.models import Fact

    for concept in concepts:
        for f in (
            Fact.objects.filter(
                company=company, taxonomy=taxonomy, concept=concept,
                period_end__isnull=False, period_start__isnull=False, value__isnull=False,
            ).order_by("-period_end")
        ):
            if f.period_end is None or f.period_start is None or f.value is None:
                continue  # excluded by the query filters; narrows the types below
            if (f.period_end - f.period_start).days >= 300:
                return float(f.value), f.period_end, concept
    return None, None, None


def _input(concept, period_end, value):
    return {
        "concept": concept,
        "period_end": period_end.isoformat() if isinstance(period_end, date) else period_end,
        "value": value,
    }


def compute_stakeholder_assessment(
    company: Company, *, taxonomy: str = "us-gaap", persist: bool = True
) -> dict[str, Any]:
    """Compute the orientation index + decomposed signals for a company."""
    capex, capex_pe, capex_c = _latest_annual(company, _CAPEX, taxonomy)
    rnd, rnd_pe, rnd_c = _latest_annual(company, _RND, taxonomy)
    buyback, bb_pe, bb_c = _latest_annual(company, _BUYBACK, taxonomy)
    dividend, dv_pe, dv_c = _latest_annual(company, _DIVIDEND, taxonomy)
    revenue, rev_pe, rev_c = _latest_annual(company, _REVENUE, taxonomy)

    signals: list[dict[str, Any]] = []

    # 1. Allocation balance: reinvestment (capex + R&D) vs payout (buybacks + dividends).
    reinvest = (capex or 0.0) + (rnd or 0.0)
    payout = (buyback or 0.0) + (dividend or 0.0)
    if reinvest + payout > 0:
        ratio = (reinvest - payout) / (reinvest + payout)  # -1 payout .. +1 reinvest
        inputs = []
        if capex is not None:
            inputs.append(_input(capex_c, capex_pe, capex))
        if rnd is not None:
            inputs.append(_input(rnd_c, rnd_pe, rnd))
        if buyback is not None:
            inputs.append(_input(bb_c, bb_pe, buyback))
        if dividend is not None:
            inputs.append(_input(dv_c, dv_pe, dividend))
        signals.append({
            "name": "allocation_balance", "label": "Reinvestment vs. shareholder payout",
            "value": round(ratio, 4), "score": round(ratio, 4), "weight": 0.40,
            "inputs": inputs,
            "note": "+1 = all reinvested (capex+R&D); -1 = all paid to shareholders (buybacks+dividends).",
        })

    # 2. Capex intensity (local/physical-investment PROXY).
    if capex is not None and revenue:
        intensity = capex / revenue
        score = _clamp((intensity - 0.05) / 0.05)
        signals.append({
            "name": "capex_intensity", "label": "Capex intensity (local-investment proxy)",
            "value": round(intensity, 4), "score": round(score, 4), "weight": 0.25,
            "inputs": [_input(capex_c, capex_pe, capex), _input(rev_c, rev_pe, revenue)],
            "note": "Proxy for building physical/local capacity. NOT a direct outsourcing measure.",
        })

    # 3. R&D intensity (capability/people investment).
    if rnd is not None and revenue:
        intensity = rnd / revenue
        score = _clamp((intensity - 0.05) / 0.10)
        signals.append({
            "name": "rnd_intensity", "label": "R&D intensity",
            "value": round(intensity, 4), "score": round(score, 4), "weight": 0.20,
            "inputs": [_input(rnd_c, rnd_pe, rnd), _input(rev_c, rev_pe, revenue)],
            "note": "R&D / revenue — investment in capability and people.",
        })

    # 4. Insider alignment (net Form 4 buying(+)/selling(-) across leadership).
    net_shares = float(
        sum(p.net_insider_shares for p in LeadershipPosition.objects.filter(company=company))
    )
    if net_shares != 0.0:
        score = 0.5 if net_shares > 0 else -0.5
        signals.append({
            "name": "insider_alignment", "label": "Insider alignment (net buy/sell)",
            "value": round(net_shares, 2), "score": score, "weight": 0.15,
            "inputs": [{"concept": "sec_form4_net_shares", "period_end": None, "value": round(net_shares, 2)}],
            "note": "Directional 'skin in the game' signal from insider transactions.",
        })

    # Weighted index over available signals.
    total_w = sum(s["weight"] for s in signals)
    index = round(sum(s["score"] * s["weight"] for s in signals) / total_w, 4) if total_w else None

    if index is None:
        label = "Insufficient data"
    elif index >= 0.33:
        label = "Reinvestment / stakeholder-tilted"
    elif index <= -0.33:
        label = "Payout / shareholder-tilted"
    else:
        label = "Balanced"

    period_end = max([pe for pe in (capex_pe, rnd_pe, bb_pe, dv_pe, rev_pe) if pe], default=None)
    result = {
        "company": company.id,
        "period_end": period_end.isoformat() if period_end else None,
        "orientation_index": index,
        "label": label,
        "signals": signals,
        "method_version": METHOD_VERSION,
        "caveats": CAVEATS,
    }

    if persist and period_end:
        with transaction.atomic():
            StakeholderAssessment.objects.update_or_create(
                company=company, period_end=period_end, method_version=METHOD_VERSION,
                defaults={
                    "orientation_index": index, "label": label, "signals": signals,
                    "caveats": CAVEATS,
                },
            )
    return result
