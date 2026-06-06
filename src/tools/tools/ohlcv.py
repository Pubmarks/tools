from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.ohlcv_cache import fetch_ohlcv_range
from tools.lib.ticker_safe import safe_ticker_component


@mcp.tool()
def fetch_ohlcv(symbol: str, start: str, end: str) -> dict:
    """Fetch daily OHLCV bars for a symbol over a date range.

    Args:
        symbol: Ticker symbol (e.g. AAPL, 7203.T).
        start: Start date YYYY-MM-DD (inclusive).
        end: End date YYYY-MM-DD (inclusive).
    """
    safe_ticker_component(symbol)
    df = fetch_ohlcv_range(symbol, start, end)
    if df.empty:
        return ToolResult(
            summary=f"{symbol.upper()} OHLCV {start}..{end} — no data found",
            artifacts=[],
        ).model_dump()

    csv_content = df.round(2).to_csv(index=False)
    return ToolResult(
        summary=f"{symbol.upper()} OHLCV {start}..{end} — {len(df)} rows",
        artifacts=[
            Artifact(path_hint="ohlcv.csv", media_type="text/csv", content=csv_content)
        ],
    ).model_dump()
