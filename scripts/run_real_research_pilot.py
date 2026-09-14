"""Small, reproducible, real-data A-share cross-sectional research pilot.

No mock data is accepted. Every cached price file has a provenance sidecar.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from pathlib import Path
import random
import sys
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.factor_metadata import apply_factor_directions
from factor_analysis.reporting import plot_ic_decay, plot_quantile_curves
from factor_analysis.research import analyze_ic_decay, calculate_quantile_returns
from factor_analysis.sample_guard import assess_research_sample
from factor_engine.factor_builder import FACTOR_COLUMNS, build_factor_data
from factor_processing import preprocess_factors
from universe import HistoricalUniverseProvider, UniverseConfig

logger = logging.getLogger("real_pilot")
PRICE_COLUMNS = ["date", "stock", "open", "high", "low", "close", "volume", "amount"]


def load_cached_real_price(csv_path: str | Path) -> pd.DataFrame:
    """Load cache only when its sidecar proves a non-mock source."""
    path = Path(csv_path); metadata_path = path.with_suffix(".json")
    if not path.exists() or not metadata_path.exists():
        raise FileNotFoundError(path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("is_real_data") is not True or metadata.get("source") == "mock":
        raise RuntimeError(f"Non-real cache rejected: {path}")
    data = pd.read_csv(path, dtype={"stock": str})
    missing = set(PRICE_COLUMNS) - set(data.columns)
    if missing: raise ValueError(f"Cached price data missing: {sorted(missing)}")
    return data


def fetch_real_stock_list(cache_path: Path) -> pd.DataFrame:
    """Fetch/cache the current real A-share candidate list for stable sampling."""
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype={"stock": str})
    import akshare as ak
    raw = ak.stock_info_a_code_name()
    code_col = next((c for c in raw.columns if str(c).lower() in {"code", "股票代码", "证券代码"}), raw.columns[0])
    name_col = next((c for c in raw.columns if str(c).lower() in {"name", "股票简称", "证券简称"}), raw.columns[1])
    result = raw[[code_col, name_col]].rename(columns={code_col: "stock", name_col: "stock_name"})
    result["stock"] = result["stock"].astype(str).str.extract(r"(\d{6})", expand=False)
    result = result.dropna().drop_duplicates("stock").sort_values("stock")
    cache_path.parent.mkdir(parents=True, exist_ok=True); result.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return result


def _normalize_akshare_history(raw: pd.DataFrame, code: str) -> pd.DataFrame:
    mapping = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "amount"}
    result = raw.rename(columns=mapping)
    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(result.columns):
        raise ValueError(f"AkShare history columns unsupported: {list(raw.columns)}")
    if "amount" not in result:
        result["amount"] = pd.to_numeric(result["close"], errors="coerce") * pd.to_numeric(result["volume"], errors="coerce")
        result.attrs["fallback"] = "tencent_amount_close_times_volume_proxy"
    result["stock"] = code
    for column in ["open", "high", "low", "close", "volume", "amount"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["date"] = pd.to_datetime(result["date"])
    return result[PRICE_COLUMNS].dropna(subset=["date", "close", "volume"]).sort_values("date")


def fetch_real_price(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch real adjusted prices, with a real Tencent endpoint fallback only."""
    import akshare as ak
    try:
        raw = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="qfq")
        result = _normalize_akshare_history(raw, code); result.attrs["source"] = "akshare_eastmoney"
    except Exception as primary_error:
        prefix = "sh" if code.startswith(("5", "6", "9")) else "sz"
        try:
            raw = ak.stock_zh_a_hist_tx(symbol=f"{prefix}{code}", start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="qfq", timeout=15)
            result = _normalize_akshare_history(raw, code); result.attrs["source"] = "akshare_tencent"
            result.attrs["primary_error"] = str(primary_error)
        except Exception as fallback_error:
            raise RuntimeError(f"real endpoints failed: eastmoney={primary_error}; tencent={fallback_error}") from fallback_error
    if result.empty: raise ValueError("real endpoint returned no usable rows")
    return result


def get_or_download_price(code: str, start_date: str, end_date: str, cache_dir: Path, fetcher: Callable = fetch_real_price) -> tuple[pd.DataFrame, dict]:
    """Read a provenance-validated cache or download and atomically record provenance."""
    path = cache_dir / f"{code}_{start_date}_{end_date}.csv"
    try:
        data = load_cached_real_price(path)
        metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8")); metadata["cache_hit"] = True
        return data, metadata
    except FileNotFoundError:
        pass
    data = fetcher(code, start_date, end_date)
    source = data.attrs.get("source")
    if not source or source == "mock": raise RuntimeError("Downloader did not prove a real source")
    metadata = {"stock": code, "source": source, "is_real_data": True, "cache_hit": False, "rows": len(data), "fallback": data.attrs.get("fallback"), "primary_error": data.attrs.get("primary_error")}
    cache_dir.mkdir(parents=True, exist_ok=True); data.to_csv(path, index=False, encoding="utf-8-sig")
    path.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return data, metadata


def _write_summary(path: Path, metadata: dict, ic: pd.DataFrame, quantile: pd.DataFrame) -> None:
    factor_5d = ic[ic.period == 5] if not ic.empty else ic
    monotonic = quantile[quantile.period == 5][["factor_name", "monotonic_increasing", "Q5-Q1"]] if not quantile.empty else quantile
    content = f"""# Real A-Share Pilot Research

> **Research validity status: {metadata['sample']['status']}**

- Period: {metadata['start_date']} to {metadata['end_date']}
- Requested stocks: {metadata['requested_stock_count']}
- Successful real downloads: {metadata['successful_stock_count']}
- Average daily cross-section: {metadata['average_daily_cross_section']:.1f}
- Real market data: true
- Financial factors included: false (market-based pilot only)
- Neutralization validated: false (no reliable PIT industry/market-cap exposures)
- Walk-forward real pilot: {metadata['walk_forward_real_pilot']}

## Five-day IC summary

{factor_5d.to_markdown(index=False) if not factor_5d.empty else 'No valid IC observations.'}

## IC decay (5/10/20/40 trading days)

{ic[ic.period.isin([5, 10, 20, 40])][['factor_name', 'period', 'mean_ic', 'mean_rank_ic', 'icir', 'rank_icir', 'positive_ic_ratio']].to_markdown(index=False) if not ic.empty else 'No valid decay observations.'}

## Five-day quantile monotonicity and Q5-Q1

{monotonic.to_markdown(index=False) if not monotonic.empty else 'No valid quantile observations.'}

## Limitations

- Candidate stocks come from a current real A-share list; historical delistings are unavailable, so survivorship bias remains.
- Listing date is inferred from the first downloaded observation and may predate the requested window.
- No PIT market cap or industry exposure was used; neutralization was intentionally skipped.
- Failed endpoints and all real-endpoint fallbacks are recorded in `real_pilot_data_quality.json`.
"""
    path.write_text(content, encoding="utf-8")


def run_pilot(start_date: str, end_date: str, stock_count: int = 50, seed: int = 20240911, max_workers: int = 8) -> dict:
    """Download and run the existing cross-sectional framework on a real pilot."""
    if stock_count < 30: raise ValueError("stock_count must be at least 30")
    output = PROJECT_ROOT / "reports/real_pilot"; output.mkdir(parents=True, exist_ok=True)
    cache = PROJECT_ROOT / "cache/real_pilot"; price_cache = cache / "prices"
    candidates = fetch_real_stock_list(cache / "a_share_list.csv")
    candidates = candidates[~candidates.stock_name.astype(str).str.upper().str.contains(r"\*?ST", regex=True)]
    codes = candidates.stock.tolist(); random.Random(seed).shuffle(codes)
    attempts = codes[:max(stock_count + 20, 70)]
    successes, failures, download_meta = {}, {}, []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for index, code in enumerate(attempts, 1):
            print(f"[{index}/{len(attempts)}] Downloading {code}...", flush=True)
            futures[executor.submit(get_or_download_price, code, start_date, end_date, price_cache)] = code
        for future in as_completed(futures):
            code = futures[future]
            try:
                frame, metadata = future.result()
                if len(frame) >= 161 and len(successes) < stock_count:
                    successes[code] = frame; download_meta.append(metadata)
            except Exception as exc:
                failures[code] = str(exc); logger.warning("%s failed: %s", code, exc)
    if len(successes) < 30:
        status = "INSUFFICIENT_REAL_SAMPLE"
    else:
        status = "READY"
    if not successes:
        raise RuntimeError("No real stock histories downloaded")
    prices = pd.concat(successes.values(), ignore_index=True).sort_values(["stock", "date"])
    prices.to_csv(cache / "real_price_panel.csv", index=False, encoding="utf-8-sig")
    print("Building factor panel...", flush=True)
    panel = build_factor_data(prices)
    for period in [1, 5, 10, 20, 40]: panel[f"forward_return_{period}"] = panel[f"forward_return_{period}d"]
    panel.to_csv(cache / "real_factor_panel.csv", index=False, encoding="utf-8-sig")
    universe = HistoricalUniverseProvider(prices, UniverseConfig(min_listing_days=120))
    eligible = pd.DataFrame([{"date": pd.Timestamp(date), "stock": stock} for date in pd.to_datetime(panel.date).unique() for stock in universe.get_universe(date)])
    panel["date"] = pd.to_datetime(panel.date); panel = panel.merge(eligible, on=["date", "stock"], how="inner")
    processed = apply_factor_directions(preprocess_factors(panel)); processed["directed_value"] = processed["normalized_value"]
    sample = assess_research_sample(processed)
    if len(successes) < 30: sample["status"] = "INSUFFICIENT_REAL_SAMPLE"
    print("Running IC analysis...", flush=True)
    ic = analyze_ic_decay(processed, [1, 5, 10, 20, 40])
    ic.to_csv(output / "real_pilot_ic.csv", index=False, encoding="utf-8-sig")
    plot_ic_decay(ic, output / "real_pilot_ic_decay.png")
    print("Running quantile analysis...", flush=True)
    quantile_rows = []
    for factor, group in processed.groupby("factor_name"):
        for period in [1, 5, 10, 20, 40]:
            daily = calculate_quantile_returns(group, return_col=f"forward_return_{period}d")
            means = daily.mean(); ordered = means[[f"Q{i}" for i in range(1, 6)]]
            quantile_rows.append({"factor_name": factor, "period": period, **means.to_dict(), "monotonic_increasing": bool(ordered.is_monotonic_increasing)})
            if period == 5: plot_quantile_curves(daily, factor, output / f"real_pilot_quantile_{factor}.png")
    quantile = pd.DataFrame(quantile_rows); quantile.to_csv(output / "real_pilot_quantile.csv", index=False, encoding="utf-8-sig")
    average_cs = processed.drop_duplicates(["date", "stock"]).groupby("date").stock.nunique().mean()
    metadata = {"pilot_status": status, "start_date": start_date, "end_date": end_date, "requested_stock_count": stock_count, "candidate_attempts": len(attempts), "successful_stock_count": len(successes), "average_daily_cross_section": float(average_cs), "sample": sample, "real_market_data": True, "financial_factors_included": False, "neutralization_validated": False, "walk_forward_real_pilot": "not_run_due_to_time", "factor_names": FACTOR_COLUMNS, "stock_list_source": "akshare_current_a_share_list", "survivorship_bias_status": "partially_bias_reduced_current_list", "download_metadata": download_meta, "download_failures": failures, "fallback_warnings": sorted({m.get("fallback") for m in download_meta if m.get("fallback")})}
    (output / "real_pilot_data_quality.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_summary(output / "real_pilot_summary.md", metadata, ic, quantile)
    print(f"Successful real stocks: {len(successes)}", flush=True)
    return {"metadata": metadata, "ic": ic, "quantile": quantile, "factor_panel": panel}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small real A-share research pilot")
    parser.add_argument("--start-date", default="2024-01-01"); parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--stock-count", type=int, default=50); parser.add_argument("--seed", type=int, default=20240911)
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args(); run_pilot(args.start_date, args.end_date, args.stock_count, args.seed, args.max_workers)


if __name__ == "__main__": main()
