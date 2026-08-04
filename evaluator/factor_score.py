import math


def _safe_float(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _clip(value, lower=0.0, upper=1.0):
    return max(lower, min(upper, value))


def rating_from_score(score):
    score = _safe_float(score, 0.0)
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Average"
    return "Weak"


def calculate_factor_score(metric_dict):
    """
    基于 ICIR、Long-Short Return、Sharpe Ratio、Win Rate 和 Max Drawdown
    生成 0-100 分的综合因子评分。
    """
    data = metric_dict or {}

    icir = _safe_float(data.get("ICIR", data.get("IC Mean", 0.0)), 0.0)
    long_short_return = _safe_float(
        data.get("Long Short Return", data.get("Long_Short_Return_Mean", 0.0)),
        0.0,
    )
    sharpe_ratio = _safe_float(
        data.get("Sharpe Ratio", data.get("Sharpe_Ratio", 0.0)),
        0.0,
    )
    win_rate = _safe_float(data.get("Win Rate", data.get("Win_Rate", 0.0)), 0.0)
    max_drawdown = _safe_float(
        data.get("Max Drawdown", data.get("Max_Drawdown", 0.0)),
        0.0,
    )

    # The evaluator supplies mean daily long-short return. Factor direction is
    # reversible, so predictive strength is scored by magnitude; drawdown is
    # always interpreted as a loss regardless of its sign convention.
    annualized_long_short = abs(long_short_return) * 252
    icir_score = _clip(abs(icir) / 0.5, 0.0, 1.0)
    long_short_score = _clip(annualized_long_short / 0.20, 0.0, 1.0)
    sharpe_score = _clip(abs(sharpe_ratio) / 2.0, 0.0, 1.0)
    win_rate_score = _clip(abs(win_rate - 0.5) / 0.15, 0.0, 1.0)
    drawdown_score = _clip(1.0 - (abs(max_drawdown) / 0.3), 0.0, 1.0)

    total_score = (
        icir_score * 30
        + long_short_score * 30
        + sharpe_score * 20
        + win_rate_score * 10
        + drawdown_score * 10
    )

    return round(float(total_score), 2)


def evaluate_factor_scores(summary_dict):
    """
    为每个因子计算综合评分，并返回包含 factor_score 和 rating 的字典。
    """
    score_summary = {}
    for factor_name, metrics in (summary_dict or {}).items():
        score = calculate_factor_score(metrics)
        score_summary[str(factor_name)] = {
            "factor_score": score,
            "rating": rating_from_score(score),
        }
    return score_summary
