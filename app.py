"""Streamlit presentation layer for the factor_evaluator platform."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Callable

import pandas as pd

from stock_evaluator import evaluate_stock

try:
    import streamlit as st
except ImportError:  # Pure helper functions remain testable before UI dependencies are installed.
    st = None


REPORTS_DIR = Path("reports")
STOCK_REPORT_PATH = REPORTS_DIR / "stock_report.md"
BACKTEST_REPORT_PATH = REPORTS_DIR / "backtest_report.md"
FACTOR_IC_REPORT_PATH = REPORTS_DIR / "factor_ic_report.md"


def validate_stock_code(stock_code: str) -> str:
    """Validate and normalize a six-digit A-share stock code."""
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("股票代码必须是6位数字，例如 600519")
    return code


def run_stock_analysis(
    stock_code: str,
    evaluator: Callable[[str], dict] = evaluate_stock,
) -> dict:
    """Run the existing stock evaluator through a UI-friendly function."""
    return evaluator(validate_stock_code(stock_code))


def load_markdown_report(path: str | Path) -> str:
    """Read an existing Markdown report, returning an empty string if absent."""
    report_path = Path(path)
    return report_path.read_text(encoding="utf-8") if report_path.exists() else ""


def parse_backtest_metrics(report: str) -> dict[str, float]:
    """Extract the dashboard metrics from the generated backtest report."""
    labels = {
        "Annual Return": "annual_return",
        "Sharpe Ratio": "sharpe_ratio",
        "Max Drawdown": "max_drawdown",
        "Alpha": "alpha",
    }
    metrics: dict[str, float] = {}
    for label, key in labels.items():
        match = re.search(rf"{re.escape(label)}:\s*([-+]?\d+(?:\.\d+)?)\s*(%)?", report)
        if match:
            value = float(match.group(1))
            metrics[key] = value / 100 if match.group(2) else value
    return metrics


def load_backtest_curves(
    returns_path: str | Path = REPORTS_DIR / "backtest_returns.csv",
) -> pd.DataFrame:
    """Build equity and drawdown curves if persisted backtest returns exist."""
    path = Path(returns_path)
    if not path.exists():
        return pd.DataFrame()
    data = pd.read_csv(path)
    if not {"date", "portfolio_return"}.issubset(data.columns):
        return pd.DataFrame()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["portfolio_return"] = pd.to_numeric(data["portfolio_return"], errors="raise")
    data = data.sort_values("date").set_index("date")
    data["equity"] = (1 + data["portfolio_return"]).cumprod()
    data["drawdown"] = data["equity"] / data["equity"].cummax() - 1
    return data


def _source_label(value: str) -> str:
    return "AkShare" if str(value).lower() == "akshare" else "Mock"


def _render_score_section(scores: dict) -> None:
    st.subheader("股票评分")
    columns = st.columns(4)
    columns[0].metric("Technical Score", f"{scores['technical_score']:.2f}")
    columns[1].metric("Value Score", f"{scores['value_score']:.2f}")
    columns[2].metric("Quality Score", f"{scores['quality_score']:.2f}")
    columns[3].metric("Final Score", f"{scores['final_score']:.2f}")
    score_table = pd.DataFrame(
        {
            "Dimension": ["Technical", "Value", "Quality", "Final"],
            "Score": [
                scores["technical_score"],
                scores["value_score"],
                scores["quality_score"],
                scores["final_score"],
            ],
        }
    )
    st.dataframe(score_table, hide_index=True, use_container_width=True)


def _render_data_sources(scores: dict) -> None:
    st.subheader("数据来源")
    market_column, financial_column = st.columns(2)
    market_column.info(f"Market Data Source: {_source_label(scores['data_source'])}")
    financial_column.info(
        f"Financial Data Source: {_source_label(scores['financial_data_source'])}"
    )


def _render_backtest_section() -> None:
    st.subheader("历史回测")
    report = load_markdown_report(BACKTEST_REPORT_PATH)
    metrics = parse_backtest_metrics(report)
    if metrics:
        columns = st.columns(4)
        columns[0].metric("Annual Return", f"{metrics.get('annual_return', 0):.2%}")
        columns[1].metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.4f}")
        columns[2].metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2%}")
        columns[3].metric("Alpha", f"{metrics.get('alpha', 0):.2%}")
    else:
        st.info("尚未找到可读取的回测指标，请先生成 reports/backtest_report.md。")

    curves = load_backtest_curves()
    if not curves.empty:
        st.markdown("#### 收益曲线")
        st.line_chart(curves[["equity"]])
        st.markdown("#### 回撤曲线")
        st.line_chart(curves[["drawdown"]])
    else:
        equity_image = REPORTS_DIR / "backtest_equity_curve.png"
        drawdown_image = REPORTS_DIR / "backtest_drawdown.png"
        if equity_image.exists():
            st.image(str(equity_image), caption="收益曲线", use_container_width=True)
        if drawdown_image.exists():
            st.image(str(drawdown_image), caption="回撤曲线", use_container_width=True)
        if not equity_image.exists() and not drawdown_image.exists():
            st.caption("当前没有已保存的回测收益或回撤曲线。")


def _render_reports() -> None:
    st.subheader("研究报告")
    reports = {
        "股票评分报告": STOCK_REPORT_PATH,
        "回测报告": BACKTEST_REPORT_PATH,
        "因子 IC 报告": FACTOR_IC_REPORT_PATH,
    }
    tabs = st.tabs(list(reports))
    for tab, (title, path) in zip(tabs, reports.items()):
        with tab:
            content = load_markdown_report(path)
            if content:
                st.markdown(content)
            else:
                st.info(f"尚未生成{title}。")


def main() -> None:
    """Render the Streamlit dashboard."""
    if st is None:
        raise RuntimeError("Streamlit is not installed. Run: pip install -r requirements.txt")
    st.set_page_config(
        page_title="Factor Evaluator",
        page_icon="📈",
        layout="wide",
    )
    st.title("Automated Quantitative Stock Scoring Platform")
    st.caption("A股多因子评分、因子研究与历史回测")

    st.subheader("股票分析")
    stock_code = st.text_input("股票代码", value="600519", max_chars=6)
    if st.button("分析", type="primary", use_container_width=False):
        try:
            with st.spinner("正在获取行情和财务数据并计算多因子评分..."):
                st.session_state["stock_scores"] = run_stock_analysis(stock_code)
            st.success(f"股票 {stock_code} 分析完成")
        except Exception as exc:
            st.error(f"分析失败：{exc}")

    scores = st.session_state.get("stock_scores")
    if scores:
        _render_score_section(scores)
        _render_data_sources(scores)

    st.divider()
    _render_backtest_section()
    st.divider()
    _render_reports()


if __name__ == "__main__":
    main()
