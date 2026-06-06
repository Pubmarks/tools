"""VWAP via yfinance — daily rolling or intraday 1-minute."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from .ohlcv_cache import fetch_ohlcv_range
from .yfinance_retry import yf_retry


def fetch_intraday_vwap(symbol: str, trade_date: str) -> pd.DataFrame:
    """
    1-minute bars for ``trade_date`` with a running VWAP column.
    yfinance only provides 1m data for the last 30 calendar days.
    Returns an empty DataFrame when no data is available.
    """
    d = date.fromisoformat(trade_date)
    next_day = (d + timedelta(days=1)).isoformat()

    ticker = yf.Ticker(symbol.upper())
    raw = yf_retry(
        lambda: ticker.history(
            start=trade_date,
            end=next_day,
            interval="1m",
            prepost=False,
        )
    )
    if raw.empty:
        return pd.DataFrame()

    if raw.index.tz is not None:
        raw.index = raw.index.tz_localize(None)

    df = raw.reset_index().rename(columns={"index": "Datetime", "Datetime": "Datetime"})
    df = df[["Datetime", "Open", "High", "Low", "Close", "Volume"]].copy()
    df = df.dropna(subset=["Close", "Volume"])
    df = df[df["Volume"] > 0]

    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["CumTPV"] = (df["TP"] * df["Volume"]).cumsum()
    df["CumVol"] = df["Volume"].cumsum()
    df["VWAP"] = (df["CumTPV"] / df["CumVol"]).round(4)

    return df[["Datetime", "Open", "High", "Low", "Close", "Volume", "VWAP"]]


def fetch_daily_vwap(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Daily OHLCV bars with a rolling cumulative VWAP column.
    Uses typical_price = (H + L + C) / 3 as the daily price proxy.
    """
    df = fetch_ohlcv_range(symbol, start_date, end_date)
    if df.empty:
        return pd.DataFrame()

    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    df = df.dropna(subset=["Close", "Volume"])
    df = df[df["Volume"] > 0]
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["CumTPV"] = (df["TP"] * df["Volume"]).cumsum()
    df["CumVol"] = df["Volume"].cumsum()
    df["VWAP"] = (df["CumTPV"] / df["CumVol"]).round(4)

    return df[["Date", "Open", "High", "Low", "Close", "Volume", "VWAP"]]
