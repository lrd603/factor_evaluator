"""End-to-end stock scoring built on the V2 data and factor layers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_loader.stock_data import load_stock_data
from factor_engine.factor_builder import build_factor_data


SCORE_FIELDS = ["momentum_score", "volatility_score", "volume_score"]
ACTIVE_WEIGHTS = {
    "momentum_score": 0.40,
    "volatility_score": 0.20,
    "volume_score": 0.20,
}


def _latest_percentile(
    factor_data: pd.DataFrame,
    factor_name: str,
    *,
    higher_is_better: bool = True,
    target: float | None = None,
) -> float:
    group = factor_data[factor_data["factor_name"] == factor_name].copy()
    if group.empty:
        raise ValueError(f"Factor data does not contain {factor_name!r}")
    group["date"] = pd.to_datetime(group["date"], errors="raise")
    group["factor_value"] = pd.to_numeric(group["factor_value"], errors="raise")
    group = group.dropna(subset=["factor_value"]).sort_values("date")
    if group.empty:
        raise ValueError(f"Factor {factor_name!r} has no valid values")

    values = group["factor_value"]
    if target is not None:
        desirability = -(values - target).abs()
    elif higher_is_better:
        desirability = values
    else:
        desirability = -values
    return float(desirability.rank(method="average", pct=True).iloc[-1] * 100)


def calculate_stock_scores(factor_data: pd.DataFrame, stock_code: str | None = None) -> dict:
    """Convert the latest normalized factor readings into a 0–100 stock score."""
    required = {"date", "stock", "factor_name", "factor_value", "return"}
    missing = required - set(factor_data.columns)
    if missing:
        raise ValueError(f"Factor data is missing columns: {sorted(missing)}")
    if factor_data.empty:
        raise ValueError("Factor data must not be empty")

    stocks = factor_data["stock"].astype(str).str.zfill(6)
    code = str(stock_code).strip().zfill(6) if stock_code is not None else stocks.iloc[0]
    selected = factor_data.loc[stocks == code].copy()
    if selected.empty:
        raise ValueError(f"Factor data does not contain stock {code}")

    momentum_score = (
        _latest_percentile(selected, "momentum_20")
        + _latest_percentile(selected, "momentum_60")
    ) / 2
    volatility_score = (
        _latest_percentile(selected, "volatility_20", higher_is_better=False)
        + _latest_percentile(selected, "volatility_60", higher_is_better=False)
    ) / 2
    # A moderate expansion to roughly 1.2 times the 20-day mean is preferred;
    # both unusually weak and abnormally large volume receive lower ranks.
    volume_score = _latest_percentile(selected, "volume_change_20", target=1.2)

    component_scores = {
        "momentum_score": momentum_score,
        "volatility_score": volatility_score,
        "volume_score": volume_score,
    }
    active_weight = sum(ACTIVE_WEIGHTS.values())
    final_score = sum(
        component_scores[name] * weight for name, weight in ACTIVE_WEIGHTS.items()
    ) / active_weight

    return {
        "stock": code,
        **{name: round(value, 2) for name, value in component_scores.items()},
        "final_score": round(final_score, 2),
    }


def generate_stock_report(
    scores: dict,
    data_source: str,
    output_path: str | Path = "reports/stock_report.md",
) -> Path:
    """Write the stock score summary as a Markdown report."""
    source_label = "AkShare" if data_source.lower() == "akshare" else "Mock"
    content = f"""# Stock Evaluation Report

## Stock Information

股票代码：{scores['stock']}

## Factor Scores

- Momentum Score: {scores['momentum_score']:.2f}
- Volatility Score: {scores['volatility_score']:.2f}
- Volume Score: {scores['volume_score']:.2f}

## Final Stock Score

**{scores['final_score']:.2f} / 100**

## Data Source

{source_label}
"""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination


def evaluate_stock(
    stock_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    report_path: str | Path = "reports/stock_report.md",
) -> dict:
    """Load prices, build factors, score one stock, and generate its report."""
    prices = load_stock_data(stock_code, start_date=start_date, end_date=end_date)
    factor_data = build_factor_data(prices, stock_code=stock_code)
    if factor_data.empty:
        raise ValueError("Insufficient market history to calculate stock scores")
    scores = calculate_stock_scores(factor_data, stock_code)
    scores["data_source"] = prices.attrs.get("data_source", "mock")
    scores["report_path"] = str(
        generate_stock_report(scores, scores["data_source"], report_path)
    )
    return scores
