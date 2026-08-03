# Factor Evaluator

## 项目介绍

这是一个自动化量化因子评价与研究报告生成工具，用于快速分析因子的预测能力和收益表现。

该项目支持单因子分析和多因子批量评价，并可自动输出 JSON 报告、Markdown 研究报告以及可视化图表，便于进行因子研究和结果汇总。

## 已实现功能

- IC Analysis
- Rank IC Analysis
- ICIR Calculation
- Group Return Analysis
- Long-Short Portfolio Analysis
- Sharpe Ratio
- Maximum Drawdown
- Win Rate
- Multi Factor Batch Evaluation
- Automatic JSON Report
- Automatic Markdown Research Report
- Visualization

## 项目结构

```text
factor_evaluator
├── data
│   ├── factor_data.csv
│   └── factor_data_multi.csv
├── evaluator
│   ├── factor_runner.py
│   ├── group_analysis.py
│   ├── metrics.py
│   ├── performance.py
│   ├── report.py
│   └── visualization.py
├── reports
│   ├── factor_report.json
│   ├── factor_summary.json
│   ├── factor_research_report.md
│   ├── ic_curve.png
│   └── long_short_curve.png
├── main.py
├── README.md
├── requirements.txt
└── .gitignore
```

## 使用方法

安装依赖：

```bash
pip install -r requirements.txt
```

运行项目：

```bash
python main.py
```

## 输出结果

项目运行后会在 `reports/` 目录下生成以下文件：

- factor_report.json
- factor_summary.json
- factor_research_report.md
- ic_curve.png
- long_short_curve.png

其中：
- `factor_report.json`：单因子结果报告
- `factor_summary.json`：多因子汇总结果
- `factor_research_report.md`：自动生成的 Markdown 研究报告
- `ic_curve.png`：IC 曲线图
- `long_short_curve.png`：Long-Short 收益曲线图
