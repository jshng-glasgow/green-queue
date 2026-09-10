from datetime import timezone

import pytest
from pydantic import ValidationError

from green_queue.models import (
    CarbonIntensityIndex,
    CurrentRegionalResponse,
    FuelType,
    RegionalForecastResponse,
)


def region_reading(short_name: str = "South Scotland") -> dict:
    return {
        "regionid": 2,
        "dnoregion": "SP Distribution",
        "shortname": short_name,
        "intensity": {"forecast": 42, "index": "very low"},
        "generationmix": [{"fuel": "wind", "perc": 72.4}],
    }


def test_current_response_parses_nested_region_history() -> None:
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

    response = CurrentRegionalResponse.model_validate(payload)
    period = response.data[0].data[0]

    assert period.from_.tzinfo == timezone.utc
    assert period.intensity.index is CarbonIntensityIndex.LOW
    assert period.generation_mix[0].fuel is FuelType.WIND
    assert period.generation_mix[0].percentage == 70.1


def test_forecast_extracts_only_requested_region() -> None:
    payload = {
        "data": [
            {
                "from": "2026-09-10T10:00Z",
                "to": "2026-09-10T10:30Z",
                "regions": [region_reading(), region_reading("North Scotland")],
            }
        ]
    }

    response = RegionalForecastResponse.model_validate(payload)
    observations = response.observations_for("south scotland")

    assert len(observations) == 1
    assert observations[0].short_name == "South Scotland"
    assert observations[0].intensity.forecast == 42


def test_new_region_ids_do_not_break_the_whole_forecast() -> None:
    gb = region_reading("GB")
    gb["regionid"] = 18
    payload = {
        "data": [
            {
                "from": "2026-09-10T10:00Z",
                "to": "2026-09-10T10:30Z",
                "regions": [region_reading(), gb],
            }
        ]
    }

    response = RegionalForecastResponse.model_validate(payload)

    assert response.data[0].regions[1].region_id == 18


@pytest.mark.parametrize("percentage", [-0.1, 100.1])
def test_generation_percentage_is_bounded(percentage: float) -> None:
    reading = region_reading()
    reading["generationmix"][0]["perc"] = percentage
    payload = {
        "data": [
            {
                "from": "2026-09-10T10:00Z",
                "to": "2026-09-10T10:30Z",
                "regions": [reading],
            }
        ]
    }

    with pytest.raises(ValidationError):
        RegionalForecastResponse.model_validate(payload)


def test_period_end_must_follow_start() -> None:
    payload = {
        "data": [
            {
                "from": "2026-09-10T10:30Z",
                "to": "2026-09-10T10:00Z",
                "regions": [region_reading()],
            }
        ]
    }

    with pytest.raises(ValidationError, match="period end"):
        RegionalForecastResponse.model_validate(payload)
