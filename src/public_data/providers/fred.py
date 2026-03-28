"""FRED API client (https://fred.stlouisfed.org/docs/api/fred/)."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import requests

from public_data.providers.base import ObservationPoint

logger = logging.getLogger(__name__)

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_INFO_URL = "https://api.stlouisfed.org/fred/series"


class FredProvider:
    provider_slug = "fred"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("FRED_API_KEY") or ""

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("FRED_API_KEY is not set")
        q = {**params, "api_key": self.api_key, "file_type": "json"}
        r = requests.get(url, params=q, timeout=60)
        r.raise_for_status()
        return r.json()

    def series_info(self, series_id: str) -> dict[str, Any]:
        return self._get(
            FRED_SERIES_INFO_URL,
            {"series_id": series_id},
        )

    def fetch_series_observations(
        self, external_id: str, observation_start: date | None = None
    ) -> tuple[list[ObservationPoint], str]:
        params: dict[str, Any] = {"series_id": external_id}
        if observation_start:
            params["observation_start"] = observation_start.isoformat()
        data = self._get(FRED_OBSERVATIONS_URL, params)
        out: list[ObservationPoint] = []
        for row in data.get("observations") or []:
            if row.get("value") in (".", None, ""):
                continue
            try:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
                out.append(ObservationPoint(d, Decimal(str(row["value"]))))
            except (ValueError, KeyError, TypeError) as e:
                logger.debug("skip row %s: %s", row, e)
        source = f"{FRED_OBSERVATIONS_URL}?{urlencode({'series_id': external_id})}"
        return out, source
