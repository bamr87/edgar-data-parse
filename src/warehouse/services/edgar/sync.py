"""Orchestrate EDGAR resolution and sync (warehouse + SEC) for APIs and jobs."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from sec_edgar.adapters.direct import DirectEdgarAdapter
from sec_edgar.cik import normalize_cik
from sec_edgar.exceptions import EdgarResolutionError
from sec_edgar.services.bulk_company_tickers import sync_companies_from_sec_company_tickers
from sec_edgar.services.company_facts import sync_company_facts_to_db
from sec_edgar.services.company_tickers_catalog import search_company_tickers
from sec_edgar.services.ingest_htm import ingest_htm_filing
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company, Filing, ListedIssuer
from warehouse.services.edgar.listed_issuers import sync_listed_issuers_from_remote


class EdgarSyncService:
    """Domain-orchestration facade for EDGAR operations.

    This is the single entry point the API and management commands should use for
    EDGAR work. It composes the lower ``sec_edgar.services.*`` I/O tier (SEC HTTP +
    payload caching) into warehouse-aware operations. Callers outside this package
    should import from here rather than reaching into ``sec_edgar.services`` directly
    (the one documented exception is reference-data lookups such as SIC codes).
    """

    @staticmethod
    def resolve_edgar_identity(
        *,
        ticker: str | None,
        cik_raw: str | None,
        name_override: str | None,
        user_agent_email: str | None,
    ) -> tuple[str, str, str | None]:
        """
        Return (cik_padded, display_name, ticker_or_none) using DB directory first,
        then full directory refresh, then per-ticker SEC lookup as last resort.
        """
        from sec_edgar.services.company_tickers_catalog import _ensure_listed_issuers_materialized

        t_upper = ticker.strip().upper() if ticker else None
        _ensure_listed_issuers_materialized(user_agent_email=user_agent_email, force_refresh=False)

        li: ListedIssuer | None = None
        if t_upper:
            li = ListedIssuer.objects.filter(ticker=t_upper).first()
        norm: str | None = None
        if li is None and cik_raw is not None:
            try:
                norm = normalize_cik(cik_raw)
            except ValueError:
                norm = None
            if norm is not None:
                li = ListedIssuer.objects.filter(cik=norm).first()

        if li is None:
            sync_listed_issuers_from_remote(user_agent_email=user_agent_email)
            if t_upper:
                li = ListedIssuer.objects.filter(ticker=t_upper).first()
            if li is None and norm is not None:
                li = ListedIssuer.objects.filter(cik=norm).first()

        if li is None and t_upper:
            ad = DirectEdgarAdapter(user_agent_email=user_agent_email)
            info = ad.cik_for_ticker(t_upper)
            cik = info["cik"]
            name = (name_override or info["name"])[:255]
            ListedIssuer.objects.update_or_create(
                cik=cik,
                defaults={
                    "ticker": t_upper,
                    "name": name,
                    "synced_at": timezone.now(),
                },
            )
            return cik, name, t_upper

        if li is None:
            raise EdgarResolutionError("Could not resolve issuer from EDGAR directory")

        name = (name_override or li.name)[:255]
        return li.cik, name, li.ticker or t_upper

    @staticmethod
    def get_or_create_company_from_edgar(
        *,
        ticker: str | None,
        cik_raw: str | None,
        name_override: str | None,
        user_agent_email: str | None,
    ) -> tuple[Company, bool]:
        cik, name, ticker_out = EdgarSyncService.resolve_edgar_identity(
            ticker=ticker,
            cik_raw=cik_raw,
            name_override=name_override,
            user_agent_email=user_agent_email,
        )
        company, created = Company.objects.get_or_create(
            cik=cik,
            defaults={"name": name, "ticker": ticker_out},
        )
        if not created:
            updates: dict[str, object] = {}
            if name and (not company.name or str(company.name).startswith("CIK ")):
                updates["name"] = name
            if ticker_out and not company.ticker:
                updates["ticker"] = ticker_out
            if updates:
                for k, v in updates.items():
                    setattr(company, k, v)
                company.save(update_fields=list(updates.keys()))
        return company, created

    @staticmethod
    def bulk_sync_companies_from_sec_tickers(
        *,
        user_agent_email: str | None,
        update_existing: bool = False,
        refresh_sec_json: bool = False,
    ) -> dict[str, Any]:
        return sync_companies_from_sec_company_tickers(
            user_agent_email=user_agent_email,
            update_existing=update_existing,
            refresh_sec_json=refresh_sec_json,
        )

    @staticmethod
    def search_edgar_directory(
        query: str,
        *,
        user_agent_email: str | None,
        limit: int = 50,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Search the cached SEC ticker directory (DB-first, optional refresh)."""
        return search_company_tickers(
            query,
            user_agent_email=user_agent_email,
            limit=limit,
            force_refresh=force_refresh,
        )

    @staticmethod
    def ingest_htm(
        *,
        url: str,
        ticker: str | None,
        cik: str | None,
        user_agent_email: str | None,
    ) -> Filing:
        """Download and parse one HTM filing into Filing/Section/Table rows."""
        return ingest_htm_filing(
            url=url, ticker=ticker, cik=cik, user_agent_email=user_agent_email
        )

    @staticmethod
    def sync_submissions(
        company: Company,
        *,
        user_agent_email: str | None,
        payload: dict[str, Any] | None = None,
        force_refresh: bool = False,
    ) -> int:
        return sync_submissions_for_company(
            company,
            payload,
            user_agent_email=user_agent_email,
            force_refresh=force_refresh,
        )

    @staticmethod
    def sync_facts(
        company: Company,
        *,
        user_agent_email: str | None,
        facts_payload: dict[str, Any] | None = None,
        force_refresh: bool = False,
        compute_metrics: bool = False,
    ) -> int:
        n = sync_company_facts_to_db(
            company,
            facts_payload,
            user_agent_email=user_agent_email,
            force_refresh=force_refresh,
        )
        if compute_metrics:
            # Runs in its OWN transaction, after the facts sync has committed — a
            # metric failure must never roll back freshly-synced facts.
            from warehouse.services.edgar.metrics import compute_derived_metrics

            compute_derived_metrics(company)
        return n
