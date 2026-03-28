"""Ingest SEC companyfacts JSON into warehouse.Fact rows."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils import timezone

from sec_edgar.adapters.direct import DirectEdgarAdapter
from sec_edgar.services.edgar_sec_payload import get_company_facts_payload, save_edgar_sec_payload
from warehouse.models import Company, EdgarEntitySyncState, EdgarSecPayload, Fact

logger = logging.getLogger(__name__)


def _touch_facts_synced(company: Company) -> None:
    state, _ = EdgarEntitySyncState.objects.get_or_create(company=company)
    state.facts_synced_at = timezone.now()
    state.last_error = ""
    state.save(update_fields=["facts_synced_at", "last_error", "updated_at"])


def _parse_us_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _to_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


@transaction.atomic
def sync_company_facts_to_db(
    company: Company,
    facts_payload: dict[str, Any] | None = None,
    *,
    user_agent_email: str | None = None,
    force_refresh: bool = False,
) -> int:
    """Replace facts for company from SEC companyfacts payload."""
    cik = company.cik.zfill(10)
    if facts_payload is None:
        facts_payload = get_company_facts_payload(
            cik, user_agent_email=user_agent_email, force_refresh=force_refresh
        )
    else:
        save_edgar_sec_payload(cik, EdgarSecPayload.Kind.COMPANY_FACTS, facts_payload)

    cik_from_api = str(facts_payload.get("cik", "")).zfill(10)
    if cik_from_api != cik:
        logger.warning("CIK mismatch payload %s vs company %s", cik_from_api, cik)

    entity_name = (facts_payload.get("entityName") or company.name)[:255]
    if entity_name and company.name != entity_name:
        company.name = entity_name
        company.save(update_fields=["name", "updated_at"])

    facts_root = facts_payload.get("facts") or {}
    rows: list[Fact] = []
    for taxonomy, concepts in facts_root.items():
        if not isinstance(concepts, dict):
            continue
        for concept, meta in concepts.items():
            if not isinstance(meta, dict):
                continue
            units = meta.get("units") or {}
            if not isinstance(units, dict):
                continue
            for unit_label, series in units.items():
                if not isinstance(series, list):
                    continue
                for pt in series:
                    if not isinstance(pt, dict):
                        continue
                    end = _parse_us_date(pt.get("end"))
                    start = _parse_us_date(pt.get("start"))
                    val = _to_decimal(pt.get("val"))
                    if val is None:
                        continue
                    dim = {
                        "unit": unit_label,
                        "form": pt.get("form"),
                        "filed": pt.get("filed"),
                        "frame": pt.get("frame"),
                        "accn": pt.get("accn"),
                    }
                    rows.append(
                        Fact(
                            company=company,
                            taxonomy=str(taxonomy)[:100],
                            concept=str(concept)[:255],
                            period_start=start,
                            period_end=end,
                            unit=str(unit_label)[:50] if unit_label else None,
                            value=val,
                            dimensions={k: v for k, v in dim.items() if v is not None},
                        )
                    )

    Fact.objects.filter(company=company).delete()
    Fact.objects.bulk_create(rows, batch_size=1000)
    _touch_facts_synced(company)
    return len(rows)


def sync_company_facts_by_ticker(ticker: str) -> tuple[Company, int]:
    ad = DirectEdgarAdapter()
    info = ad.cik_for_ticker(ticker)
    company, _ = Company.objects.get_or_create(
        cik=info["cik"],
        defaults={"ticker": ticker.upper(), "name": info["name"]},
    )
    n = sync_company_facts_to_db(company)
    return company, n
