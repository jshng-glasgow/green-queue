from copy import deepcopy
from io import StringIO

import pytest

from green_queue.data_vis import (
    DataVisualizer,
    build_status_report,
    intensity_statistics,
    render_status,
)
from green_queue.models import CurrentRegionalResponse, RegionalForecastResponse


ANSI_GREEN = "\x1b[32m"
ANSI_ORANGE = "\x1b[38;2;255;165;0m"
ANSI_RED = "\x1b[31m"


def reading(intensity: int, index: str = "moderate") -> dict:
    return {
        "regionid": 2,
        "dnoregion": "SP Distribution",
        "shortname": "South Scotland",
        "intensity": {"forecast": intensity, "index": index},
        "generationmix": [
            {"fuel": "gas", "perc": 20.0},
            {"fuel": "wind", "perc": 80.0},
        ],
    }


def observations(*intensities: int):
    periods = []
    for offset, intensity in enumerate(intensities):
        hour = 10 + offset
        periods.append(
            {
                "from": f"2026-09-10T{hour:02d}:00Z",
                "to": f"2026-09-10T{hour:02d}:30Z",
                "regions": [reading(intensity)],
            }
        )
    response = RegionalForecastResponse.model_validate({"data": periods})
    return response.observations_for("South Scotland")


def current_response(intensity: int = 70, index: str = "moderate"):
    item = reading(intensity, index)
    return CurrentRegionalResponse.model_validate(
        {
            "data": [
                {
                    "regionid": item["regionid"],
                    "dnoregion": item["dnoregion"],
                    "shortname": item["shortname"],
                    "data": [
                        {
                            "from": "2026-09-10T09:30Z",
                            "to": "2026-09-10T10:00Z",
                            "intensity": item["intensity"],
                            "generationmix": item["generationmix"],
                        }
                    ],
                }
            ]
        }
    )


def test_statistics_do_not_reorder_observations() -> None:
    items = observations(60, 20, 90)
    original = deepcopy(items)

    result = intensity_statistics(items)

    assert [item.intensity.forecast for item in items] == [60, 20, 90]
    assert items == original
    assert result.minimum.intensity.forecast == 20
    assert result.maximum.intensity.forecast == 90
    assert result.average == pytest.approx(56.67, rel=0.01)


def test_report_recommends_the_lower_forecast_period() -> None:
    report = build_status_report(
        current_response(),
        forecast=observations(55, 30, 80),
        backcast=observations(40, 60, 50),
    )

    assert report.region == "South Scotland"
    assert "waiting until" in report.recommendation
    assert report.forecast.minimum.intensity.forecast == 30


def test_report_identifies_when_no_forecast_period_is_lower() -> None:
    report = build_status_report(
        current_response(intensity=20, index="moderate"),
        forecast=observations(30, 55),
        backcast=observations(40, 60),
    )

    assert report.recommendation == (
        "There are not any lower forecast periods in the next 24 hours; "
        "consider running your job now."
    )


def test_render_status_is_plain_text_and_sorts_generation_mix() -> None:
    report = build_status_report(
        current_response(index="low"),
        forecast=observations(55, 30),
        backcast=observations(40, 60),
    )

    output = render_status(report)

    assert "Green Queue - South Scotland" in output
    assert "Carbon intensity: 70 gCO2/kWh (low)" in output
    assert output.index("wind") < output.index("gas")
    assert "\x1b" not in output


@pytest.mark.parametrize(
    ("index", "expected_colour"),
    [
        ("very low", ANSI_GREEN),
        ("low", ANSI_GREEN),
        ("moderate", ANSI_ORANGE),
        ("high", ANSI_RED),
        ("very high", ANSI_RED),
    ],
)
def test_render_status_colours_intensity_indices(
    index: str,
    expected_colour: str,
) -> None:
    report = build_status_report(
        current_response(index=index),
        forecast=observations(55, 30),
        backcast=observations(40, 60),
    )

    output = render_status(report, use_color=True)

    assert f"{expected_colour}({index})\x1b[0m" in output


@pytest.mark.parametrize(
    ("current_intensity", "index", "forecast", "message", "expected_colour"),
    [
        (
            70,
            "low",
            (30, 55),
            "Now is a great time to run your job!",
            ANSI_GREEN,
        ),
        (
            20,
            "moderate",
            (30, 55),
            "There are not any lower forecast periods in the next 24 hours; "
            "consider running your job now.",
            ANSI_ORANGE,
        ),
        (
            70,
            "moderate",
            (30, 55),
            "Consider waiting until",
            ANSI_RED,
        ),
    ],
)
def test_render_status_colours_recommendations(
    current_intensity: int,
    index: str,
    forecast: tuple[int, ...],
    message: str,
    expected_colour: str,
) -> None:
    report = build_status_report(
        current_response(intensity=current_intensity, index=index),
        forecast=observations(*forecast),
        backcast=observations(40, 60),
    )

    output = render_status(report, use_color=True)

    assert expected_colour + message in output


def test_visualizer_accepts_a_fetcher_and_output_stream() -> None:
    class FakeFetcher:
        def current_intensity(self):
            return current_response(index="low")

        def forecast_24h(self):
            return observations(30, 50)

        def backcast_24h(self):
            return observations(40, 60)

    stream = StringIO()

    DataVisualizer(FakeFetcher()).display(file=stream)

    assert stream.getvalue().startswith("Green Queue - South Scotland\n")
