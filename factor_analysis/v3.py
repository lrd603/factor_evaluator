"""Second-stage research orchestration and reporting."""

from __future__ import annotations

from pathlib import Path
import json
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config.factor_metadata import apply_factor_directions
from factor_analysis.research import analyze_ic_decay, average_factor_correlations
from factor_analysis.sample_guard import assess_research_sample
from data_loader.exposures import build_exposures
from data_loader.market_metadata import enrich_market_metadata
from factor_neutralization import NeutralizationConfig, neutralization_diagnostics, neutralize_factors
from factor_processing import preprocess_factors
from universe import HistoricalUniverseProvider, UniverseConfig
from walk_forward import WalkForwardConfig, run_walk_forward

logger = logging.getLogger(__name__)


def _markdown(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False) if not frame.empty else "No valid observations."


def run_v3_research(
    raw_market_data: pd.DataFrame,
    factor_data: pd.DataFrame,
    output_path: str | Path = "reports/factor_research_v3_report.md",
    universe_config: UniverseConfig | None = None,
    neutralization_config: NeutralizationConfig | None = None,
    walk_config: WalkForwardConfig | None = None,
) -> dict[str, object]:
    """Run dynamic-universe, exposure and OOS diagnostics on local data."""
    universe_settings = universe_config or UniverseConfig()
    enriched_market, trading_quality = enrich_market_metadata(raw_market_data)
    exposed_market, exposure_quality = build_exposures(enriched_market)
    provider = HistoricalUniverseProvider(exposed_market, universe_settings)
    factors = factor_data.copy(); factors["date"] = pd.to_datetime(factors["date"])
    eligible_rows = []
    for date in sorted(factors["date"].unique()):
        eligible_rows.extend({"date": pd.Timestamp(date), "stock": stock} for stock in provider.get_universe(date))
    eligible = pd.DataFrame(eligible_rows, columns=["date", "stock"])
    factors["stock"] = factors["stock"].astype(str).str.zfill(6)
    filtered = factors.merge(eligible, on=["date", "stock"], how="inner")
    if filtered.empty:
        raise ValueError("No factor observations overlap the point-in-time universe")
    exposure_columns = [column for column in ["market_cap", "industry", "is_st", "is_suspended", "limit_up", "limit_down", "amount"] if column in exposed_market]
    filtered = filtered.merge(exposed_market[["date", "stock", *exposure_columns]].drop_duplicates(["date", "stock"]), on=["date", "stock"], how="left")
    processed = preprocess_factors(filtered)
    processed["pre_neutral_value"] = processed["normalized_value"]
    neutralized = neutralize_factors(processed, config=neutralization_config or NeutralizationConfig())
    diagnostics = neutralization_diagnostics(neutralized)
    neutralized["normalized_value"] = neutralized["neutralized_value"]
    directed = apply_factor_directions(neutralized)
    directed["directed_value"] = directed["normalized_value"]
    before = apply_factor_directions(processed.assign(normalized_value=processed["pre_neutral_value"]))
    before["directed_value"] = before["normalized_value"]
    periods = [p for p in [1, 5, 10, 20, 40] if f"forward_return_{p}d" in directed]
    pre_ic = analyze_ic_decay(before, periods)
    post_ic = analyze_ic_decay(directed, periods)
    pre_corr = average_factor_correlations(before)[1]
    post_corr = average_factor_correlations(directed)[1]
    settings = walk_config or WalkForwardConfig()
    comparison, folds, equity_returns = run_walk_forward(directed, config=settings)
    equity = (1 + equity_returns.fillna(0)).cumprod() if not equity_returns.empty else equity_returns
    destination = Path(output_path); destination.parent.mkdir(parents=True, exist_ok=True)
    equity_path = destination.parent / "walk_forward_oos_equity.png"
    if not equity.empty:
        axis = equity.plot(figsize=(9, 5), title="Combined Walk-Forward OOS Equity")
        axis.set(xlabel="Date", ylabel="Growth of 1")
        figure = axis.get_figure(); figure.tight_layout(); figure.savefig(equity_path, dpi=180); plt.close(figure)
    statuses = directed.get("neutralization_status", pd.Series(dtype=str)).value_counts().to_dict()
    sample_quality = assess_research_sample(directed)
    warnings = list(dict.fromkeys([*provider.metadata.warnings, *trading_quality.get("warnings", []), *exposure_quality.get("warnings", [])]))
    for warning in warnings:
        logger.warning("research fallback: %s", warning)
    data_quality = {"universe": provider.metadata.to_dict(), "fundamentals_point_in_time": "source_dependent; mock=false", "industry_point_in_time": exposure_quality.get("industry_point_in_time", False), "market_cap_point_in_time": exposure_quality.get("market_cap_point_in_time", False), "trading_constraints": trading_quality, "survivorship_bias_status": provider.metadata.survivorship_bias_status, "sample_size": sample_quality, "fallback_warnings": warnings}
    (destination.parent / "research_data_quality.json").write_text(json.dumps(data_quality, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    content = f"""# Factor Research V3 Report

> **Research validity status: {sample_quality['status']}**  
> Median daily cross-section: {sample_quality['median_cross_section_size']:.0f}. Results below 30 stocks are engineering smoke-test output, not investment conclusions.

## 1. Universe construction

The universe is reconstructed on every factor date from stocks actually present in the input history. Minimum trading history: {universe_settings.min_listing_days} observations. Missing close/volume and zero-volume observations are excluded; optional ADV20 is {universe_settings.min_adv20}.

## 2. Survivorship-bias handling

Stocks cannot enter before their first input observation and eligibility changes over time. Historical index constituents are not available, so survivorship bias is reduced but **not fully eliminated**. Data quality: `{provider.data_quality}`.

## 3. Fundamental point-in-time handling

ROE uses announcement-date as-of alignment where `NOTICE_DATE` exists. Mock or sources without announcement dates are marked `point_in_time_available=False`; they must not be described as PIT-clean.

## 4. Neutralization methodology

Daily OLS residual: `factor = alpha + beta * log(market_cap) + industry dummies + epsilon`. Dummy encoding drops the first category. Missing exposures and insufficient samples explicitly fall back. Status counts: `{statuses}`.

Exposure-reduction diagnostics:

{_markdown(diagnostics)}

Pre-neutralization IC:

{_markdown(pre_ic)}

Post-neutralization IC:

{_markdown(post_ic)}

Pre-neutralization mean Spearman correlation:

{pre_corr.to_markdown() if not pre_corr.empty else 'Unavailable.'}

Post-neutralization mean Spearman correlation:

{post_corr.to_markdown() if not post_corr.empty else 'Unavailable.'}

## 5. Rolling factor weighting

Rolling IC/ICIR estimators shift daily IC by one trading day before rolling. Insufficient history falls back to equal weight.

## 6. Walk-forward design

Mode: {settings.mode}; train window: {settings.train_window}; test window: {settings.test_window}; minimum training history: {settings.min_train}. Train ends strictly before test begins and fold weights remain fixed during each test block.

Fold-level IS and OOS metrics:

{_markdown(folds.drop(columns=['train_weights'], errors='ignore'))}

## 7. IS vs OOS comparison

Training data estimates weights only. The strategy table below is combined OOS performance; no test-period outcome is used for its fold parameters.

![Combined OOS equity](walk_forward_oos_equity.png)

## 8. Strategy comparison

{_markdown(comparison)}

## 9. Trading constraints

Zero volume and explicit suspension flags are excluded when available. ST and limit-up/limit-down constraints are applied only when trustworthy fields exist; the current local CSV lacks these fields, so they are reported rather than inferred.

## 10. Remaining limitations

- No reliable point-in-time CSI 300/CSI 500 constituent history.
- Current local CSV lacks industry, market capitalization, ST, explicit suspension, and price-limit flags.
- Financial mock data has no real announcement dates.
- Walk-forward results on a three-stock local sample are smoke-test evidence, not investable evidence.
- All fallbacks are recorded in `research_data_quality.json`: `{warnings}`.
"""
    destination.write_text(content, encoding="utf-8")
    return {"report": destination, "comparison": comparison, "folds": folds, "equity_curve": equity, "filtered_factors": directed, "data_quality": data_quality, "neutralization_diagnostics": diagnostics}
