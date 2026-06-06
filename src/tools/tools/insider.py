from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.news_yf import insider_transactions_text
from tools.lib.ticker_safe import safe_ticker_component


@mcp.tool()
def fetch_insider(ticker: str) -> dict:
    """Fetch insider transactions for a company.

    Args:
        ticker: Ticker symbol (e.g. AAPL).
    """
    safe_ticker_component(ticker)
    text = insider_transactions_text(ticker)
    return ToolResult(
        summary=f"{ticker.upper()} insider transactions",
        artifacts=[Artifact(path_hint="insider.txt", media_type="text/plain", content=text)],
    ).model_dump()
