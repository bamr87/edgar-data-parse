from __future__ import annotations

import pytest
import responses
from responses import matchers

from public_data.models import ExternalSeries, SeriesObservation
from public_data.providers.fred import FRED_OBSERVATIONS_URL, FRED_SERIES_INFO_URL
from public_data.services.sync import ensure_fred_series, upsert_series_observations


@pytest.mark.django_db
def test_ensure_fred_series_creates_row(fred_api_key: None) -> None:
    body = {
        "seriess": [
            {
                "id": "TESTGDP",
                "title": "Test GDP",
                "frequency": "Quarterly",
                "units": "Billions of Dollars",
            }
        ]
    }
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rs:
        rs.add(
            responses.GET,
            FRED_SERIES_INFO_URL,
            match=[
                matchers.query_param_matcher(
                    {
                        "series_id": "TESTGDP",
                        "api_key": "test-fred-key",
                        "file_type": "json",
                    }
                )
            ],
            json=body,
        )
        obj = ensure_fred_series("TESTGDP")

    assert obj.provider == "fred"
    assert obj.external_id == "TESTGDP"
    assert "Test GDP" in obj.title
    assert ExternalSeries.objects.filter(provider="fred", external_id="TESTGDP").exists()


@pytest.mark.django_db
def test_upsert_series_observations_idempotent(fred_api_key: None) -> None:
    series = ExternalSeries.objects.create(
        provider="fred",
        external_id="SERIES1",
        title="Series 1",
    )
    obs_body = {
        "observations": [
            {"date": "2023-01-01", "value": "1.25"},
            {"date": "2023-02-01", "value": "."},
        ]
    }
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rs:
        rs.add(
            responses.GET,
            FRED_OBSERVATIONS_URL,
            match=[
                matchers.query_param_matcher(
                    {
                        "series_id": "SERIES1",
                        "api_key": "test-fred-key",
                        "file_type": "json",
                    }
                )
            ],
            json=obs_body,
        )
        n1 = upsert_series_observations(series)

    assert n1 == 1
    assert SeriesObservation.objects.filter(series=series).count() == 1

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rs:
        rs.add(
            responses.GET,
            FRED_OBSERVATIONS_URL,
            match=[
                matchers.query_param_matcher(
                    {
                        "series_id": "SERIES1",
                        "api_key": "test-fred-key",
                        "file_type": "json",
                    }
                )
            ],
            json=obs_body,
        )
        n2 = upsert_series_observations(series)

    assert n2 == 1
    assert SeriesObservation.objects.filter(series=series).count() == 1
