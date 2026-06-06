from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.fundamentals_yf import statement_csv
from tools.lib.ticker_safe import safe_ticker_component


@mcp.tool()
def fetch_statement(
    ticker: str,
    statement: str,
    freq: str = "quarterly",
    curr_date: str = "",
) -> dict:
    """Fetch a financial statement for a company.

    Args:
        ticker: Ticker symbol (e.g. AAPL).
        statement: One of 'balance_sheet', 'cashflow', 'income'.
        freq: 'quarterly' or 'annual'. Default 'quarterly'.
        curr_date: If set (YYYY-MM-DD), drop fiscal columns after this date to prevent look-ahead.
    """
    safe_ticker_component(ticker)
    if statement not in ("balance_sheet", "cashflow", "income"):
        raise ValueError("statement must be 'balance_sheet', 'cashflow', or 'income'")

    csv_content = statement_csv(ticker, statement, freq, curr_date or None)
    return ToolResult(
        summary=f"{ticker.upper()} {statement} ({freq})",
        artifacts=[
            Artifact(
                path_hint=f"{statement}.csv",
                media_type="text/csv",
                content=csv_content,
            )
        ],
    ).model_dump()
