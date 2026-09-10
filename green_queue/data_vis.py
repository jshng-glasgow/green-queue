"""Build and render a terminal summary of regional grid conditions."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from statistics import fmean
from typing import TextIO

from termcolor import colored

from .data_fetcher import DataFetcher
from .models import (
    CarbonIntensityIndex,
    CurrentRegionalResponse,
    IntensityPeriod,
    RegionalObservation,
)

Observation = IntensityPeriod | RegionalObservation
ORANGE = (255, 165, 0)


class RecommendationLevel(str, Enum):
    GREAT_TIME = "great_time"
    NO_LOWER_FORECAST = "no_lower_forecast"
    WAIT = "wait"


@dataclass(frozen=True)
class IntensityStatistics:
    minimum: Observation
    maximum: Observation
    average: float


@dataclass(frozen=True)
class GridStatusReport:
    region: str
    current: IntensityPeriod
    backcast: IntensityStatistics
    forecast: IntensityStatistics
    recommendation: str
    recommendation_level: RecommendationLevel


def intensity_statistics(observations: Sequence[Observation]) -> IntensityStatistics:
    """Calculate intensity statistics without changing the input ordering."""
    if not observations:
        raise ValueError("cannot calculate statistics without observations")

    return IntensityStatistics(
        minimum=min(observations, key=lambda item: item.intensity.forecast),
        maximum=max(observations, key=lambda item: item.intensity.forecast),
        average=fmean(item.intensity.forecast for item in observations),
    )


def build_status_report(
    current_response: CurrentRegionalResponse,
    forecast: Sequence[RegionalObservation],
    backcast: Sequence[RegionalObservation],
) -> GridStatusReport:
    """Turn validated API responses into display-ready information."""
    if not current_response.data:
        raise ValueError("current-intensity response did not contain a region")

    region = current_response.data[0]
    if not region.data:
        raise ValueError("current-intensity response did not contain a reading")

    current = max(region.data, key=lambda item: item.to)
    forecast_stats = intensity_statistics(forecast)
    backcast_stats = intensity_statistics(backcast)
    minimum = forecast_stats.minimum

    if current.intensity.index in {
        CarbonIntensityIndex.VERY_LOW,
        CarbonIntensityIndex.LOW,
    }:
        recommendation = "Now is a great time to run your job!"
        recommendation_level = RecommendationLevel.GREAT_TIME
    elif current.intensity.forecast <= minimum.intensity.forecast:
        recommendation = (
            "There are not any lower forecast periods in the next 24 hours; "
            "consider running your job now."
        )
        recommendation_level = RecommendationLevel.NO_LOWER_FORECAST
    else:
        recommendation = (
            f"Consider waiting until {_format_time(minimum.from_)} when the forecast "
            "carbon intensity is lower."
        )
        recommendation_level = RecommendationLevel.WAIT

    return GridStatusReport(
        region=region.short_name,
        current=current,
        backcast=backcast_stats,
        forecast=forecast_stats,
        recommendation=recommendation,
        recommendation_level=recommendation_level,
    )


def _format_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def _format_index(index: CarbonIntensityIndex, *, use_color: bool) -> str:
    text = f"({index.value})"
    if index in {CarbonIntensityIndex.VERY_LOW, CarbonIntensityIndex.LOW}:
        colour = "green"
    elif index is CarbonIntensityIndex.MODERATE:
        colour = ORANGE
    else:
        colour = "red"

    return colored(
        text,
        colour,
        no_color=not use_color,
        force_color=use_color,
    )


def _format_recommendation(report: GridStatusReport, *, use_color: bool) -> str:
    colours = {
        RecommendationLevel.GREAT_TIME: "green",
        RecommendationLevel.NO_LOWER_FORECAST: ORANGE,
        RecommendationLevel.WAIT: "red",
    }
    return colored(
        report.recommendation,
        colours[report.recommendation_level],
        no_color=not use_color,
        force_color=use_color,
    )


def _format_observation(
    label: str,
    observation: Observation,
    *,
    use_color: bool,
) -> str:
    intensity = observation.intensity
    return (
        f"  {label:<9} {intensity.forecast:>4} gCO2/kWh "
        f"{_format_index(intensity.index, use_color=use_color)} "
        f"at {_format_time(observation.from_)}"
    )


def render_status(report: GridStatusReport, *, use_color: bool = False) -> str:
    """Render a report as plain text suitable for any terminal."""
    current = report.current
    fuels = sorted(
        current.generation_mix,
        key=lambda fuel: fuel.percentage,
        reverse=True,
    )
    lines = [
        f"Green Queue - {report.region}",
        "",
        "Current",
        (
            f"  Carbon intensity: {current.intensity.forecast} gCO2/kWh "
            f"{_format_index(current.intensity.index, use_color=use_color)}"
        ),
        "  Generation mix:",
        *(f"    {fuel.fuel.value:<10} {fuel.percentage:>5.1f}%" for fuel in fuels),
        "",
        "Last 24 hours",
        _format_observation(
            "Minimum:", report.backcast.minimum, use_color=use_color
        ),
        _format_observation(
            "Maximum:", report.backcast.maximum, use_color=use_color
        ),
        f"  {'Average:':<9} {report.backcast.average:>4.1f} gCO2/kWh",
        "",
        "Next 24 hours",
        _format_observation(
            "Minimum:", report.forecast.minimum, use_color=use_color
        ),
        _format_observation(
            "Maximum:", report.forecast.maximum, use_color=use_color
        ),
        f"  {'Average:':<9} {report.forecast.average:>4.1f} gCO2/kWh",
        "",
        "Recommendation",
        f"  {_format_recommendation(report, use_color=use_color)}",
    ]
    return "\n".join(lines)


class DataVisualizer:
    def __init__(self, data_fetcher: DataFetcher | None = None) -> None:
        self.data_fetcher = data_fetcher or DataFetcher()

    def get_report(self) -> GridStatusReport:
        """Fetch current, forecast, and historical data and build a report."""
        return build_status_report(
            self.data_fetcher.current_intensity(),
            self.data_fetcher.forecast_24h(),
            self.data_fetcher.backcast_24h(),
        )

    def render(self, *, use_color: bool = False) -> str:
        return render_status(self.get_report(), use_color=use_color)

    def display(self, file: TextIO | None = None) -> None:
        output = file or sys.stdout
        use_color = bool(getattr(output, "isatty", lambda: False)())
        print(self.render(use_color=use_color), file=output)
