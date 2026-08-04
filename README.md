# A股因子自动评价系统

一个面向量化研究与实习项目展示的端到端因子分析工具。输入 A 股代码和研究区间后，系统会自动获取真实行情、构造基础因子、计算未来收益、完成横截面因子评价，并输出结构化结果、研究报告和可视化图表。

项目重点展示了一条可复用的量化研究流水线，而不只是单个指标的计算脚本：

```text
股票代码与日期区间
        ↓
AkShare A股日线行情
        ↓
因子构造与未来收益对齐
        ↓
IC / Rank IC / ICIR
        ↓
分组收益与多空组合
        ↓
Sharpe / 最大回撤 / 胜率
        ↓
因子评分、排名、报告与图表
```

## 项目背景

量化因子从提出到验证通常需要经过数据获取、数据清洗、因子构造、收益对齐、统计检验、组合回测和结果汇总等步骤。本项目将这些步骤组织为一个可以直接运行的研究流程，用于快速判断一个因子是否具备横截面选股能力。

当前版本支持：

- 使用 AkShare 获取沪深 A 股历史日线，主接口不可用时自动切换备用接口；
- 自动保留 `000001` 等股票代码的前导零；
- 自动生成动量、波动率和成交量因子；
- 计算未来 5 日收益，避免将当期收益作为预测目标；
- 批量计算 IC、Rank IC、ICIR、分组收益和多空收益；
- 计算 Sharpe Ratio、最大回撤和胜率；
- 输出 0–100 因子质量评分和排名；
- 生成 JSON、Markdown 研究报告和 PNG 图表；
- 兼容原有单因子、多因子手工 CSV。

## 整体架构

```text
factor_evaluator/
├─ main.py                         # 完整流程入口与命令行参数
├─ fetch_stock_data.py             # 独立行情下载命令
├─ generate_factors.py             # 独立因子生成命令
├─ data/
│  ├─ market_data.py               # AkShare 数据源、字段标准化与备用接口
│  ├─ raw_stock_data.csv           # 自动下载的 OHLCV 行情
│  └─ factor_data_generated.csv    # 自动生成的评价长表
├─ factors/
│  └─ generator.py                 # 因子、未来收益和长表生成
├─ evaluator/
│  ├─ metrics.py                   # IC、Rank IC、ICIR
│  ├─ group_analysis.py            # Top/Bottom 分组与多空收益
│  ├─ performance.py               # Sharpe、最大回撤、胜率
│  ├─ factor_runner.py             # 多因子批量调度
│  ├─ factor_score.py              # 综合评分与评级
│  ├─ report.py                    # JSON 与 Markdown 报告
│  └─ visualization.py             # IC 与累计多空曲线
├─ reports/                        # 自动生成的研究结果
└─ tests/                          # 数据、因子和评分单元测试
```

模块之间通过标准 DataFrame/CSV 字段衔接，数据获取、因子生成和评价逻辑相互独立，便于继续增加行情源、股票池或新因子。

## 因子定义

| 因子 | 定义 |
|---|---|
| `momentum` | `close / close.shift(20) - 1` |
| `volatility` | 日收益率的 20 日滚动标准差 |
| `volume_factor` | `volume / volume.rolling(20).mean() - 1` |

评价目标为未来 5 日收益：

```python
future_return_5d = close.shift(-5) / close - 1
```

生成的评价数据采用长表格式：

```text
date, stock, factor_name, factor_value, return
```

## 安装

推荐使用 Python 虚拟环境：

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

依赖包括 `pandas`、`matplotlib` 和 `akshare`。

## 完整运行示例

直接输入股票代码和研究区间：

```bash
python main.py --stocks 600519 000001 300750 --start 2023-01-01 --end 2024-12-31
```

该命令会依次执行：

1. 下载三只股票的真实历史行情；
2. 保存 `data/raw_stock_data.csv`；
3. 生成三个因子和未来 5 日收益；
4. 保存 `data/factor_data_generated.csv`；
5. 调用现有 evaluator 完成全部评价；
6. 输出因子排名、JSON 报告、Markdown 报告和图表。

如果已经存在 `data/raw_stock_data.csv`，可以跳过下载并直接运行：

```bash
python main.py
```

继续使用手工准备的因子 CSV：

```bash
python main.py --input data/factor_data_multi.csv
```

单独执行某个阶段：

```bash
python fetch_stock_data.py 600519 000001 300750 --start 2023-01-01 --end 2024-12-31
python generate_factors.py
```

## 输出结果

完整流程会生成：

```text
data/raw_stock_data.csv
data/factor_data_generated.csv
reports/factor_summary.json
reports/factor_research_report.md
reports/ic_curve.png
reports/long_short_curve.png
```

命令行排名示例：

```text
Factor Ranking:
1. volume_factor Score 51.9
2. volatility Score 42.6
3. momentum Score 32.3
```

`factor_summary.json` 示例：

```json
{
  "volume_factor": {
    "IC Mean": -0.0751,
    "ICIR": -0.1108,
    "Rank IC Mean": -0.0902,
    "Long Short Return": -0.003,
    "Sharpe Ratio": -1.0734,
    "Max Drawdown": -0.86,
    "Win Rate": 0.4326,
    "factor_score": 51.88,
    "rating": "Weak"
  }
}
```

评分用于比较因子的统计强度和可用性。负向稳定因子可以反转方向使用，因此评分层会识别负向预测强度；原始 IC、收益和风险指标仍按实际方向展示。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖：

- 股票代码校验和前导零；
- AkShare 字段映射和备用数据接口；
- 多股票行情合并与 CSV 保存；
- 三个因子及未来收益计算；
- 评分边界、收益尺度和回撤方向。

## 研究说明与可扩展方向

当前示例股票池只有三只股票，主要用于演示完整工程流程。正式因子研究应扩大横截面股票池，并进一步考虑交易成本、停牌、涨跌停、复权口径、行业与市值中性化、幸存者偏差及历史成分股变化。

后续可以扩展：

- 沪深 300、中证 500 等动态股票池；
- 价值、质量、流动性和基本面因子；
- 去极值、标准化和行业中性化；
- 多周期收益与因子衰减分析；
- 换手率、交易成本和更完整的组合回测；
- HTML 仪表盘或交互式研究报告。
