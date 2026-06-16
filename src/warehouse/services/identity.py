"""Canonical company identity / entity resolution across sources.

Consolidates a Company's known identifiers (CIK, ticker, CRM key) into
``ExternalIdentifier`` rows so one company is joinable from any source. The CRM
title-match flow (``crm_sec_match``) is the upstream that links CRM rows to CIKs.
"""

from __future__ import annotations

from warehouse.models import Company, ExternalIdentifier


def index_company_identifiers(company: Company) -> int:
    """Upsert ExternalIdentifier rows for a company's known ids; returns the count."""
    pairs: list[tuple[str, str, float]] = []
    if company.cik:
        pairs.append(("cik", company.cik, 1.0))
    if company.ticker:
        pairs.append(("ticker", company.ticker.upper(), 1.0))
    if company.crm_external_key:
        pairs.append(("crm", company.crm_external_key, 0.9))

    count = 0
    for system, value, confidence in pairs:
        ExternalIdentifier.objects.update_or_create(
            system=system,
            value=value,
            defaults={"company": company, "confidence": confidence},
        )
        count += 1
    return count


def resolve_company(system: str, value: str) -> Company | None:
    """Resolve a Company by any registered external identifier."""
    if system == "ticker":
        value = value.upper()
    ident = (
        ExternalIdentifier.objects.filter(system=system, value=value)
        .select_related("company")
        .first()
    )
    return ident.company if ident else None
