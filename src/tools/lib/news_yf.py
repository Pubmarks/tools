"""Company news, macro-style search news, and insider transactions via yfinance."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from dateutil.relativedelta import relativedelta

from .ticker_safe import safe_ticker_component
from .yfinance_retry import yf_retry


def _parse_pub_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
        except (OSError, ValueError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            return None
    return None


def _extract_article(article: dict) -> dict[str, Any]:
    if "content" in article and isinstance(article["content"], dict):
        content = article["content"]
        provider = content.get("provider") or {}
        publisher = provider.get("displayName", "Unknown") if isinstance(provider, dict) else "Unknown"
        url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
        link = url_obj.get("url", "") if isinstance(url_obj, dict) else ""
        pub = _parse_pub_date(content.get("pubDate") or content.get("displayTime"))
        return {
            "title": content.get("title", "No title"),
            "summary": content.get("summary") or content.get("description") or "",
            "publisher": publisher,
            "link": link,
            "pub_date": pub,
        }

    pub = _parse_pub_date(article.get("providerPublishTime") or article.get("pubDate"))
    return {
        "title": article.get("title", "No title"),
        "summary": article.get("summary", ""),
        "publisher": article.get("publisher", "Unknown"),
        "link": article.get("link", ""),
        "pub_date": pub,
    }


def company_news_text(ticker: str, start_date: str, end_date: str) -> str:
    """Ticker-scoped Yahoo Finance news, filtered to [start_date, end_date] when publish time exists."""
    safe_ticker_component(ticker)
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    try:
        stock = yf.Ticker(ticker.upper())
        news = yf_retry(lambda: stock.get_news(count=40))
        if not news:
            return f"No news found for {ticker}"

        parts: list[str] = []
        filtered = 0
        for article in news:
            data = _extract_article(article if isinstance(article, dict) else {})
            if data["pub_date"]:
                pub = data["pub_date"]
                if not (start_dt <= pub <= end_dt + relativedelta(days=1)):
                    continue
            line = f"### {data['title']} (source: {data['publisher']})\n"
            if data["summary"]:
                line += f"{data['summary']}\n"
            if data["link"]:
                line += f"Link: {data['link']}\n"
            parts.append(line + "\n")
            filtered += 1

        if filtered == 0:
            return f"No news found for {ticker} between {start_date} and {end_date}"

        header = f"# {ticker.upper()} news ({start_date} to {end_date})\n"
        header += f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + "## Articles\n\n" + "".join(parts)
    except Exception as e:  # noqa: BLE001
        return f"Error fetching news for {ticker}: {e}"


_MACRO_QUERIES = [
    "Federal Reserve interest rate decision FOMC",
    "ECB European Central Bank rate decision",
    "Bank of England interest rate",
    "Bank of Japan yield curve control",
    "US unemployment rate nonfarm payrolls",
    "eurozone unemployment rate EU labour market",
    "US jobless claims unemployment benefits",
    "US CPI inflation consumer prices",
    "US national debt deficit Treasury",
    "eurozone debt levels sovereign bond yield",
    "US China trade tariffs trade war",
    "EU US tariffs trade policy",
    "Section 232 tariffs steel aluminium",
    "Russia Ukraine war ceasefire sanctions",
    "Middle East conflict Israel Gaza",
    "Taiwan Strait China military",
    "NATO defence spending",
    "oil price OPEC crude WTI Brent",
    "natural gas LNG energy price",
    "gold price dollar index DXY",
    "China economy GDP property PMI",
]


def global_news_text(curr_date: str, look_back_days: int = 7, limit: int = 30) -> str:
    """Macro-oriented headlines from Yahoo Search, capped and de-duplicated by title."""
    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - relativedelta(days=look_back_days)
    start_s = start_dt.strftime("%Y-%m-%d")

    all_articles: list[dict] = []
    seen: set[str] = set()

    try:
        for query in _MACRO_QUERIES:
            search = yf_retry(
                lambda q=query: yf.Search(
                    query=q,
                    news_count=10,
                    enable_fuzzy_query=True,
                )
            )
            if not search.news:
                continue
            for article in search.news:
                if not isinstance(article, dict):
                    continue
                data = _extract_article(article)
                title = (data.get("title") or "").strip()
                if not title or title in seen:
                    continue
                if data.get("pub_date") and data["pub_date"] > curr_dt + relativedelta(days=1):
                    continue
                seen.add(title)
                all_articles.append(article)

        if not all_articles:
            return f"No global news found for {curr_date}"

        parts: list[str] = []
        for article in all_articles[:limit]:
            data = _extract_article(article)
            line = f"### {data['title']} (source: {data['publisher']})\n"
            if data["summary"]:
                line += f"{data['summary']}\n"
            if data["link"]:
                line += f"Link: {data['link']}\n"
            parts.append(line + "\n")

        header = f"# Global market news ({start_s} to {curr_date})\n"
        header += f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + "## Articles\n\n" + "".join(parts)
    except Exception as e:  # noqa: BLE001
        return f"Error fetching global news: {e}"


def insider_transactions_text(ticker: str) -> str:
    """Insider transaction table as CSV with header (yfinance)."""
    safe_ticker_component(ticker)
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        data = yf_retry(lambda: ticker_obj.insider_transactions)
        if data is None or getattr(data, "empty", True):
            return f"No insider transactions data found for symbol '{ticker}'"
        csv_body = data.to_csv()
        header = f"# Insider transactions for {ticker.upper()}\n"
        header += f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        return header + csv_body
    except Exception as e:  # noqa: BLE001
        return f"Error retrieving insider transactions for {ticker}: {e}"
