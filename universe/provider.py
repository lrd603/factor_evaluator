"""Historical, data-derived universe provider."""

from __future__ import annotations

import pandas as pd
from data_loader.security_master import active_on

from .base import UniverseMetadata, UniverseProvider
from .filters import UniverseConfig, filter_universe


class HistoricalUniverseProvider(UniverseProvider):
    """Serve the eligible stock set from the input history at a requested date."""

    def __init__(self, history: pd.DataFrame, config: UniverseConfig | None = None) -> None:
        self.history = history.copy()
        self.config = config or UniverseConfig()
        self.metadata = UniverseMetadata("input_history", False, False, "partially_bias_reduced_universe", ("listing_date_inferred_from_first_observation",))

    def get_universe(self, date: object, universe_name: str = "ALL_A") -> list[str]:
        """Return stock codes eligible on the requested date."""
        if universe_name.upper() != "ALL_A":
            raise RuntimeError(f"historical_index_constituents_unavailable:{universe_name}")
        rows = filter_universe(self.history, date, self.config)
        return [code.zfill(6) if code.isdigit() else code for code in rows["stock"].astype(str)]

    @property
    def data_quality(self) -> dict[str, bool]:
        """Describe which requested eligibility fields are actually available."""
        columns = set(self.history.columns)
        return {
            "point_in_time_index_constituents": False,
            "st_filter_available": "is_st" in columns,
            "suspension_flag_available": "is_suspended" in columns,
            "limit_status_available": {"limit_up", "limit_down"}.issubset(columns),
            "amount_available": "amount" in columns,
        }


class PointInTimeSecurityMasterProvider(UniverseProvider):
    """Combine dated existence with price-based trading eligibility."""
    def __init__(self, master, history, config=None):
        self.master=master.copy(); self.history=history.copy(); self.config=config or UniverseConfig()
        self.metadata=UniverseMetadata("exchange_security_master",True,True,"survivorship_aware_structure",())
    def get_universe(self,date,universe_name="ALL_A"):
        if universe_name.upper()!="ALL_A":raise RuntimeError(f"historical_index_constituents_unavailable:{universe_name}")
        t=pd.Timestamp(date); existing=set(self.master.loc[active_on(self.master,t),"stock_code"].astype(str))
        eligible=filter_universe(self.history[self.history.stock.astype(str).isin(existing)],t,self.config)
        return sorted(eligible.stock.astype(str).str.zfill(6).tolist())
