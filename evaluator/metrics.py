import pandas as pd


def calculate_ic(factor_values, future_returns):
    factor = pd.Series(factor_values)
    returns = pd.Series(future_returns)

    ic = factor.corr(returns)

    return ic