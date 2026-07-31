import pandas as pd

from evaluator.metrics import calculate_ic


# 读取因子数据
data = pd.read_csv("data/factor_data.csv")


print("读取的数据:")
print(data)


# 计算IC
ic = calculate_ic(
    data["factor"],
    data["return"]
)


print("\nFactor IC:", ic)