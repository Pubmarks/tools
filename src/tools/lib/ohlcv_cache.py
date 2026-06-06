"""OHLCV download with on-disk cache, filtered to a simulation date (no look-ahead)."""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import yfinance as yf

from .paths import ensure_cache_dir
from .ticker_safe import safe_ticker_component
from .yfinance_retry import yf_retry


def _clean_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])

    price_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
    if price_cols:
        data[price_cols] = data[price_cols].apply(pd.to_numeric, errors="coerce")
    data = data.dropna(subset=["Close"])
    if price_cols:
        data[price_cols] = data[price_cols].ffill().bfill()

    return data


def cache_years() -> int:
    raw = os.environ.get("TOOLS_OHLCV_CACHE_YEARS", "5")
    try:
        y = int(raw)
        return max(1, min(y, 30))
    except ValueError:
        return 5


def load_ohlcv_cached(symbol: str, curr_date: str) -> pd.DataFrame:
    """
    Download a rolling window ending today, one CSV per symbol under the cache dir.
    Rows strictly after ``curr_date`` are dropped before return.
    """
    safe_symbol = safe_ticker_component(symbol)
    curr_date_dt = pd.to_datetime(curr_date)

    today_date = pd.Timestamp.today().normalize()
    years = cache_years()
    start_date = today_date - pd.DateOffset(years=years)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = today_date.strftime("%Y-%m-%d")

    cache_root = ensure_cache_dir()
    data_file = cache_root / f"{safe_symbol}-YFin-data-{start_str}-{end_str}.csv"

    if data_file.exists():
        data = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
    else:
        raw = yf_retry(
            lambda: yf.download(
                symbol,
                start=start_str,
                end=end_str,
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            )
        )
        data = raw.reset_index()
        data.to_csv(data_file, index=False, encoding="utf-8")

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]
    return data


def fetch_ohlcv_range(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Point-in-range OHLCV via Ticker.history; does not use the long-window disk cache."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")
    ticker = yf.Ticker(symbol.upper())
    data = yf_retry(lambda: ticker.history(start=start_date, end=end_date))
    if data.empty:
        return data
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)
    data = data.reset_index()
    if "Date" not in data.columns and data.index.name != "Date":
        date_col = [c for c in data.columns if str(c).lower() in ("date", "datetime")]
        if date_col:
            data = data.rename(columns={date_col[0]: "Date"})
    return data


def filter_financials_by_date(data: pd.DataFrame, curr_date: str | None) -> pd.DataFrame:
    """Drop statement columns (fiscal period end) after curr_date to avoid look-ahead."""
    if not curr_date or data.empty:
        return data
    cutoff = pd.Timestamp(curr_date)
    mask = pd.to_datetime(data.columns, errors="coerce") <= cutoff
    return data.loc[:, mask]
