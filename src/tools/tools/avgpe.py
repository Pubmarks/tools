from __future__ import annotations

import json
import urllib.request
from datetime import datetime

from tools.app import mcp
from tools.config import cfg
from tools.envelope import Artifact, ToolResult
from tools.lib.ticker_safe import safe_ticker_component


def _fetch_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            if r.status != 200:
                return None
            return json.loads(r.read())
    except Exception:
        return None


def _fetch_avgpe(ticker: str) -> tuple[dict | None, dict | None]:
    base = cfg.avgpe_base_url.format(ticker=ticker.upper())
    return _fetch_json(f"{base}/avgpe_5.json"), _fetch_json(f"{base}/avgpe_10.json")


def _valuation_signal(p_e_last: float, p_e_median: float) -> str:
    if p_e_median <= 0:
        return "Valuation signal: median P/E not available"
    pct = (p_e_last - p_e_median) / p_e_median * 100
    direction = "ABOVE" if pct >= 0 else "BELOW"
    return (
        f"Valuation signal: current P/E ({p_e_last:.2f}) is "
        f"{abs(pct):.0f}% {direction} 5-year median ({p_e_median:.2f})"
    )


def _fmt(v: object) -> str:
    return "N/A" if v is None else str(v)


def _format_text(data: dict, window: str) -> str:
    ticker = data.get("ticker", "").upper()
    p_e_last = data.get("p_e_last")
    p_e_median = data.get("p_e_median")

    lines = [
        f"# {window}-Year P/E Analysis: {ticker}",
        f"# Period: {data.get('start_date', '?')} to {data.get('end_date', '?')}",
        f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Current P/E (TTM):          {_fmt(p_e_last)}",
        f"EPS (last):                 ${_fmt(data.get('eps_last'))}",
        f"Price (last):               ${_fmt(data.get('price_last'))}",
        "",
        "5-Year P/E Statistics (all quarters):",
        f"  Median:                   {_fmt(p_e_median)}   <- primary baseline",
        f"  Shiller (CAPE-{window}yr):      {_fmt(data.get('p_e_shiller'))}",
        f"  Harmonic mean:            {_fmt(data.get('p_e_harmonic'))}",
        f"  Mean:                     {_fmt(data.get('p_e_mean'))}",
        f"  Mode:                     {_fmt(data.get('p_e_mode'))}",
        f"  Min:                      {_fmt(data.get('p_e_min'))}  ({_fmt(data.get('p_e_min_date'))})",
        f"  Max:                      {_fmt(data.get('p_e_max'))}  ({_fmt(data.get('p_e_max_date'))})",
        "",
        "5-Year P/E Statistics (profitable quarters only):",
        f"  Median (lossy excl.):     {_fmt(data.get('p_e_median_lossy'))}",
        f"  Mean (lossy excl.):       {_fmt(data.get('p_e_mean_lossy'))}",
        f"  Mode (lossy excl.):       {_fmt(data.get('p_e_mode_lossy'))}",
        f"  Min (lossy excl.):        {_fmt(data.get('p_e_min_lossy'))}  ({_fmt(data.get('p_e_min_lossy_date'))})",
        f"  Max (lossy excl.):        {_fmt(data.get('p_e_max_lossy'))}  ({_fmt(data.get('p_e_max_lossy_date'))})",
        "",
    ]

    if isinstance(p_e_last, (int, float)) and isinstance(p_e_median, (int, float)):
        lines.append(_valuation_signal(float(p_e_last), float(p_e_median)))

    return "\n".join(lines) + "\n"


@mcp.tool()
def fetch_avgpe(ticker: str) -> dict:
    """Fetch current vs. historical P/E valuation statistics (5-year and 10-year windows).

    Args:
        ticker: Ticker symbol (e.g. AAPL).
    """
    safe_ticker_component(ticker)
    data5, data10 = _fetch_avgpe(ticker)
    if data5 is None and data10 is None:
        return ToolResult(
            summary=f"{ticker.upper()} P/E stats — not available",
            artifacts=[],
        ).model_dump()

    artifacts = []
    if data5 is not None:
        artifacts.append(Artifact(path_hint="avgpe_5.txt", media_type="text/plain", content=_format_text(data5, "5")))
    if data10 is not None:
        artifacts.append(Artifact(path_hint="avgpe_10.txt", media_type="text/plain", content=_format_text(data10, "10")))

    return ToolResult(
        summary=f"{ticker.upper()} P/E analysis — 5-year and 10-year",
        artifacts=artifacts,
    ).model_dump()
