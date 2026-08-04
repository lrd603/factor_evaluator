"""Command-line entry point for downloading A-share historical data."""

from __future__ import annotations

import argparse

from data.market_data import fetch_and_save_stock_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch A-share daily data via AkShare.")
    parser.add_argument("stocks", nargs="+", help="Six-digit stock codes, e.g. 600519 000001")
    parser.add_argument("--start", help="Start date, e.g. 2024-01-01")
    parser.add_argument("--end", help="End date, e.g. 2024-12-31")
    parser.add_argument(
        "--adjust",
        choices=["none", "qfq", "hfq"],
        default="qfq",
        help="Price adjustment: none, qfq (default), or hfq",
    )
    parser.add_argument("--output", default="data/raw_stock_data.csv")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    data = fetch_and_save_stock_data(
        args.stocks,
        start_date=args.start,
        end_date=args.end,
        output_path=args.output,
        adjust="" if args.adjust == "none" else args.adjust,
    )
    print(f"Fetched {len(data)} rows for {data['stock'].nunique()} stock(s).")
    print(f"Saved market data to {args.output}")
    print(data.head().to_string(index=False))


if __name__ == "__main__":
    main()

