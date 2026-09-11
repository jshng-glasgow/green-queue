"""Command-line interface for Green Queue."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import requests
from pydantic import ValidationError

from .data_fetcher import DataFetcher
from .data_vis import DataVisualizer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="green-queue",
        description="Check when the regional electricity grid is lower carbon.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    status = subparsers.add_parser("status", help="show current and 24-hour grid status")
    status.add_argument(
        "--region",
        default="GB",
        help="Carbon Intensity API region name (default: GB)",
    )
    status.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds (default: 10)",
    )

    subparsers.add_parser("regions", help="list available Carbon Intensity API regions")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "status":
        try:
            fetcher = DataFetcher(region=args.region, timeout=args.timeout)
            DataVisualizer(fetcher).display()
        except (requests.RequestException, ValidationError, ValueError) as error:
            print(f"green-queue: unable to retrieve grid status: {error}", file=sys.stderr)
            return 1
    elif args.command == "regions":
        print("Available Carbon Intensity API regions:")
        for region in sorted(DataFetcher().region_ids):
            print(f"  {region.title()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
