"""Default, editable A-share research universe."""

from __future__ import annotations

import re


DEFAULT_STOCK_POOL = [
    "600519",  # 贵州茅台
    "000001",  # 平安银行
    "300750",  # 宁德时代
    "601318",  # 中国平安
    "600036",  # 招商银行
    "000858",  # 五粮液
    "000333",  # 美的集团
    "600276",  # 恒瑞医药
    "601166",  # 兴业银行
    "600887",  # 伊利股份
    "002594",  # 比亚迪
    "601888",  # 中国中免
    "000651",  # 格力电器
    "600030",  # 中信证券
    "601012",  # 隆基绿能
]


def get_stock_pool(stocks: list[str] | None = None) -> list[str]:
    """Return a validated copy of the configured or supplied stock pool."""
    selected = DEFAULT_STOCK_POOL if stocks is None else stocks
    normalized = list(dict.fromkeys(str(code).strip().zfill(6) for code in selected))
    invalid = [code for code in normalized if not re.fullmatch(r"\d{6}", code)]
    if invalid:
        raise ValueError(f"Invalid A-share stock codes: {invalid}")
    if not normalized:
        raise ValueError("Stock pool must not be empty")
    return normalized.copy()
