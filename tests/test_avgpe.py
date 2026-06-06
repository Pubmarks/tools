"""Unit tests for avgpe label correctness across 5-year and 10-year windows."""
from tools.tools.avgpe import _format_text, _valuation_signal

SAMPLE_DATA = {
    "ticker": "AAPL",
    "start_date": "2015-01-01",
    "end_date": "2025-01-01",
    "p_e_last": 30.0,
    "p_e_median": 25.0,
    "eps_last": 6.5,
    "price_last": 195.0,
    "p_e_shiller": 28.0,
    "p_e_harmonic": 24.5,
    "p_e_mean": 25.5,
    "p_e_mode": 24.0,
    "p_e_min": 12.0,
    "p_e_min_date": "2020-03-31",
    "p_e_max": 45.0,
    "p_e_max_date": "2021-09-30",
    "p_e_median_lossy": 25.5,
    "p_e_mean_lossy": 26.0,
    "p_e_mode_lossy": 25.0,
    "p_e_min_lossy": 13.0,
    "p_e_min_lossy_date": "2020-03-31",
    "p_e_max_lossy": 44.0,
    "p_e_max_lossy_date": "2021-09-30",
}


def test_format_text_10yr_labels():
    out = _format_text(SAMPLE_DATA, "10")
    assert "10-Year P/E Statistics (all quarters):" in out
    assert "10-Year P/E Statistics (profitable quarters only):" in out
    assert "10-year median" in out
    assert "5-Year P/E Statistics" not in out
    assert "5-year median" not in out


def test_format_text_5yr_labels():
    out = _format_text(SAMPLE_DATA, "5")
    assert "5-Year P/E Statistics (all quarters):" in out
    assert "5-Year P/E Statistics (profitable quarters only):" in out
    assert "5-year median" in out
    assert "10-Year P/E Statistics" not in out
    assert "10-year median" not in out


def test_valuation_signal_window():
    assert "10-year median" in _valuation_signal(30.0, 25.0, "10")
    assert "5-year median" in _valuation_signal(30.0, 25.0, "5")
