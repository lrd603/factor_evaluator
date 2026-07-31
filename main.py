import pandas as pd

from evaluator.metrics import (
    calculate_daily_ic,
    calculate_daily_rank_ic,
    calculate_icir
)

# 读取因子数据
data = pd.read_csv("data/factor_data.csv")


print("读取的数据:")
print(data)


from evaluator.metrics import (
    calculate_daily_ic,
    calculate_daily_rank_ic
)


daily_ic = data.groupby("date").apply(
    calculate_daily_ic
)


daily_rank_ic = data.groupby("date").apply(
    calculate_daily_rank_ic
)


print("Daily IC:")
print(daily_ic)


print("\nDaily Rank IC:")
print(daily_rank_ic)

icir = calculate_icir(daily_ic)

print("\nICIR:")
print(icir)