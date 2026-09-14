"""V4 Phase 2: resumable, real-data A-share empirical research.

The command has two durable stages. ``--download-only`` fills the per-security
cache; a normal invocation resumes downloads and, once enough histories exist,
builds every requested research artifact. No synthetic or silent fallback data
is accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.factor_metadata import apply_factor_directions
from factor_analysis.research import analyze_ic_decay, calculate_daily_ic_series, calculate_quantile_returns, summarize_ic
from factor_analysis.sample_guard import assess_formal_research
from factor_engine.factor_builder import build_factor_data
from factor_processing import preprocess_factors
from scripts.run_real_research_pilot import fetch_real_price, fetch_real_stock_list, load_cached_real_price
from walk_forward.engine import WalkForwardConfig, run_walk_forward

FACTORS = ["momentum_20", "momentum_60", "volatility_20", "volatility_60", "volume_change_20"]
ROLLING_FACTORS = FACTORS[:4]
HORIZONS = [1, 5, 10, 20, 40]
QUANTILE_HORIZONS = [1, 5, 10, 20]


def _json(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def stable_sample(candidates: pd.DataFrame, count: int, seed: int) -> pd.DataFrame:
    """Select reproducibly by salted SHA256, independent of input row order."""
    clean = candidates.copy()
    clean = clean[~clean.stock_name.astype(str).str.upper().str.contains(r"\*?ST", regex=True)]
    clean["sample_hash"] = clean.stock.map(lambda x: hashlib.sha256(f"{seed}:{x}".encode()).hexdigest())
    return clean.sort_values(["sample_hash", "stock"]).head(count).reset_index(drop=True)


def _import_pilot_cache(code: str, price_dir: Path) -> bool:
    matches = sorted((ROOT / "cache/real_pilot/prices").glob(f"{code}_*.csv"))
    if not matches:
        return False
    frames, sources = [], []
    for source in matches:
        frame = load_cached_real_price(source)
        frames.append(frame)
        sources.append(str(source.relative_to(ROOT)))
    data = pd.concat(frames).drop_duplicates(["date", "stock"]).sort_values("date")
    target = price_dir / f"{code}.csv"
    data.to_csv(target, index=False, encoding="utf-8-sig")
    _json(target.with_suffix(".json"), {"stock": code, "source": "imported_real_pilot", "source_files": sources, "is_real_data": True, "coverage_start": str(data.date.min()), "coverage_end": str(data.date.max())})
    return True


def load_v4_cache(code: str, price_dir: Path) -> tuple[pd.DataFrame, dict] | None:
    path = price_dir / f"{code}.csv"
    if not path.exists() and not _import_pilot_cache(code, price_dir):
        return None
    meta_path = path.with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("is_real_data") is not True:
        raise RuntimeError(f"non-real V4 cache rejected: {path}")
    data = pd.read_csv(path, dtype={"stock": str})
    data["date"] = pd.to_datetime(data.date)
    return data, meta


def _covers_requested_range(data: pd.DataFrame, start: str, end: str, metadata: dict | None = None) -> bool:
    """Accept complete requests including securities listed after the start date."""
    meta = metadata or {}
    end_covered = data.date.max() >= pd.Timestamp(end) - pd.Timedelta(days=7)
    start_covered = data.date.min() <= pd.Timestamp(start) + pd.Timedelta(days=7)
    late_listing_download = meta.get("source") != "imported_real_pilot" and len(data) >= 161
    return bool(end_covered and (start_covered or late_listing_download))


def get_history(code: str, start: str, end: str, price_dir: Path) -> tuple[pd.DataFrame, dict, str]:
    """Resume a history, retaining imported pilot rows and recording every fallback."""
    cached = load_v4_cache(code, price_dir)
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    if cached is not None:
        data, meta = cached
        if _covers_requested_range(data, start, end, meta):
            return data[(data.date >= start_ts) & (data.date <= end_ts)], meta, "loaded from cache"
    fresh = fetch_real_price(code, start, end)
    fresh["date"] = pd.to_datetime(fresh.date)
    data = pd.concat([cached[0], fresh] if cached else [fresh], ignore_index=True)
    data = data.drop_duplicates(["date", "stock"], keep="last").sort_values("date")
    meta = {
        "stock": code, "source": fresh.attrs.get("source"), "is_real_data": True,
        "coverage_start": str(data.date.min().date()), "coverage_end": str(data.date.max().date()),
        "rows": len(data), "fallback": fresh.attrs.get("fallback"),
        "primary_error": fresh.attrs.get("primary_error"), "imported_pilot": cached is not None,
    }
    path = price_dir / f"{code}.csv"
    data.to_csv(path, index=False, encoding="utf-8-sig")
    _json(path.with_suffix(".json"), meta)
    return data[(data.date >= start_ts) & (data.date <= end_ts)], meta, "downloaded"


def download_universe(start: str, end: str, requested: int, seed: int, offline: bool = False) -> tuple[dict[str, pd.DataFrame], dict]:
    cache = ROOT / "cache/v4_full"; price_dir = cache / "prices"
    for name in ["prices", "metadata", "fundamentals", "exposures"]:
        (cache / name).mkdir(parents=True, exist_ok=True)
    source_list = fetch_real_stock_list(ROOT / "cache/real_pilot/a_share_list.csv")
    # Keep extra deterministic candidates so endpoint failures do not shrink the target.
    sampled = stable_sample(source_list, min(len(source_list), requested + max(50, requested // 2)), seed)
    sampled.to_csv(cache / "metadata/candidate_sample.csv", index=False, encoding="utf-8-sig")
    histories, failures, records = {}, {}, []
    for index, row in sampled.iterrows():
        if len(histories) >= requested:
            break
        code = row.stock
        try:
            cached = load_v4_cache(code, price_dir)
            covered = cached is not None and _covers_requested_range(cached[0], start, end, cached[1])
            if offline and not covered:
                raise FileNotFoundError("complete cached history unavailable in --offline mode")
            print(f"[{index + 1}/{requested}] {code} {'loaded from cache' if covered else 'downloading...'}", flush=True)
            data, meta, action = get_history(code, start, end, price_dir)
            if len(data) < 161:
                raise ValueError(f"only {len(data)} usable rows")
            histories[code] = data
            observed_start = pd.Timestamp(data.date.min())
            records.append({"stock": code, "stock_name": row.stock_name, "listing_date": str(observed_start.date()), "listing_date_quality": "exact_if_after_research_start_otherwise_left_censored", "cache_action": action, **meta})
        except Exception as exc:
            failures[code] = str(exc)
            print(f"[{index + 1}/{requested}] failed: {code}: {exc}", flush=True)
        _json(cache / "metadata/progress.json", {"requested_stock_count": requested, "successful_stock_count": len(histories), "failed_stock_count": len(failures), "failures": failures})
    pd.DataFrame(records).to_csv(cache / "metadata/selected_stocks.csv", index=False, encoding="utf-8-sig")
    return histories, {"requested_stock_count": requested, "successful_stock_count": len(histories), "failed_stock_count": len(failures), "failures": failures, "records": records}


def prepare_panel(histories: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    prices = pd.concat(histories.values(), ignore_index=True).sort_values(["stock", "date"])
    numeric = ["open", "high", "low", "close", "volume"]
    invalid = prices[numeric].isna().any(axis=1) | (prices["close"] <= 0) | (prices["volume"] < 0)
    invalid_rows = int(invalid.sum())
    prices = prices.loc[~invalid].copy()
    prices.to_csv(ROOT / "cache/v4_full/real_price_panel.csv", index=False, encoding="utf-8-sig")
    raw = build_factor_data(prices)
    raw = raw[raw.factor_name.isin(FACTORS)]
    raw.to_csv(ROOT / "cache/v4_full/real_factor_panel.csv", index=False, encoding="utf-8-sig")
    processed = apply_factor_directions(preprocess_factors(raw))
    processed["directed_value"] = processed["normalized_value"]
    processed["date"] = pd.to_datetime(processed.date)
    return prices, processed, invalid_rows


def yearly_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, annual in panel.groupby(panel.date.dt.year):
        for factor, group in annual.groupby("factor_name"):
            ic = calculate_daily_ic_series(group, "directed_value", "forward_return_5d")
            rank = calculate_daily_ic_series(group, "directed_value", "forward_return_5d", "spearman")
            sizes = group.drop_duplicates(["date", "stock"]).groupby("date").stock.nunique()
            rows.append({"year": int(year), "factor_name": factor, **summarize_ic(ic, rank), "effective_trading_days": len(rank), "average_cross_section_size": sizes.mean()})
    return pd.DataFrame(rows).sort_values(["factor_name", "year"])


def quantile_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for factor, group in panel.groupby("factor_name"):
        for horizon in QUANTILE_HORIZONS:
            daily = calculate_quantile_returns(group, return_col=f"forward_return_{horizon}d")
            means = daily.mean()
            qs = [means[f"Q{i}"] for i in range(1, 6)]
            rows.append({"factor_name": factor, "horizon": horizon, **means.to_dict(), "monotonicity": float(np.mean(np.diff(qs) > 0))})
    return pd.DataFrame(rows)


def rolling_analysis(panel: pd.DataFrame, output: Path) -> tuple[pd.DataFrame, dict]:
    frames, stability = [], {}
    for factor in ROLLING_FACTORS:
        group = panel[panel.factor_name == factor]
        daily = calculate_daily_ic_series(group, "directed_value", "forward_return_5d", "spearman")
        for window in [60, 120]:
            roll = daily.rolling(window, min_periods=window).mean()
            frames.append(pd.DataFrame({"date": roll.index, "factor_name": factor, "window": window, "rolling_mean_rank_ic": roll.values}))
            valid = roll.dropna(); expected_positive = not factor.startswith("momentum")
            stability[f"{factor}_{window}d_expected_sign_ratio"] = float(((valid > 0) if expected_positive else (valid < 0)).mean()) if len(valid) else None
    result = pd.concat(frames, ignore_index=True)
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for axis, window in zip(axes, [60, 120]):
        for factor, values in result[result.window == window].groupby("factor_name"):
            axis.plot(values.date, values.rolling_mean_rank_ic, label=factor)
        axis.axhline(0, color="grey", lw=.8); axis.set_title(f"Rolling {window}-day Mean Rank IC"); axis.legend(ncol=2)
    fig.tight_layout(); fig.savefig(output / "rolling_rank_ic.png", dpi=180); plt.close(fig)
    return result, stability


def correlation_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    wide = panel.pivot_table(index=["date", "stock"], columns="factor_name", values="directed_value")
    daily = [(date, frame.droplevel("date").corr(method="spearman")) for date, frame in wide.groupby(level="date")]
    rows = []
    for i, first in enumerate(FACTORS):
        for second in FACTORS[i + 1:]:
            values = pd.Series([matrix.loc[first, second] for _, matrix in daily if first in matrix and second in matrix]).dropna()
            mean = values.mean()
            rows.append({"factor_1": first, "factor_2": second, "mean_correlation": mean, "p95_absolute_correlation": values.abs().quantile(.95), "high_correlation_pair": bool(values.abs().quantile(.95) > .8)})
    return pd.DataFrame(rows)


def _annual_summary(yearly: pd.DataFrame, decay: pd.DataFrame) -> pd.DataFrame:
    full = decay[decay.period == 5].set_index("factor_name")
    rows = []
    for factor, group in yearly.groupby("factor_name"):
        values = group.set_index("year").mean_rank_ic
        full_value = full.loc[factor, "mean_rank_ic"]
        rows.append({"factor_name": factor, "full_period_mean_rank_ic": full_value, "yearly_same_sign_ratio": float((np.sign(values) == np.sign(full_value)).mean()), "best_year": int(values.idxmax()), "worst_year": int(values.idxmin()), "std_across_yearly_rank_ic": values.std(ddof=1)})
    return pd.DataFrame(rows)


def _reports(output: Path, quality: dict, yearly: pd.DataFrame, decay: pd.DataFrame, quantiles: pd.DataFrame, rolling_stability: dict, correlation: pd.DataFrame, wf_summary: pd.DataFrame, pilot: pd.DataFrame | None) -> None:
    annual_summary = _annual_summary(yearly, decay)
    five = decay[decay.period == 5].set_index("factor_name")
    vol = five.loc["volatility_20"]
    stability_table = annual_summary.set_index("factor_name")
    # All-sign-consistent factors are broken by signal strength relative to
    # across-year variation; this avoids an arbitrary row-order winner.
    stability_score = stability_table.yearly_same_sign_ratio * (
        stability_table.full_period_mean_rank_ic.abs()
        / stability_table.std_across_yearly_rank_ic.replace(0, np.nan)
    )
    stable_factor = stability_score.idxmax()
    vol_years = yearly[yearly.factor_name == "volatility_20"][["year", "mean_rank_ic"]]
    vol_q = quantiles[quantiles.factor_name == "volatility_20"]
    pilot_note = "Pilot comparison unavailable."
    if pilot is not None and not pilot.empty:
        row = pilot[(pilot.factor_name == "volatility_20") & (pilot.period == 5)]
        if len(row): pilot_note = f"Pilot 2024-2025 Rank IC={row.iloc[0].mean_rank_ic:.6f}; expanded sample={vol.mean_rank_ic:.6f}."
    wf_best = wf_summary.loc[wf_summary.annualized_return.idxmax(), "method"] if len(wf_summary) else "not run"
    low = f"""# Low-Volatility Study\n\n- Full-period volatility_20 Rank IC: {vol.mean_rank_ic:.6f}\n- Positive IC ratio: {vol.positive_ic_ratio:.3f}\n- Rolling expected-sign stability: {rolling_stability}\n- Most stable factor by yearly sign consistency, then |full Rank IC| / yearly standard deviation: {stable_factor}\n\n## Yearly Rank IC\n\n{vol_years.to_markdown(index=False)}\n\n## Factor decay\n\n{decay[decay.factor_name.str.startswith('volatility')].to_markdown(index=False)}\n\n## Quantiles\n\n{vol_q.to_markdown(index=False)}\n\n## Walk-forward contribution\n\nBest composite OOS method: {wf_best}. This is portfolio-level evidence, not an isolated causal contribution.\n\n## Pilot comparison\n\n{pilot_note}\n\n## Answer\n\nVolatility_20 {'remains' if stable_factor == 'volatility_20' else 'does not remain'} the most stable factor under the declared stability rule.\n"""
    (output / "low_volatility_study.md").write_text(low, encoding="utf-8")
    mom_decay = decay[decay.factor_name.str.startswith("momentum")]
    mom_yearly = yearly[yearly.factor_name.str.startswith("momentum")]
    all_negative = bool((mom_decay.mean_rank_ic < 0).all())
    yearly_negative = bool((mom_yearly.mean_rank_ic < 0).all())
    classification = "long-lasting reversal" if all_negative and yearly_negative else ("regime-dependent" if not yearly_negative else "short-term reversal")
    momentum = f"""# Momentum Study\n\n## Yearly evidence\n\n{mom_yearly.to_markdown(index=False)}\n\n## 1-40 day decay\n\n{mom_decay.to_markdown(index=False)}\n\n- Negative across every observed year: {yearly_negative}\n- Negative at every 1-40 day horizon: {all_negative}\n- Empirical classification: **{classification}**\n\nThis is an empirical label, not a causal explanation.\n"""
    (output / "momentum_study.md").write_text(momentum, encoding="utf-8")
    report = f"""# V4 Empirical Research Report\n\n## 1. Research Question\nStability of low-volatility and momentum signals, and translation into quantile and OOS performance.\n\n## 2. Data\n{quality['date_range'][0]} to {quality['date_range'][1]}; {quality['stock_count']} real A-share histories.\n\n## 3. Universe Construction\nStable SHA256 sample from a real current ALL_A list. Later listings enter only after their first observation. Historical delistings remain incomplete.\n\n## 4. Factors\n{', '.join(FACTORS)}. No financial factors.\n\n## 5. Methodology\nWinsorization, cross-sectional normalization, direction alignment, IC/Rank IC, quantiles and walk-forward. PIT exposure was unavailable, so neutralization was intentionally skipped.\n\n## 6. IC Results\n{annual_summary.to_markdown(index=False)}\n\n## 7. Factor Decay\nSee `factor_decay.csv`.\n\n## 8. Yearly Stability\nSee `yearly_factor_ic.csv`.\n\n## 9. Quantile Results\nSee `quantile_analysis.csv`.\n\n## 10. Regime Analysis\n{rolling_stability}\n\n## 11. Factor Correlation\n{correlation.to_markdown(index=False)}\n\n## 12. Walk-Forward OOS\n{wf_summary.to_markdown(index=False) if len(wf_summary) else 'Not run: sample threshold not met.'}\n\n## 13. Low-Volatility Finding\nSee `low_volatility_study.md`.\n\n## 14. Momentum Finding\nSee `momentum_study.md`.\n\n## 15. Limitations\nCurrent-list survivorship bias; listing dates at/before the research start are left-censored; no reliable PIT market-cap/industry exposures.\n\n## 16. Conclusion\nResearch validity: **{quality['formal_research_status']}**. Results are statistical associations and are not causal claims.\n"""
    (output / "v4_empirical_research_report.md").write_text(report, encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    output = ROOT / "reports/v4"; output.mkdir(parents=True, exist_ok=True)
    histories, download = download_universe(args.start_date, args.end_date, args.stock_count, args.seed, args.offline)
    if args.download_only:
        return download
    if len(histories) < args.min_stocks:
        raise RuntimeError(f"Only {len(histories)} valid histories; resume until --min-stocks {args.min_stocks} is met")
    prices, panel, invalid_price_rows = prepare_panel(histories)
    yearly = yearly_analysis(panel); yearly.to_csv(output / "yearly_factor_ic.csv", index=False, encoding="utf-8-sig")
    decay = analyze_ic_decay(panel, HORIZONS); decay.to_csv(output / "factor_decay.csv", index=False, encoding="utf-8-sig")
    quantiles = quantile_analysis(panel); quantiles.to_csv(output / "quantile_analysis.csv", index=False, encoding="utf-8-sig")
    rolling, rolling_stability = rolling_analysis(panel, output); rolling.to_csv(output / "rolling_rank_ic.csv", index=False, encoding="utf-8-sig")
    correlation = correlation_analysis(panel); correlation.to_csv(output / "factor_correlation.csv", index=False, encoding="utf-8-sig")
    sample = assess_formal_research(panel, len(histories))
    wf_summary = pd.DataFrame()
    if len(histories) >= 100:
        wf_summary, folds, equity = run_walk_forward(panel, config=WalkForwardConfig(train_window=756, test_window=126, min_train=756))
        folds.to_csv(output / "walk_forward_folds.csv", index=False, encoding="utf-8-sig")
        wf_summary.to_csv(output / "oos_strategy_comparison.csv", index=False, encoding="utf-8-sig")
        if len(equity):
            ax = (1 + equity.fillna(0)).cumprod().plot(figsize=(11, 6), title="V4 Walk-Forward OOS Equity")
            ax.figure.tight_layout(); ax.figure.savefig(output / "oos_equity.png", dpi=180); plt.close(ax.figure)
    sizes = panel.drop_duplicates(["date", "stock"]).groupby("date").stock.nunique()
    quality = {
        "stock_count": len(histories), "requested_stock_count": args.stock_count,
        "successful_stock_count": download["successful_stock_count"], "failed_stock_count": download["failed_stock_count"],
        "date_range": [str(panel.date.min().date()), str(panel.date.max().date())], "average_cross_section": float(sizes.mean()), "minimum_cross_section": int(sizes.min()),
        "survivorship_bias_status": "LIMITATION_CURRENT_LIST_HISTORICAL_DELISTINGS_INCOMPLETE",
        "listing_date_quality": "exact_if_after_research_start_otherwise_left_censored", "delisting_date_quality": "unavailable",
        "PIT_exposure_availability": False, "PIT_fundamental_availability": False, "mock_usage": False,
        "invalid_price_rows_removed": invalid_price_rows,
        "fallback_usage": sorted({r.get("fallback") for r in download["records"] if r.get("fallback")}),
        "sample_validity": sample["status"], "time_span_validity": sample["time_span_status"], "formal_research_status": sample["formal_status"],
    }
    _json(output / "research_data_quality.json", quality)
    pilot_path = ROOT / "reports/real_pilot/real_pilot_ic.csv"
    pilot = pd.read_csv(pilot_path) if pilot_path.exists() else None
    _reports(output, quality, yearly, decay, quantiles, rolling_stability, correlation, wf_summary, pilot)
    return quality


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2018-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--stock-count", type=int, default=200)
    parser.add_argument("--min-stocks", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20240911)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--offline", action="store_true", help="never access endpoints; analyze complete cached histories only")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
