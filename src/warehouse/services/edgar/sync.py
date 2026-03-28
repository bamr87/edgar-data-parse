"""Orchestrate EDGAR resolution and sync (warehouse + SEC) for APIs and jobs."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from sec_edgar.adapters.direct import DirectEdgarAdapter
from sec_edgar.services.bulk_company_tickers import sync_companies_from_sec_company_tickers
from sec_edgar.services.company_facts import sync_company_facts_to_db
from sec_edgar.services.submissions import sync_submissions_for_company
from warehouse.models import Company, ListedIssuer
from warehouse.services.edgar.listed_issuers import sync_listed_issuers_from_remote


class EdgarSyncService:
    """Application entry points for EDGAR-backed warehouse operations."""

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
            cik_try = str(cik_raw).zfill(10)
            try:
                norm = str(int(cik_try)).zfill(10)
            except ValueError:
                norm = cik_try
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
            raise ValueError("Could not resolve issuer from EDGAR directory")

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
    ) -> int:
        return sync_company_facts_to_db(
            company,
            facts_payload,
            user_agent_email=user_agent_email,
            force_refresh=force_refresh,
        )
