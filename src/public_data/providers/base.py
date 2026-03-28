from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass
class ObservationPoint:
    observation_date: date
    value: Decimal


class PublicDataProvider(Protocol):
    provider_slug: str

    def fetch_series_observations(
        self, external_id: str, observation_start: date | None = None
    ) -> tuple[list[ObservationPoint], str]: ...
