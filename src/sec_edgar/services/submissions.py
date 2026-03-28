"""Sync SEC submissions index into warehouse Filing rows (metadata)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from sec_edgar.services.edgar_sec_payload import get_submissions_payload, save_edgar_sec_payload
from sec_edgar.services.sic_reference import industry_title_for_code
from warehouse.models import Company, EdgarEntitySyncState, EdgarSecPayload, Filing

logger = logging.getLogger(__name__)


def _touch_submissions_synced(company: Company) -> None:
    state, _ = EdgarEntitySyncState.objects.get_or_create(company=company)
    state.submissions_synced_at = timezone.now()
    state.last_error = ""
    state.save(update_fields=["submissions_synced_at", "last_error", "updated_at"])


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@transaction.atomic
def sync_submissions_for_company(
    company: Company,
    payload: dict[str, Any] | None = None,
    *,
    user_agent_email: str | None = None,
    force_refresh: bool = False,
) -> int:
    cik = company.cik.zfill(10)
    if payload is None:
        payload = get_submissions_payload(
            cik, user_agent_email=user_agent_email, force_refresh=force_refresh
        )
    else:
        save_edgar_sec_payload(cik, EdgarSecPayload.Kind.SUBMISSIONS, payload)

    # Enrich company from submissions
    fields_to_update: list[str] = []
    sic = payload.get("sic")
    if sic:
        company.sic_code = str(sic)[:10]
        fields_to_update.append("sic_code")
    sic_desc = payload.get("sicDescription")
    if sic_desc:
        company.sic_description = str(sic_desc)[:255]
        fields_to_update.append("sic_description")
    elif company.sic_code and not (company.sic_description or "").strip():
        ref_title = industry_title_for_code(company.sic_code)
        if ref_title:
            company.sic_description = ref_title[:255]
            fields_to_update.append("sic_description")
    if payload.get("name") and not company.name:
        company.name = str(payload["name"])[:255]
        fields_to_update.append("name")
    if fields_to_update:
        fields_to_update.append("updated_at")
        company.save(update_fields=fields_to_update)

    recent = payload.get("filings", {}).get("recent", {})
    if not recent:
        _touch_submissions_synced(company)
        return 0

    forms = recent.get("form") or []
    accessions = recent.get("accessionNumber") or []
    filing_dates = recent.get("filingDate") or []
    report_dates = recent.get("reportDate") or []
    primary_docs = recent.get("primaryDocument") or []

    created = 0
    n = min(len(accessions), len(forms)) if accessions else 0
    for i in range(n):
        acc = accessions[i]
        if not acc:
            continue
        form = forms[i] if i < len(forms) else "UNKNOWN"
        fdate = _parse_date(filing_dates[i] if i < len(filing_dates) else None)
        pdate = _parse_date(report_dates[i] if i < len(report_dates) else None)
        primary = primary_docs[i] if i < len(primary_docs) else ""
        meta: dict[str, Any] = {}
        if primary:
            meta["primaryDocument"] = primary

        _, was_created = Filing.objects.update_or_create(
            company=company,
            accession_number=str(acc)[:30],
            defaults={
                "form_type": str(form)[:20],
                "filing_date": fdate,
                "period_of_report": pdate,
                "url": None,
                "local_path": None,
                "metadata": meta,
            },
        )
        if was_created:
            created += 1
    _touch_submissions_synced(company)
    return n
