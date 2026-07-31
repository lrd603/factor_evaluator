import pandas as pd


def calculate_ic(factor_values, future_returns):
    factor = pd.Series(factor_values)
    returns = pd.Series(future_returns)

    ic = factor.corr(returns)

    return ic
def calculate_rank_ic(factor, returns):
    """
    计算Rank IC
    使用Spearman相关系数
    """
    return factor.corr(returns, method="spearman")


def calculate_icir(ic_series):
    """
    计算ICIR
    IC均值 / IC标准差
    """
    return ic_series.mean() / ic_series.std()

def calculate_daily_ic(group):
    """
    单日横截面IC
    """
    return group["factor"].corr(group["return"])


def calculate_daily_rank_ic(group):
    """
    单日Rank IC
    """
    return group["factor"].corr(
        group["return"],
        method="spearman"
    )
def calculate_icir(ic_series):
    """
    IC Information Ratio
    """
    return ic_series.mean() / ic_series.std()