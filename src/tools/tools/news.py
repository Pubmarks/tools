from __future__ import annotations

import tempfile
from pathlib import Path

from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.news_pages import fetch_news_company_pages
from tools.lib.news_yf import company_news_text
from tools.lib.ticker_safe import safe_ticker_component


@mcp.tool()
def fetch_news(
    ticker: str,
    start: str,
    end: str,
    lookback: int = 7,
    limit: int = 10,
    include_pages: bool = True,
    page_timeout: float = 30.0,
    page_delay: float = 0.0,
) -> dict:
    """Fetch company news headlines and article bodies.

    Args:
        ticker: Ticker symbol (e.g. AAPL).
        start: Start date YYYY-MM-DD.
        end: End date YYYY-MM-DD.
        lookback: Calendar days window label. Default 7.
        limit: Max articles after deduplication. Default 10.
        include_pages: Fetch and return full article bodies. Default True.
        page_timeout: Per-URL HTTP timeout in seconds. Default 30.
        page_delay: Delay in seconds between article requests. Default 0.
    """
    safe_ticker_component(ticker)
    index_text = company_news_text(ticker, start, end)

    artifacts: list[Artifact] = [
        Artifact(
            path_hint="news_company.txt",
            media_type="text/plain",
            content=index_text,
        )
    ]

    if include_pages and "Link:" in index_text:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            index_file = tmp / "news_company.txt"
            index_file.write_text(index_text, encoding="utf-8")
            pages_dir = tmp / "news_company_pages"

            fetch_news_company_pages(
                index_file, pages_dir,
                timeout=page_timeout, delay_s=page_delay,
            )

            manifest_file = pages_dir / "manifest.json"
            if manifest_file.exists():
                artifacts.append(Artifact(
                    path_hint="news_company_pages/manifest.json",
                    media_type="application/json",
                    content=manifest_file.read_text(encoding="utf-8"),
                ))

            articles_dir = pages_dir / "articles"
            if articles_dir.exists():
                for f in sorted(articles_dir.iterdir()):
                    artifacts.append(Artifact(
                        path_hint=f"news_company_pages/articles/{f.name}",
                        media_type="text/markdown",
                        content=f.read_text(encoding="utf-8", errors="replace"),
                    ))

    article_count = sum(1 for a in artifacts if a.path_hint.startswith("news_company_pages/articles/"))
    summary = f"{ticker.upper()} news {start}..{end}"
    if article_count:
        summary += f" — {article_count} articles fetched"

    return ToolResult(summary=summary, artifacts=artifacts).model_dump()
