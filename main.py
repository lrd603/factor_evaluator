import pandas as pd

from evaluator.metrics import (
    calculate_daily_ic,
    calculate_daily_rank_ic,
    calculate_icir
)
from evaluator.group_analysis import calculate_group_return
from evaluator.report import generate_report


# 读取因子数据
data = pd.read_csv("data/factor_data.csv")


print("读取的数据:")
print(data)


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

# 生成评价报告
generate_report(
    daily_ic,
    daily_rank_ic,
    icir,
    top_return,
    bottom_return,
    long_short_return
)