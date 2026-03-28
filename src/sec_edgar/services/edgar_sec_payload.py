"""Persist and reuse raw SEC API JSON (submissions, companyfacts) — database first, then SEC."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from sec_edgar.adapters.direct import DirectEdgarAdapter
from warehouse.models import EdgarSecPayload

logger = logging.getLogger(__name__)


def save_edgar_sec_payload(cik: str, kind: str, payload: dict[str, Any]) -> None:
    """Store or replace JSON from bulk ZIP or after a live fetch."""
    cik = cik.zfill(10)
    EdgarSecPayload.objects.update_or_create(
        cik=cik,
        kind=kind,
        defaults={"payload": payload, "fetched_at": timezone.now()},
    )


def get_submissions_payload(
    cik: str,
    *,
    user_agent_email: str | None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Return SEC submissions JSON: Postgres row if present, else data.sec.gov, then save."""
    cik = cik.zfill(10)
    if not force_refresh:
        row = EdgarSecPayload.objects.filter(
            cik=cik, kind=EdgarSecPayload.Kind.SUBMISSIONS
        ).first()
        if row:
            return row.payload
    data = DirectEdgarAdapter(user_agent_email=user_agent_email).submissions(cik)
    save_edgar_sec_payload(cik, EdgarSecPayload.Kind.SUBMISSIONS, data)
    logger.debug("Fetched submissions from SEC for CIK %s", cik)
    return data


def get_company_facts_payload(
    cik: str,
    *,
    user_agent_email: str | None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Return SEC companyfacts JSON: Postgres first, else SEC API, then save."""
    cik = cik.zfill(10)
    if not force_refresh:
        row = EdgarSecPayload.objects.filter(
            cik=cik, kind=EdgarSecPayload.Kind.COMPANY_FACTS
        ).first()
        if row:
            return row.payload
    data = DirectEdgarAdapter(user_agent_email=user_agent_email).company_facts(cik)
    save_edgar_sec_payload(cik, EdgarSecPayload.Kind.COMPANY_FACTS, data)
    logger.debug("Fetched company facts from SEC for CIK %s", cik)
    return data
