from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.ticker_safe import safe_ticker_component
from tools.lib.vwap_yf import fetch_daily_vwap, fetch_intraday_vwap


@mcp.tool()
def fetch_vwap(
    symbol: str,
    bars: str = "daily",
    start: str = "",
    end: str = "",
    date: str = "",
) -> dict:
    """Fetch Volume-Weighted Average Price for a symbol.

    Args:
        symbol: Ticker symbol (e.g. AAPL).
        bars: 'daily' for cumulative daily VWAP over a range, or 'intraday' for 1-minute
            bars for a single session (last 30 days only). Default 'daily'.
        start: Start date YYYY-MM-DD (daily mode).
        end: End date YYYY-MM-DD (daily mode).
        date: Single trading date YYYY-MM-DD (intraday mode).
    """
    safe_ticker_component(symbol)

    if bars == "intraday":
        if not date:
            raise ValueError("date is required for intraday mode")
        df = fetch_intraday_vwap(symbol, date)
        if df.empty:
            return ToolResult(
                summary=f"{symbol.upper()} intraday VWAP {date} — no data",
                artifacts=[],
            ).model_dump()
        content = df.to_csv(index=False)
        return ToolResult(
            summary=f"{symbol.upper()} intraday VWAP {date} — {len(df)} bars",
            artifacts=[Artifact(path_hint="vwap.csv", media_type="text/csv", content=content)],
        ).model_dump()

    if not start or not end:
        raise ValueError("start and end are required for daily mode")
    df = fetch_daily_vwap(symbol, start, end)
    if df.empty:
        return ToolResult(
            summary=f"{symbol.upper()} daily VWAP {start}..{end} — no data",
            artifacts=[],
        ).model_dump()
    content = df.to_csv(index=False)
    return ToolResult(
        summary=f"{symbol.upper()} daily VWAP {start}..{end} — {len(df)} rows",
        artifacts=[Artifact(path_hint="vwap.csv", media_type="text/csv", content=content)],
    ).model_dump()
