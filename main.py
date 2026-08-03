import json
import os

import pandas as pd

from evaluator.factor_runner import run_factor_evaluation
from evaluator.factor_score import evaluate_factor_scores
from evaluator.metrics import (
    calculate_daily_ic,
    calculate_daily_rank_ic,
    calculate_icir,
)
from evaluator.group_analysis import calculate_group_return
from evaluator.performance import (
    calculate_max_drawdown,
    calculate_sharpe,
    calculate_win_rate,
)
from evaluator.report import generate_markdown_report, generate_report
from evaluator.visualization import plot_ic_curve, plot_long_short_curve


# 优先读取多因子测试数据；若不存在则回退到原始单因子数据
multi_factor_path = "data/factor_data_multi.csv"
base_data_path = "data/factor_data.csv"
data_path = multi_factor_path if os.path.exists(multi_factor_path) else base_data_path

data = pd.read_csv(data_path)


print("读取的数据:")
print(data)


# 新增：如果存在 factor_name / factor_value，自动评估所有因子的汇总
if "factor_name" in data.columns or "factor_value" in data.columns:
    factor_summary = run_factor_evaluation(data)

    if not factor_summary.empty:
        summary_dict = {}
        for factor_name, row in factor_summary.iterrows():
            summary_dict[str(factor_name)] = {
                "IC Mean": round(float(row["IC Mean"]), 4),
                "ICIR": round(float(row["ICIR"]), 4),
                "Rank IC Mean": round(float(row["Rank IC Mean"]), 4),
                "Long Short Return": round(float(row["Long Short Return"]), 4),
                "Sharpe Ratio": round(float(row["Sharpe Ratio"]), 4),
                "Max Drawdown": round(float(row["Max Drawdown"]), 4),
                "Win Rate": round(float(row["Win Rate"]), 4),
            }

        score_summary = evaluate_factor_scores(summary_dict)
        for factor_name, score_info in score_summary.items():
            summary_dict[str(factor_name)]["factor_score"] = round(float(score_info["factor_score"]), 2)
            summary_dict[str(factor_name)]["rating"] = score_info["rating"]

        ranking = sorted(
            score_summary.items(),
            key=lambda item: item[1]["factor_score"],
            reverse=True,
        )

        print("\nFactor Ranking:")
        for idx, (factor_name, info) in enumerate(ranking, start=1):
            print(f"{idx}. {factor_name} Score {info['factor_score']:.1f}")

        os.makedirs("reports", exist_ok=True)
        with open("reports/factor_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=4, ensure_ascii=False)

        print("\nFactor Summary:")
        print(factor_summary)

        print("\nSaved factor summary to reports/factor_summary.json")
        generate_markdown_report(summary_data=summary_dict)


# 保留原有单因子流程：当数据中不存在 factor_name 时，按旧逻辑运行
if "factor_name" not in data.columns and "factor_value" not in data.columns:
    # 计算每日IC
    daily_ic = data.groupby("date").apply(
        calculate_daily_ic
    )

    # 计算每日Rank IC
    daily_rank_ic = data.groupby("date").apply(
        calculate_daily_rank_ic
    )

    print("\nDaily IC:")
    print(daily_ic)

    print("\nDaily Rank IC:")
    print(daily_rank_ic)

    # 计算ICIR
    icir = calculate_icir(daily_ic)

    print("\nICIR:")
    print(icir)

    # 分组收益分析
    print("\nCalculating group return analysis...")
    top_return, bottom_return, long_short_return = calculate_group_return(data)

    print("\nTop Group Return:")
    print(top_return)

    print("\nBottom Group Return:")
    print(bottom_return)

    print("\nLong Short Return:")
    print(long_short_return)

    # 计算因子收益表现指标
    sharpe_ratio = calculate_sharpe(long_short_return)
    max_drawdown = calculate_max_drawdown(long_short_return)
    win_rate = calculate_win_rate(long_short_return)

    print("\nSharpe Ratio:")
    print(sharpe_ratio)

    print("\nMax Drawdown:")
    print(max_drawdown)

    print("\nWin Rate:")
    print(win_rate)

    # 生成评价报告
    generate_report(
        daily_ic,
        daily_rank_ic,
        icir,
        top_return,
        bottom_return,
        long_short_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
    )

    # 生成可视化图表
    plot_ic_curve(daily_ic)
    plot_long_short_curve(long_short_return)
