from unittest.mock import Mock

import requests
import pytest

from green_queue.data_fetcher import DataFetcher
from green_queue.models import CurrentRegionalResponse, RegionalObservation


def response_with(payload: dict) -> Mock:
    response = Mock(spec=requests.Response)
    response.json.return_value = payload
    return response


def test_current_intensity_returns_validated_model() -> None:
    payload = {
        "data": [
            {
                "regionid": 2,
                "dnoregion": "SP Distribution",
                "shortname": "South Scotland",
                "data": [
                    {
                        "from": "2026-09-10T10:00Z",
                        "to": "2026-09-10T10:30Z",
                        "intensity": {"forecast": 50, "index": "low"},
                        "generationmix": [{"fuel": "wind", "perc": 70.1}],
                    }
                ],
            }
        ]
    }
    session = Mock(spec=requests.Session)
    session.get.return_value = response_with(payload)

    result = DataFetcher(region="South Scotland", session=session).current_intensity()

    assert isinstance(result, CurrentRegionalResponse)
    session.get.assert_called_once_with(
        "https://api.carbonintensity.org.uk/regional/regionid/2",
        headers={"Accept": "application/json"},
        timeout=10.0,
    )
    session.get.return_value.raise_for_status.assert_called_once()


def test_forecast_returns_flat_selected_region_observations() -> None:
    payload = {
        "data": [
            {
                "from": "2026-09-10T10:00Z",
                "to": "2026-09-10T10:30Z",
                "regions": [
                    {
                        "regionid": 2,
                        "dnoregion": "SP Distribution",
                        "shortname": "South Scotland",
                        "intensity": {"forecast": 42, "index": "very low"},
                        "generationmix": [{"fuel": "wind", "perc": 72.4}],
                    }
                ],
            }
        ]
    }
    session = Mock(spec=requests.Session)
    session.get.return_value = response_with(payload)

    result = DataFetcher(region="South Scotland", session=session).forecast_24h()

    assert len(result) == 1
    assert isinstance(result[0], RegionalObservation)
    assert result[0].short_name == "South Scotland"


def test_default_region_uses_gb_current_endpoint() -> None:
    payload = {
        "data": [
            {
                "regionid": 18,
                "dnoregion": "GB",
                "shortname": "GB",
                "data": [
                    {
                        "from": "2026-09-10T10:00Z",
                        "to": "2026-09-10T10:30Z",
                        "intensity": {"forecast": 100, "index": "moderate"},
                        "generationmix": [{"fuel": "wind", "perc": 30.0}],
                    }
                ],
            }
        ]
    }
    session = Mock(spec=requests.Session)
    session.get.return_value = response_with(payload)

    result = DataFetcher(session=session).current_intensity()

    assert result.data[0].short_name == "GB"
    session.get.assert_called_once_with(
        "https://api.carbonintensity.org.uk/regional/regionid/18",
        headers={"Accept": "application/json"},
        timeout=10.0,
    )


def test_default_region_selects_gb_forecast_observations() -> None:
    payload = {
        "data": [
            {
                "from": "2026-09-10T10:00Z",
                "to": "2026-09-10T10:30Z",
                "regions": [
                    {
                        "regionid": 2,
                        "dnoregion": "SP Distribution",
                        "shortname": "South Scotland",
                        "intensity": {"forecast": 42, "index": "very low"},
                        "generationmix": [{"fuel": "wind", "perc": 72.4}],
                    },
                    {
                        "regionid": 18,
                        "dnoregion": "GB",
                        "shortname": "GB",
                        "intensity": {"forecast": 100, "index": "moderate"},
                        "generationmix": [{"fuel": "wind", "perc": 30.0}],
                    },
                ],
            }
        ]
    }
    session = Mock(spec=requests.Session)
    session.get.return_value = response_with(payload)

    result = DataFetcher(session=session).forecast_24h()

    assert len(result) == 1
    assert result[0].short_name == "GB"
    assert result[0].region_id == 18


def test_http_errors_are_not_hidden() -> None:
    session = Mock(spec=requests.Session)
    response = response_with({"error": {"message": "unavailable"}})
    response.raise_for_status.side_effect = requests.HTTPError("503")
    session.get.return_value = response

    with pytest.raises(requests.HTTPError, match="503"):
        DataFetcher(session=session).current_intensity()


def test_unknown_region_is_rejected_before_a_request() -> None:
    with pytest.raises(ValueError, match="unknown region"):
        DataFetcher(region="Atlantis")
