import os

import matplotlib.pyplot as plt
import pandas as pd


def _ensure_reports_dir():
    os.makedirs("reports", exist_ok=True)


def plot_ic_curve(daily_ic):
    """
    绘制 IC 随日期变化曲线，并保存到 reports/ic_curve.png
    """
    if daily_ic is None:
        raise ValueError("daily_ic cannot be None.")

    daily_ic = pd.Series(daily_ic)
    _ensure_reports_dir()

    plt.figure(figsize=(10, 6))
    plt.plot(
        daily_ic.index,
        daily_ic.values,
        marker="o",
        color="tab:blue",
        linewidth=2
    )
    plt.axhline(0, color="gray", linestyle="--", linewidth=1)
    plt.title("IC Curve")
    plt.xlabel("Date")
    plt.ylabel("IC")
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_path = os.path.join("reports", "ic_curve.png")
    plt.savefig(output_path, dpi=200)
    plt.close()

    print("IC curve saved:")
    print(output_path)

    return output_path


def plot_long_short_curve(long_short_returns):
    """
    根据每日 Long-Short 收益计算累计收益曲线，并保存到 reports/long_short_curve.png
    """
    if long_short_returns is None:
        raise ValueError("long_short_returns cannot be None.")

    long_short_returns = pd.Series(long_short_returns)
    cumulative_returns = (1 + long_short_returns).cumprod() - 1
    _ensure_reports_dir()

    plt.figure(figsize=(10, 6))
    plt.plot(
        cumulative_returns.index,
        cumulative_returns.values,
        marker="o",
        color="tab:orange",
        linewidth=2
    )
    plt.axhline(0, color="gray", linestyle="--", linewidth=1)
    plt.title("Long-Short Cumulative Return Curve")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.xticks(rotation=45)
    plt.tight_layout()

    output_path = os.path.join("reports", "long_short_curve.png")
    plt.savefig(output_path, dpi=200)
    plt.close()

    print("Long-Short curve saved:")
    print(output_path)

    return output_path
