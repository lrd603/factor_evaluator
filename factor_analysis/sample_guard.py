"""Research validity classification based on daily cross-section breadth."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SampleGuardConfig:
    min_cross_section_size: int = 30
    recommended_cross_section_size: int = 100


def assess_research_sample(data: pd.DataFrame, config: SampleGuardConfig | None = None) -> dict:
    """Classify research validity without presenting tiny panels as investment evidence."""
    settings = config or SampleGuardConfig()
    sizes = data.drop_duplicates(["date", "stock"]).groupby("date")["stock"].nunique()
    median = float(sizes.median()) if len(sizes) else 0.0
    minimum = int(sizes.min()) if len(sizes) else 0
    if median < settings.min_cross_section_size:
        status = "ENGINEERING_SMOKE_TEST"
    elif median < settings.recommended_cross_section_size:
        status = "SMALL_SAMPLE_RESEARCH"
    else:
        status = "VALID_CROSS_SECTIONAL_RESEARCH"
    return {"status": status, "median_cross_section_size": median, "minimum_cross_section_size": minimum, "quintile_available": minimum >= 5, "ic_sample_sufficient": median >= settings.min_cross_section_size}


def assess_formal_research(data: pd.DataFrame, stock_count: int | None = None) -> dict:
    """Add an explicit time-span guard to the existing breadth assessment."""
    breadth = assess_research_sample(data)
    dates = pd.to_datetime(data["date"], errors="coerce").dropna()
    years = float((dates.max() - dates.min()).days / 365.2425) if len(dates) else 0.0
    count = int(stock_count if stock_count is not None else data["stock"].nunique())
    time_status = "VALID_TIME_SPAN" if years >= 5 else "LIMITED_TIME_SAMPLE"
    breadth["time_span_years"] = years
    breadth["time_span_status"] = time_status
    breadth["formal_status"] = (
        "FORMAL_EMPIRICAL_RESEARCH"
        if count >= 100 and years >= 5
        else "NOT_FORMAL_EMPIRICAL_RESEARCH"
    )
    return breadth
