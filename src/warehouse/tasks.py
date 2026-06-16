"""Celery tasks for background EDGAR sync (autodiscovered by config.celery).

Each task is a thin wrapper over the synchronous ``EdgarSyncService`` so the same
logic runs identically from the API (async), management commands (sync), and the
worker. Task state is queryable via the ``/api/v1/tasks/<id>/`` endpoint.
"""

from __future__ import annotations

from celery import shared_task

from warehouse.models import Company
from warehouse.services.edgar.sync import EdgarSyncService


@shared_task(name="warehouse.sync_submissions")
def sync_submissions_task(company_id: int, user_agent_email: str | None = None) -> int:
    company = Company.objects.get(id=company_id)
    return EdgarSyncService.sync_submissions(company, user_agent_email=user_agent_email)


@shared_task(name="warehouse.sync_facts")
def sync_facts_task(
    company_id: int,
    user_agent_email: str | None = None,
    compute_metrics: bool = True,
) -> int:
    company = Company.objects.get(id=company_id)
    return EdgarSyncService.sync_facts(
        company, user_agent_email=user_agent_email, compute_metrics=compute_metrics
    )


@shared_task(name="warehouse.compute_metrics")
def compute_metrics_task(company_id: int) -> int:
    from warehouse.services.edgar.metrics import compute_derived_metrics

    company = Company.objects.get(id=company_id)
    return compute_derived_metrics(company)
