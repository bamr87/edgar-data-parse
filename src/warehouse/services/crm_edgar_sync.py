"""Rate-limited SEC submissions + facts sync for CRM-matched issuers."""

from __future__ import annotations

import logging
import time
from typing import Any

from django.db import transaction

from sec_edgar.services.company_facts import sync_company_facts_to_db
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company, CrmCompanyRecord

logger = logging.getLogger(__name__)


def _call_sec_with_backoff(fn, /, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RuntimeError as e:
        err = str(e).lower()
        if "429" in err or "rate limit" in err:
            logger.warning("SEC rate signal (%s); sleeping 65s then retry once", e)
            time.sleep(65)
            return fn(*args, **kwargs)
        raise


def _apply_crm_metadata(company: Company, crm: CrmCompanyRecord) -> None:
    if not company.crm_external_key:
        company.crm_external_key = crm.key[:64]
    company.customer_class = crm.customer_class or company.customer_class
    company.customer_type = crm.customer_type or company.customer_type
    company.customer_vertical = crm.vertical or company.customer_vertical
    company.contract_status = crm.contract_status or company.contract_status
    if crm.city:
        company.hq_city = crm.city[:255]
    company.save(
        update_fields=[
            "crm_external_key",
            "customer_class",
            "customer_type",
            "customer_vertical",
            "contract_status",
            "hq_city",
            "updated_at",
        ]
    )


def upsert_company_for_crm(crm: CrmCompanyRecord) -> Company:
    if not crm.sec_cik:
        raise ValueError("CRM row has no sec_cik")
    cik = str(crm.sec_cik).zfill(10)
    company, _ = Company.objects.get_or_create(
        cik=cik,
        defaults={
            "ticker": (crm.sec_ticker or "")[:10] or None,
            "name": (crm.name or crm.contract_name or "Unknown")[:255],
        },
    )
    if crm.sec_ticker and not company.ticker:
        company.ticker = crm.sec_ticker[:10]
        company.save(update_fields=["ticker", "updated_at"])
    _apply_crm_metadata(company, crm)
    crm.matched_company = company
    crm.save(update_fields=["matched_company", "updated_at"])
    return company


def sync_crm_matched_edgar(
    *,
    user_agent_email: str | None,
    delay_seconds: float = 0.25,
    delay_after_facts_seconds: float = 0.35,
    limit: int | None = None,
    skip_facts: bool = False,
    start_after_pk: int = 0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    For each CrmCompanyRecord with ``sec_cik``, upsert Company and pull SEC submissions
    (and optionally company facts). Sleeps ``delay_seconds`` between HTTP-heavy steps to
    stay below SEC informal rate guidance (~10 req/s); default is conservative.
    """
    qs = (
        CrmCompanyRecord.objects.exclude(sec_cik__isnull=True)
        .exclude(sec_cik="")
        .filter(match_status="exact")
        .order_by("pk")
    )
    if start_after_pk:
        qs = qs.filter(pk__gt=start_after_pk)
    if limit is not None:
        qs = qs[:limit]

    processed = 0
    submissions_rows = 0
    facts_rows = 0
    errors: list[str] = []

    for crm in qs.iterator():
        try:
            if dry_run:
                logger.info("dry-run would sync %s CIK %s", crm.key, crm.sec_cik)
                processed += 1
                continue
            with transaction.atomic():
                company = upsert_company_for_crm(crm)
            n_sub = _call_sec_with_backoff(
                sync_submissions_for_company,
                company,
                user_agent_email=user_agent_email,
            )
            submissions_rows += n_sub
            time.sleep(delay_seconds)
            n_facts = 0
            if not skip_facts:
                n_facts = _call_sec_with_backoff(
                    sync_company_facts_to_db,
                    company,
                    user_agent_email=user_agent_email,
                )
                facts_rows += n_facts
                time.sleep(delay_after_facts_seconds)
            else:
                time.sleep(delay_seconds)
            processed += 1
            logger.info(
                "Synced EDGAR for %s CIK=%s filings_index_rows=%s facts_rows=%s",
                crm.key,
                company.cik,
                n_sub,
                n_facts,
            )
        except Exception as e:
            msg = f"{crm.key} CIK {crm.sec_cik}: {e}"
            logger.exception("EDGAR sync failed for %s", crm.key)
            errors.append(msg[:500])
            time.sleep(max(delay_seconds, 1.0))

    return {
        "processed": processed,
        "submissions_index_rows_touched": submissions_rows,
        "facts_rows_loaded": facts_rows,
        "errors": errors[:50],
        "error_count": len(errors),
    }
