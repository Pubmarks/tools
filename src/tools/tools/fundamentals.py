from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.fundamentals_yf import fundamentals_text
from tools.lib.ticker_safe import safe_ticker_component


@mcp.tool()
def fetch_fundamentals(ticker: str) -> dict:
    """Fetch company fundamentals summary (PE, market cap, margins, etc.).

    Args:
        ticker: Ticker symbol (e.g. AAPL).
    """
    safe_ticker_component(ticker)
    text = fundamentals_text(ticker)
    return ToolResult(
        summary=f"{ticker.upper()} fundamentals",
        artifacts=[Artifact(path_hint="fundamentals.txt", media_type="text/plain", content=text)],
    ).model_dump()
