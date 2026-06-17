"""Read-side analytics over normalized ``Fact`` rows (no live SEC calls)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Max, QuerySet

from warehouse.models import Company, Fact, PeerGroup


class EdgarAnalyticsService:
    @staticmethod
    def latest_by_concepts(
        company: Company,
        concepts: list[str],
        *,
        taxonomy: str = "us-gaap",
    ) -> dict[str, dict[str, Any]]:
        """For each concept, the fact row with max ``period_end`` (one row per concept)."""
        qs: QuerySet[Fact] = Fact.objects.filter(
            company=company, taxonomy=taxonomy, concept__in=concepts
        )
        out: dict[str, dict[str, Any]] = {}
        for concept in concepts:
            row = (
                qs.filter(concept=concept)
                .order_by("-period_end", "-id")
                .values("concept", "period_end", "period_start", "value", "unit", "dimensions")
                .first()
            )
            if row:
                val = row.get("value")
                out[concept] = {
                    "concept": row["concept"],
                    "period_end": row["period_end"].isoformat() if row["period_end"] else None,
                    "period_start": row["period_start"].isoformat() if row["period_start"] else None,
                    "value": float(val) if val is not None else None,
                    "unit": row.get("unit"),
                    "dimensions": row.get("dimensions") or {},
                }
        return out

    @staticmethod
    def timeseries_for_concept(
        company: Company,
        concept: str,
        *,
        taxonomy: str = "us-gaap",
        limit: int = 80,
    ) -> list[dict[str, Any]]:
        rows = (
            Fact.objects.filter(company=company, taxonomy=taxonomy, concept=concept)
            .order_by("-period_end", "-id")[:limit]
        )
        return [
            {
                "period_end": f.period_end.isoformat() if f.period_end else None,
                "period_start": f.period_start.isoformat() if f.period_start else None,
                "value": float(f.value) if f.value is not None else None,
                "unit": f.unit,
                "dimensions": f.dimensions,
            }
            for f in rows
        ]

    @staticmethod
    def timeseries_for_concepts(
        company: Company,
        concepts: list[str],
        *,
        taxonomy: str = "us-gaap",
        limit: int = 80,
        annual_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Time series resolved across a *priority chain* of concepts.

        Companies migrate XBRL tags over time (e.g. ``Revenues`` →
        ``RevenueFromContractWithCustomerExcludingAssessedTax`` under ASC 606), so a
        single literal tag yields a series that ends when the company switched tags.
        For each ``period_end`` this picks the value from the highest-priority concept
        that reported it, producing a continuous series across the tag history.

        ``annual_only`` drops sub-annual *durational* facts (keeps the ~full-year
        value per fiscal year); instant/point-in-time facts (no ``period_start``,
        e.g. balance-sheet items) always pass through.
        """
        priority = {c: i for i, c in enumerate(concepts)}
        chosen: dict[date, tuple[int, Fact]] = {}
        for f in (
            Fact.objects.filter(company=company, taxonomy=taxonomy, concept__in=concepts)
            .order_by("-period_end", "-id")
        ):
            if f.period_end is None or f.value is None:
                continue
            if annual_only and f.period_start is not None and (f.period_end - f.period_start).days < 300:
                continue
            pr = priority.get(f.concept, len(concepts))
            current = chosen.get(f.period_end)
            if current is None or pr < current[0]:
                chosen[f.period_end] = (pr, f)
        ordered = sorted(chosen.values(), key=lambda t: t[1].period_end, reverse=True)[:limit]
        return [
            {
                "period_end": f.period_end.isoformat() if f.period_end else None,
                "period_start": f.period_start.isoformat() if f.period_start else None,
                "value": float(f.value) if f.value is not None else None,
                "unit": f.unit,
                "concept": f.concept,
                "dimensions": f.dimensions,
            }
            for _pr, f in ordered
        ]

    @staticmethod
    def peer_group_latest_for_concept(
        peer_group: PeerGroup,
        concept: str,
        *,
        taxonomy: str = "us-gaap",
    ) -> list[dict[str, Any]]:
        company_ids = list(
            peer_group.memberships.values_list("company_id", flat=True).distinct()
        )
        if not company_ids:
            return []
        latest = (
            Fact.objects.filter(
                company_id__in=company_ids,
                taxonomy=taxonomy,
                concept=concept,
            )
            .values("company_id")
            .annotate(max_end=Max("period_end"))
        )
        by_company_end: dict[int, date | None] = {
            row["company_id"]: row["max_end"] for row in latest
        }
        out: list[dict[str, Any]] = []
        for cid, max_end in by_company_end.items():
            if max_end is None:
                continue
            f = (
                Fact.objects.filter(
                    company_id=cid,
                    taxonomy=taxonomy,
                    concept=concept,
                    period_end=max_end,
                )
                .order_by("-id")
                .first()
            )
            if f and f.value is not None:
                out.append(
                    {
                        "company_id": cid,
                        "period_end": max_end.isoformat(),
                        "value": float(f.value),
                        "unit": f.unit,
                    }
                )
        out.sort(key=lambda r: r["company_id"])
        return out
