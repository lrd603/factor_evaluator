import json
import os

from evaluator.factor_score import rating_from_score


def _quality_text(report_data):
    icir = float(report_data.get("ICIR", report_data.get("ICIR", 0.0)))
    sharpe = float(report_data.get("Sharpe_Ratio", report_data.get("Sharpe Ratio", 0.0)))
    rank_ic = float(report_data.get("Rank_IC_mean", report_data.get("Rank IC Mean", 0.0)))

    if icir > 1 and sharpe > 1:
        return "Strong factor with positive predictive ability."
    if icir > 0.5 and rank_ic > 0.3:
        return "Moderate factor with reasonable stability."
    if icir > 0:
        return "Weak factor with limited predictive ability."
    return "Poor stability and weak predictive ability."


def generate_markdown_report(report_data=None, summary_data=None, output_path="reports/factor_research_report.md"):
    """
    生成 Markdown 因子研究报告。
    支持单因子 report_data 或多因子 summary_data。
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if summary_data is None:
        summary_path = os.path.join(os.path.dirname(output_path), "factor_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)

    if report_data is None and summary_data is None:
        json_path = os.path.join(os.path.dirname(output_path), "factor_report.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)

    if summary_data is not None:
        ranked_factors = sorted(
            summary_data.items(),
            key=lambda item: float(item[1].get("factor_score", 0.0)),
            reverse=True,
        )
        summary_rows = []
        for factor_name, values in summary_data.items():
            summary_rows.append(
                f"| {factor_name} | {values.get('IC Mean', 0.0)} | {values.get('ICIR', 0.0)} | {values.get('Rank IC Mean', 0.0)} | {values.get('Long Short Return', 0.0)} | {values.get('Sharpe Ratio', 0.0)} | {values.get('Max Drawdown', 0.0)} | {values.get('Win Rate', 0.0)} |"
            )

        quality_items = []
        for factor_name, values in summary_data.items():
            factor_quality = _quality_text(values)
            quality_items.append(f"- {factor_name}: {factor_quality}")

        ranking_lines = []
        for idx, (factor_name, values) in enumerate(ranked_factors, start=1):
            score = values.get("factor_score", 0.0)
            ranking_lines.append(f"{idx}. {factor_name} Score {score}")

        top_factor_name, top_values = ranked_factors[0] if ranked_factors else (None, {})
        top_score = top_values.get("factor_score", 0.0)
        top_rating = top_values.get("rating", rating_from_score(top_score))

        lines = [
            "# Factor Research Report",
            "",
            "## 1. Performance Summary",
            "",
            "| Factor | IC Mean | ICIR | Rank IC Mean | Long Short Return | Sharpe Ratio | Max Drawdown | Win Rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            *summary_rows,
            "",
            "## 2. Return Analysis",
            "",
            "The summary table above includes each factor's long-short return behavior and return quality metrics.",
            "",
            "## 3. Factor Quality",
            "",
            *quality_items,
            "",
            "## Factor Score",
            "",
            f"Final Score: {top_score}",
            f"Rating: {top_rating}",
            "",
            "Score based on:",
            "- ICIR",
            "- Long Short Return",
            "- Sharpe Ratio",
            "- Win Rate",
            "- Drawdown",
            "",
            "Factor Ranking:",
            *ranking_lines,
            "",
            "## 4. Visualization",
            "",
            "![IC Curve](ic_curve.png)",
            "",
            "![Long Short Curve](long_short_curve.png)",
            "",
        ]
    elif report_data is not None:
        metrics = {
            "IC Mean": report_data.get("IC_mean", report_data.get("IC Mean", 0.0)),
            "Rank IC Mean": report_data.get("Rank_IC_mean", report_data.get("Rank IC Mean", 0.0)),
            "ICIR": report_data.get("ICIR", 0.0),
            "Sharpe Ratio": report_data.get("Sharpe_Ratio", report_data.get("Sharpe Ratio", 0.0)),
            "Max Drawdown": report_data.get("Max_Drawdown", report_data.get("Max Drawdown", 0.0)),
            "Win Rate": report_data.get("Win_Rate", report_data.get("Win Rate", 0.0)),
            "Top Group Return": report_data.get("Top_Return_Mean", report_data.get("Top Group Return", 0.0)),
            "Bottom Group Return": report_data.get("Bottom_Return_Mean", report_data.get("Bottom Group Return", 0.0)),
            "Long Short Return": report_data.get("Long_Short_Return_Mean", report_data.get("Long Short Return", 0.0)),
        }
        score = report_data.get("factor_score", report_data.get("Factor Score", 0.0))
        rating = report_data.get("rating", rating_from_score(score))
        quality_text = _quality_text(report_data)
        lines = [
            "# Factor Research Report",
            "",
            "## 1. Performance Summary",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| IC Mean | {metrics['IC Mean']} |",
            f"| Rank IC Mean | {metrics['Rank IC Mean']} |",
            f"| ICIR | {metrics['ICIR']} |",
            f"| Sharpe Ratio | {metrics['Sharpe Ratio']} |",
            f"| Max Drawdown | {metrics['Max Drawdown']} |",
            f"| Win Rate | {metrics['Win Rate']} |",
            "",
            "## 2. Return Analysis",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Top Group Return | {metrics['Top Group Return']} |",
            f"| Bottom Group Return | {metrics['Bottom Group Return']} |",
            f"| Long Short Return | {metrics['Long Short Return']} |",
            "",
            "## 3. Factor Quality",
            "",
            quality_text,
            "",
            "## Factor Score",
            "",
            f"Final Score: {score}",
            f"Rating: {rating}",
            "",
            "Score based on:",
            "- ICIR",
            "- Long Short Return",
            "- Sharpe Ratio",
            "- Win Rate",
            "- Drawdown",
            "",
            "## 4. Visualization",
            "",
            "![IC Curve](ic_curve.png)",
            "",
            "![Long Short Curve](long_short_curve.png)",
            "",
        ]
    else:
        lines = [
            "# Factor Research Report",
            "",
            "No factor data available.",
        ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("========================")
    print("Markdown research report saved:")
    print(output_path)

    return output_path


def generate_report(
    daily_ic,
    daily_rank_ic,
    icir,
    top_return=None,
    bottom_return=None,
    long_short_return=None,
    sharpe_ratio=None,
    max_drawdown=None,
    win_rate=None
):

    ic_mean = daily_ic.mean()
    ic_std = daily_ic.std()
    rank_ic_mean = daily_rank_ic.mean()
    top_return_mean = top_return.mean() if top_return is not None else 0.0
    bottom_return_mean = bottom_return.mean() if bottom_return is not None else 0.0
    long_short_return_mean = long_short_return.mean() if long_short_return is not None else 0.0
    sharpe_ratio = float(sharpe_ratio) if sharpe_ratio is not None else 0.0
    max_drawdown = float(max_drawdown) if max_drawdown is not None else 0.0
    win_rate = float(win_rate) if win_rate is not None else 0.0

    if icir > 1:
        quality = "Strong"
    elif icir > 0.5:
        quality = "Medium"
    else:
        quality = "Weak"

    from evaluator.factor_score import calculate_factor_score

    factor_score = calculate_factor_score({
        "ICIR": float(icir),
        "Long Short Return": float(long_short_return_mean),
        "Sharpe Ratio": float(sharpe_ratio),
        "Win Rate": float(win_rate),
        "Max Drawdown": float(max_drawdown),
    })

    report = {
        "IC_mean": round(float(ic_mean), 4),
        "IC_std": round(float(ic_std), 4),
        "ICIR": round(float(icir), 4),
        "Rank_IC_mean": round(float(rank_ic_mean), 4),
        "Top_Return_Mean": round(float(top_return_mean), 4),
        "Bottom_Return_Mean": round(float(bottom_return_mean), 4),
        "Long_Short_Return_Mean": round(float(long_short_return_mean), 4),
        "Sharpe_Ratio": round(float(sharpe_ratio), 4),
        "Max_Drawdown": round(float(max_drawdown), 4),
        "Win_Rate": round(float(win_rate), 4),
        "factor_score": round(float(factor_score), 2),
        "rating": rating_from_score(factor_score),
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

    generate_markdown_report(report_data=report)

    print("========================")
    print("Factor Evaluation Report")
    print("========================")

    for key, value in report.items():
        print(f"{key}: {value}")

    print("========================")
    print("Report saved:")
    print("reports/factor_report.json")