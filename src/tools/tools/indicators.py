from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.indicators import SUPPORTED_INDICATORS, indicator_series, indicator_window_text
from tools.lib.ticker_safe import safe_ticker_component


@mcp.tool()
def fetch_indicators(
    symbol: str,
    indicators: list[str],
    curr_date: str,
    lookback: int = 30,
    mode: str = "window",
) -> dict:
    """Fetch technical indicators for a symbol.

    Args:
        symbol: Ticker symbol (e.g. AAPL).
        indicators: One or more indicator names. Supported: close_50_sma, close_200_sma,
            close_10_ema, macd, macds, macdh, rsi, boll, boll_ub, boll_lb, atr, vwma, mfi.
        curr_date: As-of date YYYY-MM-DD — no data after this date is used.
        lookback: Calendar days of window to return (mode=window only). Default 30.
        mode: 'window' for human-readable daily lines, 'series' for CSV. Default 'window'.
    """
    safe_ticker_component(symbol)
    artifacts = []

    for ind in indicators:
        ind_lower = ind.strip().lower()
        if ind_lower not in SUPPORTED_INDICATORS:
            raise ValueError(
                f"indicator {ind!r} not supported; choose from {sorted(SUPPORTED_INDICATORS)}"
            )
        if mode == "series":
            df = indicator_series(symbol, ind_lower, curr_date)
            content = df.to_csv(index=False)
            artifacts.append(
                Artifact(
                    path_hint=f"indicators_{ind_lower}.csv",
                    media_type="text/csv",
                    content=content,
                )
            )
        else:
            text = indicator_window_text(symbol, ind_lower, curr_date, lookback)
            artifacts.append(
                Artifact(
                    path_hint="indicators.txt",
                    media_type="text/plain",
                    content=text,
                )
            )

    return ToolResult(
        summary=f"{symbol.upper()} indicators {', '.join(indicators)} as-of {curr_date}",
        artifacts=artifacts,
    ).model_dump()
