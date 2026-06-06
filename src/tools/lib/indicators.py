"""Technical indicators via stockstats on cached OHLCV."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from .ohlcv_cache import load_ohlcv_cached

SUPPORTED_INDICATORS = frozenset(
    {
        "close_50_sma",
        "close_200_sma",
        "close_10_ema",
        "macd",
        "macds",
        "macdh",
        "rsi",
        "boll",
        "boll_ub",
        "boll_lb",
        "atr",
        "vwma",
        "mfi",
    }
)


def indicator_series(symbol: str, indicator: str, curr_date: str) -> pd.DataFrame:
    ind = indicator.strip().lower()
    if ind not in SUPPORTED_INDICATORS:
        raise ValueError(
            f"indicator {indicator!r} not supported; choose from {sorted(SUPPORTED_INDICATORS)}"
        )
    data = load_ohlcv_cached(symbol, curr_date)
    df = wrap(data.copy())
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    _ = df[ind]  # triggers stockstats
    return df[["Date", ind]]


def indicator_window_text(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int = 30,
) -> str:
    """Human-readable lines for each calendar day in the lookback window."""
    ind = indicator.strip().lower()
    if ind not in SUPPORTED_INDICATORS:
        raise ValueError(
            f"indicator {indicator!r} not supported; choose from {sorted(SUPPORTED_INDICATORS)}"
        )

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - relativedelta(days=look_back_days)

    df = indicator_series(symbol, ind, curr_date)
    row_by_date = {r["Date"]: r[ind] for _, r in df.iterrows()}

    lines = []
    current_dt = curr_date_dt
    while current_dt >= before:
        date_str = current_dt.strftime("%Y-%m-%d")
        val = row_by_date.get(date_str)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            lines.append(f"{date_str}: N/A: Not a trading day (weekend or holiday)")
        else:
            lines.append(f"{date_str}: {val}")
        current_dt = current_dt - relativedelta(days=1)

    header = f"## {ind} values from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
    return header + "\n".join(lines) + "\n"
