"""AkShare universe adapter that refuses unsafe historical backfills."""

from __future__ import annotations

import pandas as pd

from .base import UniverseMetadata, UniverseProvider


class AkShareUniverseProvider(UniverseProvider):
    """Expose current constituents only and explicitly reject historical queries."""

    def __init__(self) -> None:
        self.metadata = UniverseMetadata(
            universe_source="akshare_current_constituents",
            point_in_time_universe=False,
            historical_constituents_available=False,
            survivorship_bias_status="current_constituent_fallback",
            warnings=("historical_index_constituents_unavailable",),
        )

    def get_universe(self, date: object, universe_name: str = "ALL_A") -> list[str]:
        """Reject historical dates because AkShare current membership is not PIT history."""
        if pd.Timestamp(date).normalize() != pd.Timestamp.today().normalize():
            raise RuntimeError("historical_index_constituents_unavailable")
        raise RuntimeError("current constituent fetch requires explicit real-data runner")
