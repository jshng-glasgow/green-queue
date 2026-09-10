"""Prints out current grid status to temrinal. It grabs the current status,
and the 24h backcast and forcast for South Scotland.

Data provided:

Current carbon instensity and index.

Current grid makeup (percentage of each fuel type).
Min, max and average over the last 24 hrs
Time and value of forecasted minimum and maximum carbon intensity over the next 24 hrs.

Estimate of typical HPC job carbon if run now vs next minimum. 

Suggestion of when to run a job.


"""
from .data_fetcher import DataFetcher


class DataVisualizer:
    def __init__(self, data_fetcher: DataFetcher | None = None) -> None:
        self.data_fetcher = data_fetcher or DataFetcher()

    def display(self) -> None:
        current = self.data_fetcher.current_intensity().data[0].data[0]
        forecast = self.data_fetcher.forecast_24h()
        backcast = self.data_fetcher.backcast_24h()

        next_min_forecast = min(forecast, key=lambda obs: obs.intensity.forecast)
        # sort forecast and backcast by intensity
        forecast.sort(key=lambda obs: obs.intensity.forecast)
        backcast.sort(key=lambda obs: obs.intensity.forecast)


        backcast_avg = sum(obs.intensity.forecast for obs in backcast) / len(backcast) 

        print("Current carbon intensity:", current.intensity.forecast, "gCO2/kWh")
        print("Current grid makeup:")
        for fuel in current.generation_mix:
            print(f"  {fuel.fuel}: {fuel.percentage:.1f}%")
        print()
        print("Last 24 hours:")
        print(f"  Min: {backcast[0].intensity.forecast} ({backcast[0].intensity.index.value}) at {backcast[0].from_}")
        print(f"  Max: {backcast[-1].intensity.forecast} ({backcast[-1].intensity.index.value}) at {backcast[-1].to}")
        print(f"  Average: {backcast_avg:.1f}")
        print()
        print("Next 24 hours:")
        print(f"  Forecasted min: {forecast[0].intensity.forecast} ({forecast[0].intensity.index.value}) at {forecast[0].from_}")
        print(f"  Forecasted max: {forecast[-1].intensity.forecast} ({forecast[-1].intensity.index.value}) at {forecast[-1].to}")

        next_forecast_low = []
        if current.intensity.index.value in ["very low", "low"]:
            print("  Now is a great time to run your job!")
        elif current.intensity.index.value in ["moderate", "high"]: 
            print(f"  Now is not a great time to run your job. Consider waiting until {next_min_forecast.from_} when the forecasted carbon intensity is lower.")