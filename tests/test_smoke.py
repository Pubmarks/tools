"""Smoke tests — each tool wrapper called with mocked lib functions (no network)."""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _ohlcv_df():
    return pd.DataFrame({
        "Date": ["2024-01-02", "2024-01-03"],
        "Open": [185.0, 186.0],
        "High": [187.0, 188.0],
        "Low": [184.0, 185.0],
        "Close": [186.0, 187.0],
        "Volume": [50000000, 48000000],
    })


def test_fetch_ohlcv_returns_envelope():
    with patch("tools.tools.ohlcv.fetch_ohlcv_range", return_value=_ohlcv_df()):
        from tools.tools.ohlcv import fetch_ohlcv
        result = fetch_ohlcv("AAPL", "2024-01-01", "2024-01-31")
    assert result["summary"].startswith("AAPL")
    assert len(result["artifacts"]) == 1
    assert result["artifacts"][0]["path_hint"] == "ohlcv.csv"
    assert result["artifacts"][0]["media_type"] == "text/csv"


def test_fetch_ohlcv_empty():
    with patch("tools.tools.ohlcv.fetch_ohlcv_range", return_value=pd.DataFrame()):
        from tools.tools.ohlcv import fetch_ohlcv
        result = fetch_ohlcv("AAPL", "2024-01-01", "2024-01-02")
    assert result["artifacts"] == []


def test_fetch_fundamentals_returns_envelope():
    with patch("tools.tools.fundamentals.fundamentals_text", return_value="# Fundamentals\nPE: 28"):
        from tools.tools.fundamentals import fetch_fundamentals
        result = fetch_fundamentals("AAPL")
    assert result["artifacts"][0]["path_hint"] == "fundamentals.txt"
    assert "PE" in result["artifacts"][0]["content"]


def test_fetch_statement_returns_envelope():
    with patch("tools.tools.statement.statement_csv", return_value="# Balance Sheet\na,b\n1,2"):
        from tools.tools.statement import fetch_statement
        result = fetch_statement("AAPL", "balance_sheet")
    assert result["artifacts"][0]["path_hint"] == "balance_sheet.csv"


def test_fetch_statement_invalid_kind():
    from tools.tools.statement import fetch_statement
    with pytest.raises(ValueError, match="balance_sheet"):
        fetch_statement("AAPL", "profit_loss")


def test_fetch_insider_returns_envelope():
    with patch("tools.tools.insider.insider_transactions_text", return_value="# Insider\nDate,Shares\n"):
        from tools.tools.insider import fetch_insider
        result = fetch_insider("AAPL")
    assert result["artifacts"][0]["path_hint"] == "insider.txt"


def test_fetch_macro_returns_envelope():
    with patch("tools.tools.macro.macro_data_text", return_value="# FRED Macro\nUnemployment: 4%"):
        from tools.tools.macro import fetch_macro_data
        result = fetch_macro_data("2024-01-15")
    assert result["artifacts"][0]["path_hint"] == "macro_data.txt"


def test_fetch_avgpe_not_available():
    with patch("tools.tools.avgpe._fetch_avgpe", return_value=(None, None)):
        from tools.tools.avgpe import fetch_avgpe
        result = fetch_avgpe("AAPL")
    assert result["artifacts"] == []
    assert "not available" in result["summary"]


def test_fetch_avgpe_with_data():
    mock_data = {
        "ticker": "AAPL",
        "p_e_last": 28.5,
        "p_e_median": 26.0,
        "eps_last": 6.5,
        "price_last": 185.0,
        "p_e_shiller": 27.1,
        "p_e_harmonic": 27.0,
        "p_e_mean": 27.3,
        "p_e_mode": 25.0,
        "p_e_min": 14.0,
        "p_e_min_date": "2020-03-20",
        "p_e_max": 38.0,
        "p_e_max_date": "2021-01-04",
        "start_date": "2019-01-01",
        "end_date": "2024-01-01",
    }
    with patch("tools.tools.avgpe._fetch_avgpe", return_value=(mock_data, mock_data)):
        from tools.tools.avgpe import fetch_avgpe
        result = fetch_avgpe("AAPL")
    assert len(result["artifacts"]) == 2
    assert result["artifacts"][0]["path_hint"] == "avgpe_5.txt"
    assert result["artifacts"][1]["path_hint"] == "avgpe_10.txt"
    assert "ABOVE" in result["artifacts"][0]["content"] or "BELOW" in result["artifacts"][0]["content"]


def test_fetch_news_no_links():
    with patch("tools.tools.news.company_news_text", return_value="# AAPL news\nNo articles."):
        from tools.tools.news import fetch_news
        result = fetch_news("AAPL", "2024-01-01", "2024-01-31", include_pages=False)
    assert result["artifacts"][0]["path_hint"] == "news_company.txt"
    assert len(result["artifacts"]) == 1


def test_fetch_global_news_no_links():
    with patch("tools.tools.global_news.global_news_text", return_value="# Global\nHeadlines."):
        with patch("tools.tools.global_news.rss_global_news_text", return_value=""):
            from tools.tools.global_news import fetch_global_news
            result = fetch_global_news(curr_date="2024-01-15", include_pages=False)
    assert result["artifacts"][0]["path_hint"] == "news_global.txt"


def test_fetch_vwap_daily():
    df = _ohlcv_df().copy()
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = 186.0
    with patch("tools.tools.vwap.fetch_daily_vwap", return_value=df):
        from tools.tools.vwap import fetch_vwap
        result = fetch_vwap("AAPL", bars="daily", start="2024-01-01", end="2024-01-31")
    assert result["artifacts"][0]["path_hint"] == "vwap.csv"


def test_fetch_vwap_intraday_missing_date():
    from tools.tools.vwap import fetch_vwap
    with pytest.raises(ValueError, match="date"):
        fetch_vwap("AAPL", bars="intraday")


def test_fetch_indicators_invalid():
    from tools.tools.indicators import fetch_indicators
    with pytest.raises(ValueError, match="not supported"):
        fetch_indicators("AAPL", ["bad_indicator"], "2024-01-15")
