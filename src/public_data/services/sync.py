"""Sync external series observations into the database."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from public_data.models import ExternalSeries, SeriesObservation
from public_data.providers.fred import FredProvider


@transaction.atomic
def upsert_series_observations(
    series: ExternalSeries,
    *,
    observation_start=None,
) -> int:
    if series.provider == "fred":
        provider = FredProvider()
        points, source_url = provider.fetch_series_observations(
            series.external_id, observation_start=observation_start
        )
    else:
        raise ValueError(f"Unsupported provider {series.provider}")

    n = 0
    now = timezone.now()
    for p in points:
        SeriesObservation.objects.update_or_create(
            series=series,
            observation_date=p.observation_date,
            defaults={
                "value": p.value,
                "source_url": source_url[:1024],
            },
        )
        n += 1
    series.last_synced_at = now
    series.save(update_fields=["last_synced_at"])
    return n


def ensure_fred_series(external_id: str) -> ExternalSeries:
    prov = FredProvider()
    info = prov.series_info(external_id)
    ser = (info.get("seriess") or [None])[0] or {}
    title = str(ser.get("title") or external_id)[:512]
    freq = str(ser.get("frequency") or "")[:32]
    units = str(ser.get("units") or "")[:128]
    obj, _ = ExternalSeries.objects.update_or_create(
        provider="fred",
        external_id=external_id,
        defaults={
            "title": title,
            "frequency": freq,
            "units": units,
            "metadata": {"fred": ser},
        },
    )
    return obj


def sync_series_incremental(series: ExternalSeries, days_back: int = 365 * 10) -> int:
    start = None
    if days_back:
        start = (timezone.now().date() - timedelta(days=days_back))
    return upsert_series_observations(series, observation_start=start)
