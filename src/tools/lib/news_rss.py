"""RSS feed fetcher for macro news from Reuters, FT, and Bloomberg."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

try:
    from curl_cffi import requests as curl_requests
except ImportError:  # pragma: no cover
    curl_requests = None  # type: ignore[misc, assignment]

_RSS_FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
    ("Financial Times", "https://www.ft.com/rss/home/uk"),
    ("Bloomberg", "https://feeds.bloomberg.com/economics/news.rss"),
]

_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _fetch_feed(url: str, timeout: float = 15.0) -> str | None:
    if curl_requests is not None:
        try:
            resp = curl_requests.get(url, impersonate="chrome", timeout=timeout)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=int(timeout)) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _parse_pub_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).replace(tzinfo=None)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _strip_html(text: str, max_chars: int = 1500) -> str:
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text[:max_chars]


def _item_summary(item: ET.Element) -> str:
    content = item.find("content:encoded", _NS)
    if content is not None and content.text:
        s = _strip_html(content.text)
        if len(s) > 80:
            return s
    desc = item.findtext("description") or ""
    return _strip_html(desc)


def rss_global_news_text(curr_date: str, look_back_days: int = 7, limit_per_feed: int = 10) -> str:
    """Fetch macro RSS feeds and return article blocks in the same ### format as global_news_text."""
    from dateutil.relativedelta import relativedelta

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - relativedelta(days=look_back_days)

    parts: list[str] = []
    seen: set[str] = set()

    for publisher, feed_url in _RSS_FEEDS:
        raw = _fetch_feed(feed_url)
        if not raw:
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            continue

        count = 0
        for item in root.findall(".//item"):
            if count >= limit_per_feed:
                break
            title = (item.findtext("title") or "").strip()
            if not title or title in seen:
                continue
            link = (item.findtext("link") or "").strip()
            pub_date = _parse_pub_date(item.findtext("pubDate"))
            if pub_date and (pub_date < start_dt or pub_date > curr_dt):
                continue
            summary = _item_summary(item)
            seen.add(title)
            line = f"### {title} (source: {publisher})\n"
            if summary:
                line += f"{summary}\n"
            if link:
                line += f"Link: {link}\n"
            parts.append(line + "\n")
            count += 1

    return "".join(parts)
