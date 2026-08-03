import math

import pandas as pd


def calculate_sharpe(returns):
    """
    计算年化 Sharpe Ratio。
    输入每日收益序列，年化系数使用 sqrt(252)。
    """
    returns = pd.Series(returns, dtype=float)
    if returns.empty:
        return 0.0

    daily_return_mean = returns.mean()
    daily_return_std = returns.std(ddof=1)

    if daily_return_std == 0:
        return 0.0

    sharpe = (daily_return_mean / daily_return_std) * math.sqrt(252)
    return float(sharpe)


def calculate_max_drawdown(returns):
    """
    计算累积收益曲线的最大回撤。
    """
    returns = pd.Series(returns, dtype=float)
    if returns.empty:
        return 0.0

    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


def calculate_win_rate(returns):
    """
    计算正收益比例。
    """
    returns = pd.Series(returns, dtype=float)
    if returns.empty:
        return 0.0

    win_rate = (returns > 0).mean()
    return float(win_rate)
