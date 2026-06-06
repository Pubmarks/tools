from __future__ import annotations

import json
import urllib.request
from datetime import datetime

from tools.app import mcp
from tools.config import cfg
from tools.envelope import Artifact, ToolResult
from tools.lib.ticker_safe import safe_ticker_component


def _fetch_avgpe(ticker: str) -> dict | None:
    url = cfg.avgpe_base_url.format(ticker=ticker.lower())
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            if r.status != 200:
                return None
            return json.loads(r.read())
    except Exception:
        return None


def _valuation_signal(p_e_last: float, p_e_median: float) -> str:
    if p_e_median <= 0:
        return "Valuation signal: median P/E not available"
    pct = (p_e_last - p_e_median) / p_e_median * 100
    direction = "ABOVE" if pct >= 0 else "BELOW"
    return (
        f"Valuation signal: current P/E ({p_e_last:.2f}) is "
        f"{abs(pct):.0f}% {direction} 5-year median ({p_e_median:.2f})"
    )


def _format_text(data: dict) -> str:
    ticker = data.get("ticker", "").upper()
    p_e_last = data.get("p_e_last")
    p_e_median = data.get("p_e_median_5yr")
    lossy = data.get("p_e_lossy_5yr", 0)

    lines = [
        f"# 5-Year P/E Analysis: {ticker}",
        f"# Period: {data.get('start_date', '?')} to {data.get('end_date', '?')}",
        f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Current P/E (TTM):     {p_e_last}",
        f"EPS (last):            ${data.get('eps_last', 'N/A')}",
        f"Price (last):          ${data.get('price_last', 'N/A')}",
        "",
        "5-Year P/E Statistics:",
        f"  Median:              {p_e_median}   <- primary baseline",
        f"  Shiller (CAPE-5yr):  {data.get('p_e_shiller_5yr', 'N/A')}",
        f"  Mean:                {data.get('p_e_mean_5yr', 'N/A')}",
        f"  Mode:                {data.get('p_e_mode_5yr', 'N/A')}",
        f"  Min:                 {data.get('p_e_min', 'N/A')}  ({data.get('p_e_min_date', '?')})",
        f"  Max:                 {data.get('p_e_max', 'N/A')}  ({data.get('p_e_max_date', '?')})",
        "",
    ]

    if isinstance(p_e_last, (int, float)) and isinstance(p_e_median, (int, float)):
        lines.append(_valuation_signal(float(p_e_last), float(p_e_median)))

    lines.append(f"Loss-making quarters in period: {int(lossy) if lossy else 0}")
    if lossy:
        lines.append("NOTE: mean P/E unreliable due to loss-making quarters — prefer median and Shiller.")

    return "\n".join(lines) + "\n"


@mcp.tool()
def fetch_avgpe(ticker: str) -> dict:
    """Fetch current vs. historical 5-year P/E valuation statistics.

    Args:
        ticker: Ticker symbol (e.g. AAPL).
    """
    safe_ticker_component(ticker)
    data = _fetch_avgpe(ticker)
    if data is None:
        return ToolResult(
            summary=f"{ticker.upper()} P/E stats — not available",
            artifacts=[],
        ).model_dump()

    text = _format_text(data)
    return ToolResult(
        summary=f"{ticker.upper()} 5-year P/E analysis",
        artifacts=[Artifact(path_hint="avgpe.txt", media_type="text/plain", content=text)],
    ).model_dump()
