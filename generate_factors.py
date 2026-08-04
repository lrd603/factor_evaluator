"""Command-line entry point for generating evaluator-compatible factor data."""

from __future__ import annotations

import argparse

from factors.generator import generate_factor_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate factors from raw A-share daily market data."
    )
    parser.add_argument("--input", default="data/raw_stock_data.csv")
    parser.add_argument("--output", default="data/factor_data_generated.csv")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    factor_data = generate_factor_data(args.input, args.output)
    print(f"Generated {len(factor_data)} factor rows.")
    print(f"Saved factor data to {args.output}")
    print(factor_data.head().to_string(index=False))


if __name__ == "__main__":
    main()

