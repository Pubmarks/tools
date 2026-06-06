"""Yahoo fundamentals and financial statements (yfinance)."""
from __future__ import annotations

from datetime import datetime

import yfinance as yf

from .ohlcv_cache import filter_financials_by_date
from .yfinance_retry import yf_retry


def fundamentals_text(ticker: str) -> str:
    ticker_obj = yf.Ticker(ticker.upper())
    info = yf_retry(lambda: ticker_obj.info)

    if not info:
        return f"No fundamentals data found for symbol '{ticker}'"

    fields = [
        ("Name", info.get("longName")),
        ("Sector", info.get("sector")),
        ("Industry", info.get("industry")),
        ("Market Cap", info.get("marketCap")),
        ("PE Ratio (TTM)", info.get("trailingPE")),
        ("Forward PE", info.get("forwardPE")),
        ("PEG Ratio", info.get("pegRatio")),
        ("Price to Book", info.get("priceToBook")),
        ("EPS (TTM)", info.get("trailingEps")),
        ("Forward EPS", info.get("forwardEps")),
        ("Dividend Yield", info.get("dividendYield")),
        ("Beta", info.get("beta")),
        ("52 Week High", info.get("fiftyTwoWeekHigh")),
        ("52 Week Low", info.get("fiftyTwoWeekLow")),
        ("50 Day Average", info.get("fiftyDayAverage")),
        ("200 Day Average", info.get("twoHundredDayAverage")),
        ("Revenue (TTM)", info.get("totalRevenue")),
        ("Gross Profit", info.get("grossProfits")),
        ("EBITDA", info.get("ebitda")),
        ("Net Income", info.get("netIncomeToCommon")),
        ("Profit Margin", info.get("profitMargins")),
        ("Operating Margin", info.get("operatingMargins")),
        ("Return on Equity", info.get("returnOnEquity")),
        ("Return on Assets", info.get("returnOnAssets")),
        ("Debt to Equity", info.get("debtToEquity")),
        ("Current Ratio", info.get("currentRatio")),
        ("Book Value", info.get("bookValue")),
        ("Free Cash Flow", info.get("freeCashflow")),
    ]

    lines = [f"{label}: {value}" for label, value in fields if value is not None]
    header = f"# Company Fundamentals for {ticker.upper()}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + "\n".join(lines)


def statement_csv(
    ticker: str,
    kind: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    kind = kind.lower().strip()
    freq_l = freq.lower().strip()
    t = yf.Ticker(ticker.upper())

    if kind == "balance_sheet":
        data = yf_retry(
            lambda: t.quarterly_balance_sheet if freq_l == "quarterly" else t.balance_sheet
        )
        title = "Balance Sheet"
    elif kind == "cashflow":
        data = yf_retry(
            lambda: t.quarterly_cashflow if freq_l == "quarterly" else t.cashflow
        )
        title = "Cash Flow"
    elif kind == "income":
        data = yf_retry(
            lambda: t.quarterly_income_stmt if freq_l == "quarterly" else t.income_stmt
        )
        title = "Income Statement"
    else:
        raise ValueError("kind must be balance_sheet, cashflow, or income")

    data = filter_financials_by_date(data, curr_date)
    if data.empty:
        return f"No {title.lower()} data found for symbol '{ticker}'"

    csv_string = data.to_csv()
    header = f"# {title} data for {ticker.upper()} ({freq_l})\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    return header + csv_string
