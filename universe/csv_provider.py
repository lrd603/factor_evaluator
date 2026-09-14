"""Point-in-time universe provider backed by local CSV/data frames."""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from .base import SUPPORTED_UNIVERSES, UniverseMetadata, UniverseProvider
from .filters import UniverseConfig, filter_universe


class CSVUniverseProvider(UniverseProvider):
    """Build ALL_A from listing intervals or index universes from dated membership."""

    def __init__(self, history: pd.DataFrame | str | Path, config: UniverseConfig | None = None) -> None:
        self.history = pd.read_csv(history, dtype={"stock": str}) if isinstance(history, (str, Path)) else history.copy()
        self.config = config or UniverseConfig()
        has_intervals = "listing_date" in self.history
        self.metadata = UniverseMetadata(
            universe_source="local_csv",
            point_in_time_universe=has_intervals,
            historical_constituents_available=has_intervals,
            survivorship_bias_status="fully_point_in_time_universe" if has_intervals else "partially_bias_reduced_universe",
            warnings=() if has_intervals else ("listing_date_inferred_from_first_observation",),
        )

    def get_universe(self, date: object, universe_name: str = "ALL_A") -> list[str]:
        """Resolve membership without using observations after the requested date."""
        name = universe_name.upper()
        if name not in SUPPORTED_UNIVERSES:
            raise ValueError(f"Unsupported universe: {universe_name}")
        cutoff = pd.Timestamp(date)
        data = self.history.copy()
        if name != "ALL_A":
            if "universe_name" not in data or "effective_date" not in data:
                raise RuntimeError(f"historical_index_constituents_unavailable:{name}")
            effective = pd.to_datetime(data["effective_date"])
            end = pd.to_datetime(data.get("end_date", pd.Series(pd.NaT, index=data.index)))
            selected = data[(data["universe_name"].str.upper() == name) & (effective <= cutoff) & (end.isna() | (end >= cutoff))]
            return sorted(selected["stock"].astype(str).str.zfill(6).unique())
        if "listing_date" in data:
            listing = pd.to_datetime(data["listing_date"], errors="coerce")
            delisting = pd.to_datetime(data.get("delisting_date", pd.Series(pd.NaT, index=data.index)), errors="coerce")
            intervals = data[(listing <= cutoff) & (delisting.isna() | (delisting >= cutoff))]
            if {"date", "close", "volume"}.issubset(intervals.columns):
                intervals = filter_universe(intervals, cutoff, self.config)
            return sorted(intervals["stock"].astype(str).str.zfill(6).unique())
        warnings.warn("listing_date unavailable; first observation is only a partial bias reduction", RuntimeWarning)
        return sorted(filter_universe(data, cutoff, self.config)["stock"].astype(str).str.zfill(6).unique())
