"""Artifacts for the V2 cross-sectional factor research report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_ic_decay(summary: pd.DataFrame, output_path: str | Path) -> Path:
    """Plot mean rank IC against holding period for every factor."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(9, 5))
    for factor, group in summary.groupby("factor_name"):
        axis.plot(group["period"], group["mean_rank_ic"], marker="o", label=factor)
    axis.axhline(0, color="grey", linewidth=0.8)
    axis.set(xlabel="Holding period (days)", ylabel="Mean Rank IC", title="Factor IC Decay")
    if not summary.empty:
        axis.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(destination, dpi=180); plt.close(fig)
    return destination


def plot_correlation_heatmap(matrix: pd.DataFrame, output_path: str | Path) -> Path:
    """Plot an annotated factor correlation heatmap without extra dependencies."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(8, 7))
    if matrix.empty:
        axis.text(0.5, 0.5, "Insufficient cross-sectional data", ha="center")
        axis.axis("off")
    else:
        image = axis.imshow(matrix.values, vmin=-1, vmax=1, cmap="coolwarm")
        axis.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
        axis.set_yticks(range(len(matrix.index)), matrix.index)
        fig.colorbar(image, ax=axis)
    axis.set_title("Average Daily Spearman Factor Correlation")
    fig.tight_layout(); fig.savefig(destination, dpi=180); plt.close(fig)
    return destination


def plot_quantile_curves(daily: pd.DataFrame, factor: str, output_path: str | Path) -> Path:
    """Plot cumulative Q1..Q5 and Q5-Q1 forward-return curves."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cumulative = (1 + daily.fillna(0)).cumprod() - 1
    axis = cumulative.plot(figsize=(9, 5), title=f"Quantile Returns: {factor}")
    axis.set(xlabel="Date", ylabel="Cumulative return")
    figure = axis.get_figure(); figure.tight_layout(); figure.savefig(destination, dpi=180); plt.close(figure)
    return destination


def generate_v2_report(
    factors: list[str], ic_summary: pd.DataFrame, quantile_means: pd.DataFrame,
    pearson: pd.DataFrame, spearman: pd.DataFrame, redundant: pd.DataFrame,
    output_path: str | Path = "reports/factor_research_v2_report.md",
    normalization_method: str = "cross_sectional_zscore",
) -> Path:
    """Write the complete V2 cross-sectional research report."""
    destination = Path(output_path); destination.parent.mkdir(parents=True, exist_ok=True)
    ic_table = ic_summary.to_markdown(index=False) if not ic_summary.empty else "No valid IC observations."
    quantile_table = quantile_means.to_markdown() if not quantile_means.empty else "No valid quantile observations."
    redundant_text = redundant.to_markdown(index=False) if not redundant.empty else "No pairs above |0.8|."
    factor_lines = "\n".join(f"- {factor}" for factor in factors)
    content = f"""# Factor Research V2 Report

## 1. Research universe

All stocks present in the input on each trading date; this is a data-defined universe and may carry survivorship bias.

## 2. Factor definitions

{factor_lines}

## 3. Preprocessing method

Daily, per-factor percentile winsorization at 1%/99%, followed by direction alignment.

## 4. Normalization method

`{normalization_method}`. Statistics use only the same-date stock cross-section.

## 5. IC / Rank IC summary

{ic_table}

## 6. IC significance

The table reports conventional t-statistics and normal-approximation two-sided p-values. Newey-West HAC is not applied.

## 7. IC decay

![Factor IC decay](factor_ic_decay.png)

## 8. Quantile returns

{quantile_table}

## 9. Q5-Q1 spread

Q5 is the high/desirable factor group after direction alignment. The table and factor-specific charts report Q5 minus Q1.

## 10. Factor correlation

![Factor correlation](factor_correlation_heatmap.png)

Potential redundant factors (absolute mean daily Spearman correlation above 0.8):

{redundant_text}

## 11. Composite score method

Baseline static category weights are technical 0.4, value 0.3, and quality 0.3. Static weights are normalized by the sum of absolute weights; equal weighting is also supported.

## 12. Limitations

- The CSV fallback may contain only a 5-day forward return, so unavailable horizons are omitted.
- The input universe is not yet point-in-time constituent data and may have survivorship bias.
- Industry/size neutralization, trading suspensions, limit-up/down constraints, and HAC inference remain future work.
"""
    destination.write_text(content, encoding="utf-8")
    return destination
