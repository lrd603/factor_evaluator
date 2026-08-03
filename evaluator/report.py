import json
import os


def generate_report(
    daily_ic,
    daily_rank_ic,
    icir,
    top_return=None,
    bottom_return=None,
    long_short_return=None
):

    ic_mean = daily_ic.mean()
    ic_std = daily_ic.std()
    rank_ic_mean = daily_rank_ic.mean()
    top_return_mean = top_return.mean() if top_return is not None else 0.0
    bottom_return_mean = bottom_return.mean() if bottom_return is not None else 0.0
    long_short_return_mean = long_short_return.mean() if long_short_return is not None else 0.0

    if icir > 1:
        quality = "Strong"
    elif icir > 0.5:
        quality = "Medium"
    else:
        quality = "Weak"

    report = {
        "IC_mean": round(float(ic_mean), 4),
        "IC_std": round(float(ic_std), 4),
        "ICIR": round(float(icir), 4),
        "Rank_IC_mean": round(float(rank_ic_mean), 4),
        "Top_Return_Mean": round(float(top_return_mean), 4),
        "Bottom_Return_Mean": round(float(bottom_return_mean), 4),
        "Long_Short_Return_Mean": round(float(long_short_return_mean), 4),
        "quality": quality
    }

    os.makedirs(
        "reports",
        exist_ok=True
    )

    with open(
        "reports/factor_report.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("========================")
    print("Factor Evaluation Report")
    print("========================")

    for key, value in report.items():
        print(f"{key}: {value}")

    print("========================")
    print("Report saved:")
    print("reports/factor_report.json")