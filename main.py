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
from factors.generator import generate_factor_data


RAW_DATA_PATH = Path("data/raw_stock_data.csv")
GENERATED_DATA_PATH = Path("data/factor_data_generated.csv")
LEGACY_MULTI_FACTOR_PATH = Path("data/factor_data_multi.csv")
LEGACY_SINGLE_FACTOR_PATH = Path("data/factor_data.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the factor evaluation workflow.")
    parser.add_argument(
        "--input",
        help="Use a prepared factor CSV and skip factor generation.",
    )
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
    print("Saved factor summary to reports/factor_summary.json")


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


def run_workflow(data_path: str | Path) -> None:
    print(f"Reading factor data: {data_path}")
    data = pd.read_csv(data_path, dtype={"stock": str})
    print(f"Loaded {len(data)} rows.")
    if "factor_name" in data.columns or "factor_value" in data.columns:
        run_multi_factor_workflow(data)
    else:
        run_single_factor_workflow(data)


def main() -> None:
    args = build_parser().parse_args()
    data_path = prepare_factor_data(args.input, args.raw, args.generated)
    run_workflow(data_path)


if __name__ == "__main__":
    main()
