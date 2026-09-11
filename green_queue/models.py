"""Validated models for responses from the Carbon Intensity API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CarbonIntensityIndex(str, Enum):
    VERY_LOW = "very low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very high"


class FuelType(str, Enum):
    BIOMASS = "biomass"
    COAL = "coal"
    GAS = "gas"
    HYDRO = "hydro"
    IMPORTS = "imports"
    NUCLEAR = "nuclear"
    OTHER = "other"
    SOLAR = "solar"
    STORAGE = "storage"
    WIND = "wind"


class ApiModel(BaseModel):
    """Common API model behaviour.

    Unknown fields are retained so an additive upstream API change does not
    stop the login-time display from working.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class CarbonIntensity(ApiModel):
    """Carbon intensity in gCO2/kWh for one half-hour period."""

    forecast: int = Field(ge=0)
    index: CarbonIntensityIndex
    actual: int | None = Field(default=None, ge=0)


class FuelMix(ApiModel):
    fuel: FuelType
    percentage: float = Field(alias="perc", ge=0, le=100)


class Period(ApiModel):
    from_: datetime = Field(alias="from")
    to: datetime

    @model_validator(mode="after")
    def end_must_follow_start(self) -> Period:
        if self.to <= self.from_:
            raise ValueError("period end must be later than its start")
        return self


class IntensityPeriod(Period):
    intensity: CarbonIntensity
    generation_mix: list[FuelMix] = Field(alias="generationmix")


class Region(ApiModel):
    region_id: int = Field(alias="regionid", ge=1)
    dno_region: str = Field(alias="dnoregion")
    short_name: str = Field(alias="shortname")
    postcode: str | None = None


class RegionReading(Region):
    intensity: CarbonIntensity
    generation_mix: list[FuelMix] = Field(alias="generationmix")


class RegionalPeriod(Period):
    regions: list[RegionReading]

    def observation_for(self, short_name: str) -> RegionalObservation | None:
        """Return the selected region combined with this period's timestamps."""
        match = next(
            (region for region in self.regions if region.short_name.casefold() == short_name.casefold()),
            None,
        )
        if match is None:
            return None
        return RegionalObservation(
            from_=self.from_,
            to=self.to,
            **match.model_dump(),
        )


class RegionalObservation(Period, RegionReading):
    """A visualiser-friendly reading for one region and half-hour period."""


class RegionHistory(Region):
    data: list[IntensityPeriod]


class CurrentRegionalResponse(ApiModel):
    """Envelope returned by endpoints such as ``/regional/scotland``."""

    data: list[RegionHistory]


class RegionalForecastResponse(ApiModel):
    """Envelope returned by regional forecast and backcast endpoints."""

    data: list[RegionalPeriod]

    def observations_for(self, short_name: str) -> list[RegionalObservation]:
        observations = [period.observation_for(short_name) for period in self.data]
        return [observation for observation in observations if observation is not None]
