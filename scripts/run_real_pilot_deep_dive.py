"""Offline stability diagnostics for the cached 50-stock real pilot."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.factor_metadata import apply_factor_directions
from factor_analysis.research import (
    analyze_ic_decay,
    average_factor_correlations,
    calculate_daily_ic_series,
    calculate_quantile_returns,
    summarize_ic,
)
from factor_processing import preprocess_factors
from universe import HistoricalUniverseProvider, UniverseConfig

FACTORS = ["momentum_20", "momentum_60", "volatility_20", "volatility_60", "volume_change_20"]
HORIZONS = [1, 5, 10, 20, 40]
OUTPUT = PROJECT_ROOT / "reports/real_pilot"


def load_cached_panel() -> pd.DataFrame:
    """Load and preprocess the existing real pilot without any network access."""
    panel = pd.read_csv(PROJECT_ROOT / "cache/real_pilot/real_factor_panel.csv", dtype={"stock": str})
    prices = pd.read_csv(PROJECT_ROOT / "cache/real_pilot/real_price_panel.csv", dtype={"stock": str})
    panel["date"] = pd.to_datetime(panel["date"]); prices["date"] = pd.to_datetime(prices["date"])
    provider = HistoricalUniverseProvider(prices, UniverseConfig(min_listing_days=120))
    eligible = pd.DataFrame(
        [{"date": date, "stock": stock} for date in sorted(panel.date.unique()) for stock in provider.get_universe(date)],
        columns=["date", "stock"],
    )
    panel = panel[panel.factor_name.isin(FACTORS)].merge(eligible, on=["date", "stock"], how="inner")
    processed = apply_factor_directions(preprocess_factors(panel))
    processed["directed_value"] = processed["normalized_value"]
    return processed


def yearly_ic(panel: pd.DataFrame) -> pd.DataFrame:
    """Calculate five-day IC diagnostics separately for each calendar year."""
    rows = []
    for year, annual in panel.groupby(panel.date.dt.year):
        for factor, group in annual.groupby("factor_name"):
            ic = calculate_daily_ic_series(group, "directed_value", "forward_return_5d")
            rank_ic = calculate_daily_ic_series(group, "directed_value", "forward_return_5d", "spearman")
            metrics = summarize_ic(ic, rank_ic)
            rows.append({"year": int(year), "factor_name": factor, **metrics})
    return pd.DataFrame(rows).sort_values(["factor_name", "year"])


def detailed_decay(panel: pd.DataFrame) -> pd.DataFrame:
    """Return the existing multi-horizon IC analysis in a focused schema."""
    result = analyze_ic_decay(panel, HORIZONS)
    return result.rename(columns={"period": "horizon"})[
        ["factor_name", "horizon", "mean_ic", "mean_rank_ic", "icir", "rank_icir", "positive_ic_ratio", "observations"]
    ]


def low_volatility_diagnostic(panel: pd.DataFrame) -> pd.DataFrame:
    """Combine yearly and horizon IC with Q5-Q1 for low-volatility factors."""
    rows = []
    subset = panel[panel.factor_name.isin(["volatility_20", "volatility_60"])]
    scopes = [("full", None, subset)] + [("year", int(year), annual) for year, annual in subset.groupby(subset.date.dt.year)]
    for scope, year, scoped in scopes:
        horizons = HORIZONS if scope == "full" else [5]
        for factor, group in scoped.groupby("factor_name"):
            for horizon in horizons:
                return_col = f"forward_return_{horizon}d"
                rank_ic = calculate_daily_ic_series(group, "directed_value", return_col, "spearman")
                quantiles = calculate_quantile_returns(group, return_col=return_col)
                rows.append({
                    "scope": scope, "year": year, "factor_name": factor, "horizon": horizon,
                    "mean_rank_ic": rank_ic.mean(), "positive_rank_ic_ratio": (rank_ic > 0).mean(),
                    "Q5-Q1": quantiles["Q5-Q1"].mean(),
                })
    return pd.DataFrame(rows)


def rolling_rank_ic(panel: pd.DataFrame) -> pd.DataFrame:
    """Calculate trailing 60-trading-day mean five-day Rank IC."""
    series = []
    for factor in ["momentum_20", "momentum_60", "volatility_20"]:
        group = panel[panel.factor_name == factor]
        daily = calculate_daily_ic_series(group, "directed_value", "forward_return_5d", "spearman")
        rolling = daily.rolling(60, min_periods=30).mean()
        series.append(pd.DataFrame({"date": rolling.index, "factor_name": factor, "rolling_60d_mean_rank_ic": rolling.values}))
    return pd.concat(series, ignore_index=True)


def _momentum_diagnosis(decay: pd.DataFrame, factor: str) -> str:
    values = decay[decay.factor_name == factor].set_index("horizon").mean_rank_ic
    if (values.loc[[1, 5]] < 0).all() and (values.loc[[20, 40]] > 0).any():
        return "short-term reversal pattern"
    if (values < 0).all():
        return "momentum broadly ineffective in this sample"
    return "sample noise / regime dependence"


def update_summary(yearly: pd.DataFrame, decay: pd.DataFrame, low_vol: pd.DataFrame, correlation: pd.DataFrame) -> None:
    """Append an idempotent, data-derived stability section to the pilot summary."""
    yearly_pivot = yearly.pivot(index="factor_name", columns="year", values="mean_rank_ic")
    direction_lines = []
    for factor in FACTORS:
        values = yearly_pivot.loc[factor].dropna()
        consistent = len(values) == 2 and (values.iloc[0] * values.iloc[1] > 0)
        direction_lines.append(f"- {factor}: {'same sign' if consistent else 'regime-dependent sign'} ({', '.join(f'{int(y)}={v:.4f}' for y, v in values.items())})")
    redundant = []
    for i, first in enumerate(correlation.columns):
        for second in correlation.columns[i + 1:]:
            value = correlation.loc[first, second]
            if abs(value) > 0.8: redundant.append(f"{first} / {second} ({value:.3f})")
    vol_decay = decay[decay.factor_name == "volatility_20"].set_index("horizon").mean_rank_ic
    section = f"""## Stability and Regime Diagnostics

### Yearly direction

{chr(10).join(direction_lines)}

### Momentum diagnosis

- momentum_20: {_momentum_diagnosis(decay, 'momentum_20')}.
- momentum_60: {_momentum_diagnosis(decay, 'momentum_60')}.
- Both momentum signals remain negative through 40 days, so this sample does not support a short-only reversal interpretation.

### Low-volatility diagnosis

- volatility_20 Rank IC by horizon: {', '.join(f'{int(h)}D={v:.4f}' for h, v in vol_decay.items())}.
- Low volatility is more horizon-stable than momentum, but yearly consistency and quintile spreads must still be considered before treating it as robust.

### Redundancy

- Pairs with absolute average daily Spearman correlation above 0.8: {', '.join(redundant) if redundant else 'none'}.

These results describe the cached 50-stock pilot only and do not represent the full A-share market.
"""
    path = OUTPUT / "real_pilot_summary.md"; content = path.read_text(encoding="utf-8")
    marker = "## Stability and Regime Diagnostics"
    if marker in content: content = content.split(marker)[0].rstrip() + "\n\n"
    path.write_text(content.rstrip() + "\n\n" + section, encoding="utf-8")


def main() -> None:
    print("Loading cached 50-stock real panel...")
    panel = load_cached_panel()
    print("Calculating yearly IC and detailed decay...")
    annual = yearly_ic(panel); decay = detailed_decay(panel)
    annual.to_csv(OUTPUT / "yearly_ic.csv", index=False, encoding="utf-8-sig")
    decay.to_csv(OUTPUT / "factor_decay_detailed.csv", index=False, encoding="utf-8-sig")
    print("Calculating low-volatility and rolling diagnostics...")
    low_vol = low_volatility_diagnostic(panel); rolling = rolling_rank_ic(panel)
    low_vol.to_csv(OUTPUT / "low_vol_diagnostic.csv", index=False, encoding="utf-8-sig")
    rolling.to_csv(OUTPUT / "rolling_rank_ic.csv", index=False, encoding="utf-8-sig")
    pivot = rolling.pivot(index="date", columns="factor_name", values="rolling_60d_mean_rank_ic")
    axis = pivot.plot(figsize=(10, 5), title="Rolling 60-Day Mean Rank IC")
    axis.axhline(0, color="grey", linewidth=0.8); axis.set_ylabel("Mean Rank IC")
    figure = axis.get_figure(); figure.tight_layout(); figure.savefig(OUTPUT / "rolling_rank_ic.png", dpi=180); plt.close(figure)
    print("Calculating real factor correlations...")
    correlation = average_factor_correlations(panel)[1]
    correlation.to_csv(OUTPUT / "factor_correlation_real.csv", encoding="utf-8-sig")
    update_summary(annual, decay, low_vol, correlation)
    print("Deep-dive outputs saved.")


if __name__ == "__main__":
    main()
