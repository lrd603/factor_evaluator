import math

import pandas as pd


def calculate_group_return(data, quantile=0.3):
    """
    按日期对因子排序，分组计算Top/Bottom组合每日平均收益。

    参数:
        data: DataFrame，包含 date、stock、factor、return
        quantile: Top/Bottom 分组比例，默认为 0.3

    返回:
        top_return: 各交易日 Top 组平均收益序列
        bottom_return: 各交易日 Bottom 组平均收益序列
        long_short_return: 各交易日 Top - Bottom 收益序列
    """
    if not 0 < quantile < 1:
        raise ValueError("quantile must be between 0 and 1.")

    required_columns = {"date", "stock", "factor", "return"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        raise ValueError(
            f"DataFrame missing required columns: {sorted(missing_columns)}"
        )

    def _daily_group_stats(group):
        group = group.sort_values("factor", ascending=False).reset_index(drop=True)
        top_n = max(1, int(math.ceil(len(group) * quantile)))
        bottom_n = max(1, int(math.ceil(len(group) * quantile)))

        top_group = group.head(top_n)
        bottom_group = group.tail(bottom_n).sort_values(
            "factor",
            ascending=True
        ).reset_index(drop=True)

        top_mean_return = top_group["return"].mean()
        bottom_mean_return = bottom_group["return"].mean()

        return pd.Series(
            {
                "top_return": top_mean_return,
                "bottom_return": bottom_mean_return,
            }
        )

    daily_stats = data.groupby("date", sort=True).apply(_daily_group_stats)

    top_return = daily_stats["top_return"]
    bottom_return = daily_stats["bottom_return"]
    long_short_return = top_return - bottom_return

    return top_return, bottom_return, long_short_return
