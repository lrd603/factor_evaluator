"""Cross-sectional IC analysis for technical and financial factors."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SUPPORTED_FACTORS = [
    "momentum_20",
    "momentum_60",
    "volatility_20",
    "volatility_60",
    "volume_change_20",
    "PE",
    "PB",
    "ROE",
]
REQUIRED_COLUMNS = ["date", "stock", "factor_name", "factor_value", "return"]


def _daily_correlations(group: pd.DataFrame) -> tuple[float, float] | None:
    clean = group[["stock", "factor_value", "return"]].dropna()
    if clean["stock"].nunique() < 2:
        return None
    if clean["factor_value"].nunique() < 2 or clean["return"].nunique() < 2:
        return None
    return (
        float(clean["factor_value"].corr(clean["return"])),
        float(clean["factor_value"].corr(clean["return"], method="spearman")),
    )


def analyze_factor_ic(factor_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate IC Mean, Rank IC Mean and ICIR for each supported factor."""
    missing = set(REQUIRED_COLUMNS) - set(factor_data.columns)
    if missing:
        raise ValueError(f"Factor data is missing columns: {sorted(missing)}")
    if factor_data.empty:
        raise ValueError("Factor data must not be empty")

    data = factor_data[REQUIRED_COLUMNS].copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["factor_value"] = pd.to_numeric(data["factor_value"], errors="coerce")
    data["return"] = pd.to_numeric(data["return"], errors="coerce")
    data = data[data["factor_name"].isin(SUPPORTED_FACTORS)]
    if data.empty:
        raise ValueError("Factor data contains no supported factors")

    rows = []
    for factor_name, factor_group in data.groupby("factor_name", sort=False):
        correlations = []
        for _, daily_group in factor_group.groupby("date", sort=True):
            result = _daily_correlations(daily_group)
            if result is not None:
                correlations.append(result)
        if not correlations:
            continue
        daily = pd.DataFrame(correlations, columns=["ic", "rank_ic"])
        standard_deviation = float(daily["ic"].std(ddof=1))
        ic_mean = float(daily["ic"].mean())
        icir = ic_mean / standard_deviation if standard_deviation > 1e-12 else 0.0
        rows.append(
            {
                "Factor": factor_name,
                "IC Mean": ic_mean,
                "Rank IC Mean": float(daily["rank_ic"].mean()),
                "ICIR": icir,
                "Observations": len(daily),
            }
        )
    if not rows:
        raise ValueError("No valid cross-sectional IC observations were generated")
    result = pd.DataFrame(rows)
    result["_strength"] = result["ICIR"].abs()
    result = result.sort_values(["_strength", "Factor"], ascending=[False, True])
    result.insert(0, "Rank", range(1, len(result) + 1))
    return result.drop(columns="_strength").reset_index(drop=True)


def generate_ic_report(
    analysis: pd.DataFrame,
    output_path: str | Path = "reports/factor_ic_report.md",
) -> Path:
    """Write factor IC metrics and ranking to a Markdown report."""
    required = {"Rank", "Factor", "IC Mean", "Rank IC Mean", "ICIR"}
    missing = required - set(analysis.columns)
    if missing:
        raise ValueError(f"IC analysis is missing columns: {sorted(missing)}")
    lines = [
        "# Factor IC Report",
        "",
        "Factors are ranked by absolute ICIR; a negative IC indicates an inverse signal.",
        "",
        "| Rank | Factor | IC Mean | Rank IC Mean | ICIR |",
        "|---:|---|---:|---:|---:|",
    ]
    for _, row in analysis.iterrows():
        lines.append(
            f"| {int(row['Rank'])} | {row['Factor']} | {row['IC Mean']:.4f} | "
            f"{row['Rank IC Mean']:.4f} | {row['ICIR']:.4f} |"
        )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination
