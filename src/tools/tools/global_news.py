from __future__ import annotations

import tempfile
from pathlib import Path

from tools.app import mcp
from tools.envelope import Artifact, ToolResult
from tools.lib.news_pages import fetch_news_company_pages
from tools.lib.news_rss import rss_global_news_text
from tools.lib.news_yf import global_news_text


@mcp.tool()
def fetch_global_news(
    curr_date: str = "",
    lookback: int = 7,
    limit: int = 30,
    include_pages: bool = True,
    page_timeout: float = 30.0,
    page_delay: float = 0.0,
) -> dict:
    """Fetch broad market and macro news headlines and article bodies.

    Args:
        curr_date: As-of date YYYY-MM-DD. Defaults to today if not provided.
        lookback: Calendar days window. Default 7.
        limit: Max headlines after deduplication. Default 30.
        include_pages: Fetch and return full article bodies. Default True.
        page_timeout: Per-URL HTTP timeout in seconds. Default 30.
        page_delay: Delay in seconds between article requests. Default 0.
    """
    from datetime import date

    if not curr_date:
        curr_date = date.today().isoformat()

    yf_text = global_news_text(curr_date, lookback, limit)
    rss_text = rss_global_news_text(curr_date, lookback)
    combined = yf_text.rstrip() + "\n\n" + rss_text if rss_text.strip() else yf_text

    artifacts: list[Artifact] = [
        Artifact(
            path_hint="news_global.txt",
            media_type="text/plain",
            content=combined,
        )
    ]

    if include_pages and "Link:" in combined:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            index_file = tmp / "news_global.txt"
            index_file.write_text(combined, encoding="utf-8")
            pages_dir = tmp / "news_global_pages"

            fetch_news_company_pages(
                index_file, pages_dir,
                timeout=page_timeout, delay_s=page_delay,
            )

            manifest_file = pages_dir / "manifest.json"
            if manifest_file.exists():
                artifacts.append(Artifact(
                    path_hint="news_global_pages/manifest.json",
                    media_type="application/json",
                    content=manifest_file.read_text(encoding="utf-8"),
                ))

            articles_dir = pages_dir / "articles"
            if articles_dir.exists():
                for f in sorted(articles_dir.iterdir()):
                    artifacts.append(Artifact(
                        path_hint=f"news_global_pages/articles/{f.name}",
                        media_type="text/markdown",
                        content=f.read_text(encoding="utf-8", errors="replace"),
                    ))

    article_count = sum(1 for a in artifacts if a.path_hint.startswith("news_global_pages/articles/"))
    summary = f"Global market news as-of {curr_date}"
    if article_count:
        summary += f" — {article_count} articles fetched"

    return ToolResult(summary=summary, artifacts=artifacts).model_dump()
