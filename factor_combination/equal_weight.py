"""Equal-weight factor combination."""

import pandas as pd


def combine_equal_weight(values: pd.DataFrame) -> pd.Series:
    """Average available normalized factor columns for every observation."""
    return values.apply(pd.to_numeric, errors="coerce").mean(axis=1)
