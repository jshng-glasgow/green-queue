"""Client for the NESO Carbon Intensity API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests

from .models import (
    CurrentRegionalResponse,
    RegionalForecastResponse,
    RegionalObservation,
)


class DataFetcher:
    def __init__(
        self,
        base_url: str = "https://api.carbonintensity.org.uk/",
        *,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        self.headers = {"Accept": "application/json"}
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or requests.Session()

    def _fetch_data(self, endpoint: str) -> Any:
        response = self.session.get(
            urljoin(self.base_url, endpoint),
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def current_intensity(self, region: str = "scotland") -> CurrentRegionalResponse:
        endpoint = f"regional/{region}"
        return CurrentRegionalResponse.model_validate(self._fetch_data(endpoint))

    def forecast_24h(self, region: str = "South Scotland") -> list[RegionalObservation]:
        return self._regional_window("fw24h", region)

    def backcast_24h(self, region: str = "South Scotland") -> list[RegionalObservation]:
        return self._regional_window("pt24h", region)

    def _regional_window(self, window: str, region: str) -> list[RegionalObservation]:
        # The API documents all timestamps as UTC and expects minute precision.
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
        endpoint = f"regional/intensity/{now}/{window}"
        response = RegionalForecastResponse.model_validate(self._fetch_data(endpoint))
        observations = response.observations_for(region)
        if not observations:
            raise ValueError(f"region {region!r} was not present in the API response")
        return observations
    
