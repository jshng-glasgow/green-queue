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
