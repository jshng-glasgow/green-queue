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
                "regionid": 16,
                "dnoregion": "Scotland",
                "shortname": "Scotland",
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

    result = DataFetcher(session=session).current_intensity()

    assert isinstance(result, CurrentRegionalResponse)
    session.get.assert_called_once_with(
        "https://api.carbonintensity.org.uk/regional/scotland",
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

    result = DataFetcher(session=session).forecast_24h()

    assert len(result) == 1
    assert isinstance(result[0], RegionalObservation)
    assert result[0].short_name == "South Scotland"


def test_http_errors_are_not_hidden() -> None:
    session = Mock(spec=requests.Session)
    response = response_with({"error": {"message": "unavailable"}})
    response.raise_for_status.side_effect = requests.HTTPError("503")
    session.get.return_value = response

    with pytest.raises(requests.HTTPError, match="503"):
        DataFetcher(session=session).current_intensity()
