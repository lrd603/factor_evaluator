"""Explicit cached/local V3.1 research runner; never silently substitutes mock data."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from factor_analysis.v3 import run_v3_research


def main() -> None:
    parser = argparse.ArgumentParser(description="Run auditable V3.1 factor research")
    parser.add_argument("--prices", default="data/raw_stock_data.csv")
    parser.add_argument("--factors", default="data/factor_data_generated.csv")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--factor-set", nargs="+")
    parser.add_argument("--universe", choices=["ALL_A", "CSI300", "CSI500"], default="ALL_A")
    args = parser.parse_args()
    if args.universe != "ALL_A":
        raise SystemExit("CSI300/CSI500 rejected: no true historical constituent source was supplied")
    price_path = PROJECT_ROOT / args.prices; factor_path = PROJECT_ROOT / args.factors
    if not price_path.exists() or not factor_path.exists():
        raise SystemExit("Required real/cache inputs are missing; mock fallback is disabled")
    prices = pd.read_csv(price_path, dtype={"stock": str})
    factors = pd.read_csv(factor_path, dtype={"stock": str})
    for frame in (prices, factors): frame["date"] = pd.to_datetime(frame["date"])
    if args.start_date:
        prices = prices[prices.date >= pd.Timestamp(args.start_date)]; factors = factors[factors.date >= pd.Timestamp(args.start_date)]
    if args.end_date:
        prices = prices[prices.date <= pd.Timestamp(args.end_date)]; factors = factors[factors.date <= pd.Timestamp(args.end_date)]
    if args.factor_set:
        factors = factors[factors.factor_name.isin(args.factor_set)]
    for directory in ["cache/prices", "cache/fundamentals", "cache/universe", "cache/exposures"]:
        (PROJECT_ROOT / directory).mkdir(parents=True, exist_ok=True)
    result = run_v3_research(prices, factors)
    print(result["report"])


if __name__ == "__main__":
    main()
