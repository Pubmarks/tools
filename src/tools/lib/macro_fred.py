"""FRED API fetcher for key macroeconomic series."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# (label, series_id, unit, obs_limit)
_SERIES: list[tuple[str, str, str, int]] = [
    ("US Unemployment Rate",       "UNRATE",              "%",     6),
    ("US Nonfarm Payrolls",        "PAYEMS",              "K jobs",3),
    ("US CPI (All Urban)",         "CPIAUCSL",            "index", 6),
    ("Fed Funds Rate",             "FEDFUNDS",            "%",     3),
    ("10-Year Treasury Yield",     "DGS10",               "%",     10),
    ("2-Year Treasury Yield",      "DGS2",                "%",     10),
    ("US Federal Debt",            "GFDEBTN",             "$bn",   3),
    ("Broad Dollar Index",         "DTWEXBGS",            "index", 10),
    ("Eurozone Unemployment Rate", "LRHUTTTTEZM156S",     "%",     6),
    ("Brent Crude Oil",            "DCOILBRENTEU",        "$/bbl", 10),
]


def _fetch_series(series_id: str, api_key: str, obs_limit: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": obs_limit,
    })
    url = f"{FRED_BASE}?{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    return [o for o in data.get("observations", []) if o.get("value", ".") != "."]


def _trend_str(obs: list[dict[str, Any]]) -> str:
    vals = [o["value"] for o in reversed(obs)]
    return " → ".join(vals)


def macro_data_text(curr_date: str) -> str:
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        return "Error: FRED_API_KEY environment variable not set"

    lines: list[str] = [
        f"# FRED Macro Data (as of {curr_date})",
        f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for label, series_id, unit, obs_limit in _SERIES:
        lines.append(f"## {label} ({series_id})")
        try:
            obs = _fetch_series(series_id, api_key, obs_limit)
        except Exception as e:  # noqa: BLE001
            lines.append(f"Error: {e}")
            lines.append("")
            continue

        if not obs:
            lines.append("No data available")
            lines.append("")
            continue

        lines.append(f"Latest:   {obs[0]['value']} {unit} ({obs[0]['date']})")
        if len(obs) > 1:
            lines.append(f"Previous: {obs[1]['value']} {unit} ({obs[1]['date']})")
        if len(obs) >= 3:
            lines.append(f"Trend (oldest→latest): {_trend_str(obs)}")
        lines.append("")

    return "\n".join(lines)
