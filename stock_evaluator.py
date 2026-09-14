"""End-to-end stock scoring built on the V2 data and factor layers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.factor_metadata import DEFAULT_NORMALIZATION_METHOD, apply_factor_directions
from factor_combination.static_weight import combine_static_weight
from factor_processing import preprocess_factors
from data_loader.stock_data import load_stock_data
from factor_engine.factor_builder import build_factor_data
from factor_engine.quality import calculate_quality_factor
from factor_engine.value import calculate_value_factors
from financial_loader.financial_data import load_financial_data


SCORE_FIELDS = ["momentum_score", "volatility_score", "volume_score"]
ACTIVE_WEIGHTS = {
    "momentum_score": 0.40,
    "volatility_score": 0.20,
    "volume_score": 0.20,
}
MULTIFACTOR_WEIGHTS = {
    "technical_score": 0.40,
    "value_score": 0.30,
    "quality_score": 0.30,
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


def calculate_stock_scores(
    factor_data: pd.DataFrame,
    stock_code: str | None = None,
    normalization_method: str = DEFAULT_NORMALIZATION_METHOD,
    combination_method: str = "static_weight",
) -> dict:
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

    if normalization_method == "time_series_percentile":
        momentum_score = (_latest_percentile(selected, "momentum_20") + _latest_percentile(selected, "momentum_60")) / 2
        volatility_score = (_latest_percentile(selected, "volatility_20", higher_is_better=False) + _latest_percentile(selected, "volatility_60", higher_is_better=False)) / 2
        volume_score = _latest_percentile(selected, "volume_change_20", target=1.2)
    else:
        latest_date = pd.to_datetime(factor_data["date"], errors="raise").max()
        latest = factor_data.loc[pd.to_datetime(factor_data["date"]) == latest_date].copy()
        processed = apply_factor_directions(preprocess_factors(latest, normalization_method))
        if normalization_method == "cross_sectional_zscore":
            processed["score_value"] = processed.groupby("factor_name")["normalized_value"].rank(pct=True) * 100
        else:
            processed["score_value"] = processed["normalized_value"]
        target_rows = processed[processed["stock"].astype(str).str.zfill(6) == code]
        lookup = target_rows.groupby("factor_name")["score_value"].mean()
        momentum_score = float(lookup.reindex(["momentum_20", "momentum_60"]).mean())
        volatility_score = float(lookup.reindex(["volatility_20", "volatility_60"]).mean())
        volume_score = float(lookup.get("volume_change_20", float("nan")))

    component_scores = {
        "momentum_score": momentum_score,
        "volatility_score": volatility_score,
        "volume_score": volume_score,
    }
    if combination_method == "equal_weight":
        final_score = float(pd.Series(component_scores).mean())
    elif combination_method == "static_weight":
        final_score = float(combine_static_weight(pd.DataFrame([component_scores]), ACTIVE_WEIGHTS).iloc[0])
    else:
        raise ValueError("combination_method must be 'equal_weight' or 'static_weight'")

    return {
        "stock": code,
        **{name: round(value, 2) for name, value in component_scores.items()},
        "final_score": round(final_score, 2),
    }


def _series_latest_percentile(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        raise ValueError("Financial factor has no valid values")
    return float(numeric.rank(method="average", pct=True).iloc[-1] * 100)


def calculate_multifactor_scores(
    technical_factor_data: pd.DataFrame,
    financial_data: pd.DataFrame,
    stock_code: str | None = None,
    normalization_method: str = DEFAULT_NORMALIZATION_METHOD,
) -> dict:
    """Combine V2 technical scoring with V3 value and quality scores."""
    technical = calculate_stock_scores(
        technical_factor_data, stock_code, normalization_method=normalization_method
    )
    code = technical["stock"]
    financial = financial_data.copy()
    if "stock" not in financial.columns:
        financial["stock"] = code
    if financial.empty or code not in set(financial["stock"].astype(str).str.zfill(6)):
        raise ValueError(f"Financial data does not contain stock {code}")
    financial["date"] = pd.to_datetime(financial["date"], errors="raise")
    financial = financial.sort_values(["stock", "date"]).reset_index(drop=True)
    financial = calculate_value_factors(financial)
    financial = calculate_quality_factor(financial)
    if normalization_method == "time_series_percentile":
        selected_financial = financial[financial["stock"].astype(str).str.zfill(6) == code]
        value_score = (_series_latest_percentile(selected_financial["pe_factor"]) + _series_latest_percentile(selected_financial["pb_factor"])) / 2
        quality_score = _series_latest_percentile(selected_financial["roe_factor"])
    else:
        latest = financial.groupby("stock", sort=False).tail(1).copy()
        long = latest.melt(
            id_vars=["stock"], value_vars=["pe_factor", "pb_factor", "roe_factor"],
            var_name="factor_name", value_name="factor_value",
        )
        long["date"] = pd.to_datetime(technical_factor_data["date"]).max()
        scored = apply_factor_directions(preprocess_factors(long, normalization_method))
        if normalization_method == "cross_sectional_zscore":
            scored["score_value"] = scored.groupby("factor_name")["normalized_value"].rank(pct=True) * 100
        else:
            scored["score_value"] = scored["normalized_value"]
        target = scored[scored["stock"].astype(str).str.zfill(6) == code].set_index("factor_name")["score_value"]
        value_score = float(target.reindex(["pe_factor", "pb_factor"]).mean())
        quality_score = float(target.get("roe_factor", float("nan")))
    component_scores = {
        "technical_score": technical["final_score"],
        "value_score": value_score,
        "quality_score": quality_score,
    }
    final_score = float(
        combine_static_weight(pd.DataFrame([component_scores]), MULTIFACTOR_WEIGHTS).iloc[0]
    )
    return {
        **technical,
        **{name: round(value, 2) for name, value in component_scores.items()},
        "final_score": round(final_score, 2),
    }


def generate_stock_report(
    scores: dict,
    data_source: str,
    output_path: str | Path = "reports/stock_report.md",
    financial_data_source: str | None = None,
) -> Path:
    """Write the stock score summary as a Markdown report."""
    source_label = "AkShare" if data_source.lower() == "akshare" else "Mock"
    if "technical_score" in scores:
        score_section = f"""- Technical Score: {scores['technical_score']:.2f}
- Value Score: {scores['value_score']:.2f}
- Quality Score: {scores['quality_score']:.2f}"""
    else:
        score_section = f"""- Momentum Score: {scores['momentum_score']:.2f}
- Volatility Score: {scores['volatility_score']:.2f}
- Volume Score: {scores['volume_score']:.2f}"""
    financial_source_label = (
        "AkShare" if (financial_data_source or "").lower() == "akshare" else "Mock"
    )
    data_source_section = f"Market: {source_label}"
    if financial_data_source is not None:
        data_source_section += f"\n\nFinancial: {financial_source_label}"

    content = f"""# Stock Evaluation Report

## Stock Information

股票代码：{scores['stock']}

## Factor Scores

{score_section}

## Final Stock Score

**{scores['final_score']:.2f} / 100**

## Data Source

{data_source_section}
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
    include_financial: bool = True,
) -> dict:
    """Load prices, build factors, score one stock, and generate its report."""
    prices = load_stock_data(stock_code, start_date=start_date, end_date=end_date)
    factor_data = build_factor_data(prices, stock_code=stock_code)
    if factor_data.empty:
        raise ValueError("Insufficient market history to calculate stock scores")
    financial_source = None
    if include_financial:
        financial_data = load_financial_data(stock_code)
        financial_source = financial_data.attrs.get("data_source", "mock")
        scores = calculate_multifactor_scores(factor_data, financial_data, stock_code)
    else:
        scores = calculate_stock_scores(factor_data, stock_code)
    scores["data_source"] = prices.attrs.get("data_source", "mock")
    if financial_source is not None:
        scores["financial_data_source"] = financial_source
    scores["report_path"] = str(
        generate_stock_report(
            scores, scores["data_source"], report_path, financial_source
        )
    )
    return scores
