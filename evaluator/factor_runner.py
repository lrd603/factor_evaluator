import pandas as pd

from evaluator.group_analysis import calculate_group_return
from evaluator.metrics import (
    calculate_daily_ic,
    calculate_daily_rank_ic,
    calculate_icir,
)
from evaluator.performance import (
    calculate_max_drawdown,
    calculate_sharpe,
    calculate_win_rate,
)


def run_factor_evaluation(data):
    """
    对 DataFrame 中的每个因子分别计算核心评价指标，并返回汇总 DataFrame。

    兼容数据格式：
    - 旧格式：date, stock, factor, return
    - 新格式：date, stock, factor_value, factor_name, return
    """
    if data is None or data.empty:
        return pd.DataFrame()

    if "factor_name" in data.columns:
        factor_name_col = "factor_name"
        factor_value_col = "factor_value" if "factor_value" in data.columns else "factor"
    elif "factor" in data.columns:
        data = data.copy()
        data["factor_name"] = "factor"
        factor_name_col = "factor_name"
        factor_value_col = "factor"
    elif "factor_value" in data.columns:
        data = data.copy()
        data["factor_name"] = "factor_value"
        factor_name_col = "factor_name"
        factor_value_col = "factor_value"
    else:
        raise ValueError(
            "DataFrame must include either 'factor' or 'factor_value', and optional 'factor_name'."
        )

    results = []

    for factor_name, group in data.groupby(factor_name_col, sort=True):
        group = group.copy()
        group["factor"] = group[factor_value_col]

        daily_ic = group.groupby("date").apply(calculate_daily_ic)
        daily_rank_ic = group.groupby("date").apply(calculate_daily_rank_ic)
        icir = calculate_icir(daily_ic)

        _, _, long_short_return = calculate_group_return(group)
        sharpe_ratio = calculate_sharpe(long_short_return)
        max_drawdown = calculate_max_drawdown(long_short_return)
        win_rate = calculate_win_rate(long_short_return)

        results.append(
            {
                "factor_name": str(factor_name),
                "IC Mean": float(daily_ic.mean()),
                "ICIR": float(icir),
                "Rank IC Mean": float(daily_rank_ic.mean()),
                "Long Short Return": float(long_short_return.mean()),
                "Sharpe Ratio": float(sharpe_ratio),
                "Max Drawdown": float(max_drawdown),
                "Win Rate": float(win_rate),
            }
        )

    summary = pd.DataFrame(results)
    if summary.empty:
        return summary

    summary = summary.set_index("factor_name")
    return summary
