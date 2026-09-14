"""Factor evaluator command-line workflow.

By default, raw A-share data is converted into factors before evaluation.  The
legacy CSV workflow remains available as an automatic fallback or via --input.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys


def _ensure_project_environment() -> None:
    """Re-run with the project virtual environment when dependencies are absent."""
    required = ("pandas", "matplotlib")
    if all(importlib.util.find_spec(package) is not None for package in required):
        return

    executable_name = "python.exe" if os.name == "nt" else "python"
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    project_python = Path(__file__).resolve().parent / ".venv" / scripts_dir / executable_name
    if project_python.exists() and Path(sys.executable).resolve() != project_python.resolve():
        print(f"Switching to project environment: {project_python}")
        os.execv(str(project_python), [str(project_python), *sys.argv])


_ensure_project_environment()

import matplotlib
import pandas as pd

# Report generation is a non-interactive batch workflow and must not require Tk.
matplotlib.use("Agg")

from evaluator.factor_runner import run_factor_evaluation
from evaluator.factor_score import evaluate_factor_scores
from evaluator.group_analysis import calculate_group_return
from evaluator.metrics import calculate_daily_ic, calculate_daily_rank_ic, calculate_icir
from evaluator.performance import calculate_max_drawdown, calculate_sharpe, calculate_win_rate
from evaluator.report import generate_markdown_report, generate_report
from evaluator.visualization import plot_ic_curve, plot_long_short_curve
from data.market_data import fetch_and_save_stock_data
from factors.generator import generate_factor_data
from stock_evaluator import evaluate_stock
from config.factor_metadata import DEFAULT_NORMALIZATION_METHOD, apply_factor_directions
from factor_analysis.reporting import (
    generate_v2_report,
    plot_correlation_heatmap,
    plot_ic_decay,
    plot_quantile_curves,
)
from factor_analysis.research import (
    analyze_ic_decay,
    average_factor_correlations,
    calculate_quantile_returns,
)
from factor_processing import preprocess_factors
from factor_analysis.v3 import run_v3_research


RAW_DATA_PATH = Path("data/raw_stock_data.csv")
GENERATED_DATA_PATH = Path("data/factor_data_generated.csv")
LEGACY_MULTI_FACTOR_PATH = Path("data/factor_data_multi.csv")
LEGACY_SINGLE_FACTOR_PATH = Path("data/factor_data.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the factor evaluation workflow.")
    parser.add_argument(
        "--stocks",
        nargs="+",
        help="Download and evaluate six-digit A-share stock codes.",
    )
    parser.add_argument("--start", help="Market-data start date, e.g. 2023-01-01.")
    parser.add_argument("--end", help="Market-data end date, e.g. 2024-12-31.")
    parser.add_argument(
        "--input",
        help="Use a prepared factor CSV and skip factor generation.",
    )
    parser.add_argument("--research-v3-real", action="store_true", help="Run the auditable V3.1 research pipeline from real/local cached inputs.")
    parser.add_argument("--universe", choices=["ALL_A", "CSI300", "CSI500"], default="ALL_A")
    parser.add_argument("--factors", nargs="+", help="Optional factor-name subset for research.")
    parser.add_argument("--raw", default=str(RAW_DATA_PATH), help="Raw market-data CSV.")
    parser.add_argument(
        "--generated",
        default=str(GENERATED_DATA_PATH),
        help="Generated factor-data CSV.",
    )
    return parser


def prepare_factor_data(
    manual_input: str | None = None,
    raw_path: str | Path = RAW_DATA_PATH,
    generated_path: str | Path = GENERATED_DATA_PATH,
) -> Path:
    """Generate factors from raw data, or select a legacy/manual factor CSV."""
    if manual_input:
        selected = Path(manual_input)
        if not selected.exists():
            raise FileNotFoundError(f"Factor data not found: {selected}")
        print(f"Manual factor data selected: {selected}")
        return selected

    raw_source = Path(raw_path)
    if raw_source.exists():
        print(f"Reading raw market data: {raw_source}")
        generated = generate_factor_data(raw_source, generated_path)
        print(f"Generated {len(generated)} factor rows: {generated_path}")
        return Path(generated_path)

    if LEGACY_MULTI_FACTOR_PATH.exists():
        print(
            f"Raw market data not found at {raw_source}; "
            f"using legacy data: {LEGACY_MULTI_FACTOR_PATH}"
        )
        return LEGACY_MULTI_FACTOR_PATH
    if LEGACY_SINGLE_FACTOR_PATH.exists():
        print(
            f"Raw market data not found at {raw_source}; "
            f"using legacy data: {LEGACY_SINGLE_FACTOR_PATH}"
        )
        return LEGACY_SINGLE_FACTOR_PATH
    raise FileNotFoundError("No raw or prepared factor data file was found")


def _factor_group(data: pd.DataFrame, factor_name: str) -> pd.DataFrame:
    """Convert one named factor to the evaluator's internal single-factor shape."""
    group = data[data["factor_name"].astype(str) == str(factor_name)].copy()
    value_column = "factor_value" if "factor_value" in group.columns else "factor"
    group["factor"] = group[value_column]
    return group


def _plot_representative_factor(data: pd.DataFrame, factor_name: str) -> None:
    """Create the standard plots for the highest-scoring factor."""
    group = _factor_group(data, factor_name)
    daily_ic = group.groupby("date").apply(calculate_daily_ic)
    _, _, long_short_return = calculate_group_return(group)
    plot_ic_curve(daily_ic)
    plot_long_short_curve(long_short_return)
    print(f"Visualization factor: {factor_name}")


def run_multi_factor_workflow(data: pd.DataFrame) -> None:
    factor_summary = run_factor_evaluation(data)
    if factor_summary.empty:
        raise ValueError("Factor evaluation returned no results")

    summary_dict = {}
    for factor_name, row in factor_summary.iterrows():
        summary_dict[str(factor_name)] = {
            "IC Mean": round(float(row["IC Mean"]), 4),
            "ICIR": round(float(row["ICIR"]), 4),
            "Rank IC Mean": round(float(row["Rank IC Mean"]), 4),
            "Long Short Return": round(float(row["Long Short Return"]), 4),
            "Sharpe Ratio": round(float(row["Sharpe Ratio"]), 4),
            "Max Drawdown": round(float(row["Max Drawdown"]), 4),
            "Win Rate": round(float(row["Win Rate"]), 4),
        }

    score_summary = evaluate_factor_scores(summary_dict)
    for factor_name, score_info in score_summary.items():
        summary_dict[factor_name]["factor_score"] = round(float(score_info["factor_score"]), 2)
        summary_dict[factor_name]["rating"] = score_info["rating"]

    ranking = sorted(
        score_summary.items(), key=lambda item: item[1]["factor_score"], reverse=True
    )
    print("\nFactor Ranking:")
    for index, (factor_name, info) in enumerate(ranking, start=1):
        print(f"{index}. {factor_name} Score {info['factor_score']:.1f}")

    os.makedirs("reports", exist_ok=True)
    with open("reports/factor_summary.json", "w", encoding="utf-8") as output:
        json.dump(summary_dict, output, indent=4, ensure_ascii=False)

    representative_factor = ranking[0][0]
    _plot_representative_factor(data, representative_factor)
    generate_markdown_report(summary_data=summary_dict)
    run_cross_sectional_research(data)
    print("Saved factor summary to reports/factor_summary.json")


def run_cross_sectional_research(data: pd.DataFrame) -> Path:
    """Generate V2 cross-sectional statistics while preserving legacy outputs."""
    processed = apply_factor_directions(
        preprocess_factors(data, normalization_method=DEFAULT_NORMALIZATION_METHOD)
    )
    processed["directed_value"] = processed["normalized_value"]
    if "forward_return_5d" not in processed and "return" in processed:
        processed["forward_return_5d"] = pd.to_numeric(processed["return"], errors="coerce")
    periods = [period for period in [1, 5, 10, 20, 40] if f"forward_return_{period}d" in processed]
    ic_summary = analyze_ic_decay(processed, periods=periods)
    pearson, spearman, redundant = average_factor_correlations(processed)
    plot_ic_decay(ic_summary, "reports/factor_ic_decay.png")
    plot_correlation_heatmap(spearman, "reports/factor_correlation_heatmap.png")
    quantile_means = {}
    for factor, group in processed.groupby("factor_name", sort=True):
        daily = calculate_quantile_returns(group, return_col="return")
        quantile_means[str(factor)] = daily.mean()
        safe_name = "".join(character if character.isalnum() or character in "-_" else "_" for character in str(factor))
        plot_quantile_curves(daily, str(factor), f"reports/quantile_return_{safe_name}.png")
    return generate_v2_report(
        sorted(processed["factor_name"].astype(str).unique()),
        ic_summary,
        pd.DataFrame(quantile_means).T,
        pearson,
        spearman,
        redundant,
    )


def run_single_factor_workflow(data: pd.DataFrame) -> None:
    daily_ic = data.groupby("date").apply(calculate_daily_ic)
    daily_rank_ic = data.groupby("date").apply(calculate_daily_rank_ic)
    icir = calculate_icir(daily_ic)
    top_return, bottom_return, long_short_return = calculate_group_return(data)
    sharpe_ratio = calculate_sharpe(long_short_return)
    max_drawdown = calculate_max_drawdown(long_short_return)
    win_rate = calculate_win_rate(long_short_return)

    generate_report(
        daily_ic,
        daily_rank_ic,
        icir,
        top_return,
        bottom_return,
        long_short_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
    )
    plot_ic_curve(daily_ic)
    plot_long_short_curve(long_short_return)


def run_workflow(data_path: str | Path, factors: list[str] | None = None) -> None:
    print(f"Reading factor data: {data_path}")
    data = pd.read_csv(data_path, dtype={"stock": str})
    if factors and "factor_name" in data:
        data = data[data["factor_name"].isin(factors)].copy()
        if data.empty:
            raise ValueError("Requested factor set is absent from the input")
    print(f"Loaded {len(data)} rows.")
    if "factor_name" in data.columns or "factor_value" in data.columns:
        run_multi_factor_workflow(data)
        if RAW_DATA_PATH.exists() and "forward_return_1d" in data.columns:
            raw = pd.read_csv(RAW_DATA_PATH, dtype={"stock": str})
            try:
                result = run_v3_research(raw, data)
                print(f"Saved V3 research report to {result['report']}")
            except ValueError as exc:
                print(f"V3 research skipped: {exc}")
    else:
        run_single_factor_workflow(data)


def run_interactive_stock_workflow() -> None:
    """Run the V2 single-stock experience when main.py has no arguments."""
    stock_code = input("请输入股票代码: ").strip()
    print(f"\n正在获取 {stock_code} 的行情并计算股票评分...")
    scores = evaluate_stock(stock_code)
    source = "AkShare" if scores["data_source"] == "akshare" else "Mock"
    print("\nStock Score:")
    print(f"Stock: {scores['stock']}")
    print(f"Technical Score: {scores['technical_score']:.2f}")
    print(f"Value Score: {scores['value_score']:.2f}")
    print(f"Quality Score: {scores['quality_score']:.2f}")
    print(f"Final Score: {scores['final_score']:.2f}")
    print(f"Data Source: {source}")
    financial_source = (
        "AkShare" if scores["financial_data_source"] == "akshare" else "Mock"
    )
    print(f"Financial Data Source: {financial_source}")
    print(f"Report: {scores['report_path']}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if len(sys.argv) == 1:
        run_interactive_stock_workflow()
        return

    if args.stocks:
        if args.input:
            parser.error("--stocks cannot be combined with --input")
        if not args.start or not args.end:
            parser.error("--stocks requires both --start and --end")
        print(
            f"Fetching {len(args.stocks)} stock(s) from {args.start} to {args.end}..."
        )
        market_data = fetch_and_save_stock_data(
            args.stocks,
            start_date=args.start,
            end_date=args.end,
            output_path=args.raw,
        )
        print(f"Fetched {len(market_data)} market-data rows: {args.raw}")
    elif args.start or args.end:
        parser.error("--start and --end can only be used together with --stocks")

    data_path = prepare_factor_data(args.input, args.raw, args.generated)
    if args.research_v3_real and args.universe != "ALL_A":
        parser.error("CSI300/CSI500 require a true dated constituent file; current constituents will not be backfilled")
    run_workflow(data_path, args.factors)


if __name__ == "__main__":
    main()
