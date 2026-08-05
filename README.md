# Automated Quantitative Stock Scoring and Factor Research Platform

一个面向 A 股的自动化多因子研究、股票评分与历史回测平台。

输入股票代码后，系统可以自动获取行情和财务数据，计算技术、价值与质量因子，生成 0–100 的股票综合评分，并输出 Markdown 研究报告。项目同时提供股票池回测、沪深300基准比较、交易成本建模和因子 IC 有效性分析。

## 项目简介

项目将量化研究中的主要步骤组织为一条可复用的自动化流程：

```text
股票代码
    ↓
获取 A 股行情与财务数据
    ↓
计算技术、价值和质量因子
    ↓
标准化因子并生成股票评分
    ↓
股票池回测与沪深300基准比较
    ↓
输出股票评分、回测和因子研究报告
```

当公开数据接口暂时不可用时，数据层支持确定性 Mock 数据回退，便于离线开发和测试。真实数据与 Mock 数据会在命令行和报告中明确标识。

## 核心功能

### 1. 数据获取

- 通过 AkShare 获取 A 股历史 OHLCV 行情；
- 支持腾讯和 Eastmoney 行情端点回退；
- 获取历史 PE、PB 和 ROE 财务指标；
- 自动识别沪深市场代码；
- 真实接口不可用时支持 Mock fallback。

### 2. 因子体系

技术因子：

- `momentum_20`：20 日动量；
- `momentum_60`：60 日动量；
- `volatility_20`：20 日收益波动率；
- `volatility_60`：60 日收益波动率；
- `volume_change_20`：成交量相对20日均量变化。

价值因子：

- PE / Earnings Yield；
- PB / Book Yield。

质量因子：

- ROE。

研究层支持对上述因子计算横截面 IC、Rank IC、ICIR，并按因子有效性生成排名报告。

### 3. 股票评分

多因子综合评分采用以下权重：

| 评分维度 | 权重 | 主要因子 |
|---|---:|---|
| Technical | 40% | Momentum、Volatility、Volume |
| Value | 30% | PE、PB |
| Quality | 30% | ROE |

各因子先进行历史标准化，再转换为 0–100 分。系统同时保留旧版纯技术评分接口，保证已有研究流程兼容。

### 4. 股票池回测

- 支持可配置的多股票池；
- 默认股票池包含15只 A 股；
- 默认每20个交易日调仓；
- 默认选择评分最高的 Top 20%；
- Long-Only 等权组合；
- 预留 Long-Short 扩展接口；
- 默认交易成本为成交金额的 0.1%；
- 使用沪深300作为基准；
- 输出 Strategy Return、Benchmark Return 和 Alpha；
- 计算 Annual Return、Sharpe Ratio、Max Drawdown、Win Rate 和 Information Ratio。

## 项目结构

```text
factor_evaluator/
├── main.py                         # 交互式股票评分入口
├── stock_evaluator.py              # V2/V3 股票评分流程
├── data_loader/
│   └── stock_data.py               # A股历史行情与 Mock fallback
├── financial_loader/
│   └── financial_data.py           # PE、PB、ROE 财务数据
├── factor_engine/
│   ├── factor_builder.py           # evaluator 标准长表构建
│   ├── momentum.py                 # 20/60日动量
│   ├── volatility.py               # 20/60日波动率
│   ├── volume_factor.py            # 成交量因子
│   ├── value.py                    # PE/PB 价值因子
│   └── quality.py                  # ROE 质量因子
├── factor_analysis/
│   └── ic_analysis.py              # IC、Rank IC、ICIR与因子排名
├── evaluator/                      # 原始因子评价系统
│   ├── metrics.py
│   ├── group_analysis.py
│   ├── performance.py
│   ├── factor_score.py
│   ├── factor_runner.py
│   ├── report.py
│   └── visualization.py
├── backtest/
│   ├── engine.py                   # 回测引擎与沪深300基准
│   ├── portfolio.py                # Top 20%组合构建
│   ├── metrics.py                  # 回测风险收益指标
│   └── configured.py               # 配置化股票池回测入口
├── config/
│   └── stock_pool.py               # 默认股票池配置
├── data/                            # 示例及生成的数据
├── reports/                         # Markdown、JSON和PNG研究结果
└── tests/                           # 数据、因子、评分和回测测试
```

## 使用方法

### 安装依赖

建议使用 Python 虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 运行股票评分

```bash
python main.py
```

根据提示输入股票代码：

```text
请输入股票代码: 600519
```

系统将自动完成：

1. 获取历史行情；
2. 获取 PE、PB 和 ROE；
3. 计算技术、价值和质量因子；
4. 生成多因子股票评分；
5. 输出 `reports/stock_report.md`。

### 运行股票池回测

```python
from backtest import create_configured_backtest

engine = create_configured_backtest(
    start_date="2025-01-01",
    end_date="2026-08-04",
)

daily_returns = engine.run()
engine.generate_report()
print(engine.metrics)
```

默认股票池可在 `config/stock_pool.py` 中修改。回测报告输出到 `reports/backtest_report.md`。

### 运行因子 IC 分析

```python
from factor_analysis import analyze_factor_ic, generate_ic_report

analysis = analyze_factor_ic(factor_data)
generate_ic_report(analysis)
print(analysis)
```

输入数据使用标准长表格式：

```text
date, stock, factor_name, factor_value, return
```

### 运行测试

```bash
pytest -v
```

## 示例结果

### Stock Score

以 `600519` 为例：

```text
Stock: 600519
Technical Score: 59.71
Value Score: 92.03
Quality Score: 16.54
Final Score: 56.46
Data Source: AkShare
Financial Data Source: AkShare
```

完整报告：`reports/stock_report.md`。

### Factor Score

因子评价系统输出：

```text
IC Mean
Rank IC Mean
ICIR
Group Return
Long-Short Return
Sharpe Ratio
Max Drawdown
Win Rate
Factor Score
```

研究结果包括 `reports/factor_research_report.md`、`reports/factor_ic_report.md` 以及 IC 和多空收益曲线。

### Backtest Report

五股票示例回测结果：

```text
Stock Pool: 600519, 000001, 300750, 601318, 600036
Strategy Return: 19.18%
CSI 300 Benchmark Return: 22.39%
Alpha: -3.22%
Annual Return: 14.92%
Sharpe Ratio: 0.7070
Max Drawdown: -16.50%
```

这些结果仅用于展示研究流程，不构成投资建议。历史表现不代表未来收益。

## 技术栈

- Python
- Pandas
- NumPy
- AkShare
- Matplotlib
- Pytest

## 后续优化方向

- Streamlit Dashboard；
- 增加成长、现金流、估值变化和情绪因子；
- 扩大股票池并支持指数成分股动态更新；
- 增加行业和市值中性化；
- 增加滑点、涨跌停、停牌和更精细的交易成本模型；
- 增加滚动训练、样本外检验和因子衰减分析。

## 免责声明

本项目用于量化研究、工程实践和教学展示。项目输出不构成任何投资建议，使用者应自行评估数据质量、模型假设和市场风险。
