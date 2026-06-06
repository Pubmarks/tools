"""Fetch full HTML pages for URLs listed in news index text files."""
from __future__ import annotations

import hashlib
import html as html_module
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[misc, assignment]

try:
    from curl_cffi import requests as curl_requests
except ImportError:  # pragma: no cover
    curl_requests = None  # type: ignore[misc, assignment]


LINK_RE = re.compile(r"^Link:\s*(\S+)\s*$", re.MULTILINE)
BLOCK_SPLIT = re.compile(r"(?=^###\s)", re.MULTILINE)

SCRAPE_PRIORITY = frozenset({
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "federalreserve.gov", "ecb.europa.eu", "bls.gov",
    "oecd.org", "imf.org", "worldbank.org", "bis.org",
})

SUMMARY_ONLY = frozenset({"ft.com", "wsj.com", "bloomberg.com"})

_JUNK_LINE = re.compile(
    r"^(?:"
    r"skip to .+|"
    r"advertisement\.?$|"
    r"story continues\.?$|"
    r"recommended stories\.?$|"
    r"trending (?:topics|tickers)\.?$|"
    r"top gainers\.?$|"
    r"explore further\.?$|"
    r"sign in(?: to .+)?\.?$|"
    r"subscribe(?: now)?\.?$|"
    r"unlock\.?$|"
    r"claim \d+% off.*|"
    r"privacy (?:policy|dashboard)\.?$|"
    r"terms(?: of use)?\.?$|"
    r"copyright ©.*|"
    r"report an issue\.?$|"
    r"disclaimer.*|"
    r"more info\.?$|"
    r"help\.?$|"
    r"feedback\.?$|"
    r"sitemap\.?$|"
    r"licensing\.?$|"
    r"what's new\.?$|"
    r"about our ads\.?$|"
    r"data disclaimer\.?$|"
    r"network\.?$|"
    r"u\.s\. markets closed\.?$|"
    r"new on yahoo\.?$|"
    r"latest\.?$|"
    r"editor'?s picks\.?$|"
    r"watch now\.?$|"
    r"\.{3,}$|"
    r"oops, something went wrong\.?$|"
    r"\d+ min read\.?$|"
    r"click here\.?$|"
    r"see .+ stock forecast\.?$"
    r")$",
    re.IGNORECASE,
)

_PROMO_SHORT = re.compile(
    r"(?i)^(hedge fund-level data|powerful investing tools|for smarter, sharper decisions|"
    r"unlock|smart investor picks|discover top-performing stock ideas and upgrade to a portfolio"
    r"|tipranks unlock|claim \d+% off).{0,120}$"
)

_ORPHAN_PERCENT = re.compile(r"^[+-]?\d+\.?\d*%$")
_TICKER_TOKEN = re.compile(r"^[\^]?[A-Z]{1,5}(?:\.PVT)?$")
_PRIVATE_TICKER = re.compile(r"^[A-Z]{1,8}\.PVT$")
_DATELINE = re.compile(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), .+\d{4} at .+$", re.IGNORECASE)
_MENU_CRUMB = re.compile(
    r"^(?:News|Politics|World|Weather|Sports|Finance|Tech|Life|Style|Shopping|"
    r"Health|Games|Videos|Podcasts|RSS|Jobs|Apps|More|Show all)$",
    re.IGNORECASE,
)


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host.removeprefix("www.")
    except Exception:
        return ""


def _slot_priority(url: str) -> int:
    d = _domain(url)
    if d in SCRAPE_PRIORITY:
        return 0
    if d in SUMMARY_ONLY:
        return 2
    return 1


@dataclass
class ArticleRecord:
    index: int
    url: str
    file: str
    http_status: int | None
    headline: str | None
    error: str | None
    text_chars: int
    paywall: bool = field(default=False)


def parse_news_company_blocks(text: str) -> list[tuple[str | None, str | None, str]]:
    """Return (headline, summary, url) for each article block that has a Link: line."""
    if "## Articles" in text:
        _, _, rest = text.partition("## Articles")
        body = rest
    else:
        body = text

    blocks = [b.strip() for b in BLOCK_SPLIT.split(body) if b.strip()]
    out: list[tuple[str | None, str | None, str]] = []
    for block in blocks:
        m = LINK_RE.search(block)
        if not m:
            continue
        url = m.group(1).strip()
        if not url.lower().startswith(("http://", "https://")):
            continue
        lines = block.splitlines()
        headline = None
        if lines and lines[0].strip().startswith("###"):
            headline = lines[0].strip().lstrip("#").strip()
        summary_lines = []
        for line in lines[1:]:
            ln = line.strip()
            if LINK_RE.match(ln) or ln.startswith("Link:"):
                break
            if ln:
                summary_lines.append(ln)
        summary = " ".join(summary_lines) if summary_lines else None
        out.append((headline, summary, url))
    return out


def _walk_json_ld_for_article_body(obj: Any) -> str | None:
    best: str | None = None
    best_len = 0

    def consider(s: str | None) -> None:
        nonlocal best, best_len
        if isinstance(s, str) and len(s.strip()) > best_len:
            best = s.strip()
            best_len = len(best)

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            ab = o.get("articleBody")
            if isinstance(ab, str):
                consider(ab)
            typ = o.get("@type")
            types = typ if isinstance(typ, list) else ([typ] if typ else [])
            flat_types = [t.lower() for t in types if isinstance(t, str)]
            if any(t in ("newsarticle", "article", "webpage") for t in flat_types):
                consider(o.get("description"))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for item in o:
                walk(item)

    walk(obj)
    return best


def _article_body_from_json_ld(soup: Any) -> str | None:
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        body = _walk_json_ld_for_article_body(data)
        if body and len(body) > 400:
            return html_module.unescape(body)
    return None


def _decompose_noise_tags(soup: Any) -> None:
    for tag in soup(["script", "style", "noscript", "template", "iframe", "svg"]):
        tag.decompose()
    for sel in (
        "nav", "header", "footer", "aside", "form", "button",
        "[role='navigation']", "[role='banner']", "[role='dialog']",
        "[aria-modal='true']", "[data-testid*='ad']",
        "[class*='ad-slot' i]", "[class*='AdSlot' i]",
        "[id*='masterNav' i]", "[id*='Navigation' i]",
        "[class*='consent' i]", "[class*='cookie' i]", "[id*='consent' i]",
    ):
        for el in soup.select(sel):
            el.decompose()


def _pick_main_article_root(soup: Any) -> Any:
    selectors = (
        "div.caas-body", "div[class*='caas-body']",
        "[data-testid='article-body']", "[itemprop='articleBody']",
        "article", "[role='article']", "main", "[role='main']",
    )
    best_el = None
    best_score = 0
    for sel in selectors:
        for el in soup.select(sel):
            t = el.get_text(separator=" ", strip=True)
            score = len(t)
            if score > best_score and score > 400:
                best_el = el
                best_score = score
    return best_el if best_el is not None else (soup.body or soup)


def _filter_text_lines(text: str) -> str:
    raw_lines: list[str] = []
    prev: str | None = None
    for line in text.splitlines():
        ln = line.strip()
        if not ln or ln == prev:
            continue
        prev = ln
        if _JUNK_LINE.match(ln):
            continue
        if len(ln) <= 2 and not ln.isdigit():
            continue
        if _MENU_CRUMB.match(ln) and len(ln) < 40:
            continue
        if len(ln) < 160 and _PROMO_SHORT.match(ln):
            continue
        if re.search(r"(?i)claim \d+% off tipranks", ln):
            continue
        if _PRIVATE_TICKER.match(ln):
            continue
        if _DATELINE.match(ln):
            continue
        if ln.strip() in {"TipRanks", "Yahoo Finance", "StockStory", "Simply Wall St."}:
            continue
        if ln.lower() in {"and", "or", "with", "the", "to", "of", "in", "at", "on", "by", "as", "is", "are"}:
            continue
        raw_lines.append(ln)

    out: list[str] = []
    i = 0
    while i < len(raw_lines):
        ln = raw_lines[i]
        nxt = raw_lines[i + 1] if i + 1 < len(raw_lines) else ""
        if _TICKER_TOKEN.match(ln) and _ORPHAN_PERCENT.match(nxt):
            i += 2
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def _html_to_text(html: str, max_chars: int = 120_000) -> str:
    if BeautifulSoup is None:
        return html[:max_chars]
    soup = BeautifulSoup(html, "html.parser")

    body_ld = _article_body_from_json_ld(soup)
    if body_ld:
        out = _filter_text_lines(body_ld)
        if len(out) > 400:
            if len(out) > max_chars:
                out = out[:max_chars] + "\n\n[truncated]"
            return out

    _decompose_noise_tags(soup)
    root = _pick_main_article_root(soup)
    text = root.get_text(separator="\n", strip=True)
    text = _filter_text_lines(text)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[truncated]"
    return text


def _fetch_url(url: str, timeout: float, max_retries: int = 2) -> tuple[int, str | None, str | None]:
    if curl_requests is None:
        return 0, None, "curl_cffi is not installed"

    last_err: str | None = None
    for attempt in range(max_retries + 1):
        try:
            session = curl_requests.Session()
            resp = session.get(url, impersonate="chrome", timeout=timeout, allow_redirects=True)
            code = int(resp.status_code)
            raw = resp.text if resp.text else ""
            return code, raw, None
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            if attempt >= max_retries:
                return 0, None, last_err
            import time
            time.sleep(1.5 * (attempt + 1))
    return 0, None, last_err


def fetch_news_company_pages(
    news_company_path: Path,
    out_dir: Path,
    *,
    timeout: float = 30.0,
    delay_s: float = 0.0,
) -> tuple[list[ArticleRecord], str | None]:
    """
    Read a news index text file, fetch each URL, write under ``out_dir``:
      manifest.json
      articles/article-NNNN-<hash>.md

    Returns (records, fatal_error).
    """
    if not news_company_path.is_file():
        return [], f"Input file not found: {news_company_path}"

    link_index = (
        "global" if "news_global" in news_company_path.name.lower() else "company"
    )

    raw = news_company_path.read_text(encoding="utf-8", errors="replace")
    triples = parse_news_company_blocks(raw)
    seen: set[str] = set()
    ordered: list[tuple[str | None, str | None, str]] = []
    for headline, summary, url in triples:
        if url in seen:
            continue
        seen.add(url)
        ordered.append((headline, summary, url))

    if not ordered:
        return [], "No Link: URLs found in input file"

    ordered.sort(key=lambda t: _slot_priority(t[2]))

    articles_dir = out_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    records: list[ArticleRecord] = []
    manifest_rows: list[dict[str, Any]] = []

    for i, (headline, summary, url) in enumerate(ordered, start=1):
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        fname = f"article-{i:04d}-{h}.md"
        rel = f"articles/{fname}"
        path = articles_dir / fname
        domain = _domain(url)
        is_paywall = False

        if domain in SUMMARY_ONLY:
            text_body = (summary or "") + f"\n[Paywalled source: {domain} — headline and summary only]\n"
            status = None
            err_out = None
            is_paywall = True
        else:
            if delay_s > 0 and i > 1:
                import time
                time.sleep(delay_s)
            status, html, err = _fetch_url(url, timeout=timeout)
            err_out = err
            text_body = ""
            if err:
                text_body = f"[fetch error]\n{err}\n"
            elif html is not None:
                if status >= 400:
                    text_body = f"[HTTP {status}]\n{html[:8000]}\n"
                else:
                    text_body = _html_to_text(html)
                    if len(text_body) < 400 and summary:
                        text_body = summary + "\n[Likely paywalled — body too short; summary used as fallback]\n"
                        is_paywall = True

        meta = {
            "url": url,
            "index": i,
            "http_status": status if status else None,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "headline_from_index": headline,
            "error": err_out,
            "paywall": is_paywall,
        }
        header = "---\n" + json.dumps(meta, indent=2) + "\n---\n\n"
        path.write_text(header + text_body, encoding="utf-8")

        rec = ArticleRecord(
            index=i, url=url, file=rel,
            http_status=status if status else None,
            headline=headline, error=err_out,
            text_chars=len(text_body), paywall=is_paywall,
        )
        records.append(rec)
        manifest_rows.append(asdict(rec))

    manifest = {
        "source_file": str(news_company_path),
        "link_index": link_index,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "article_count": len(manifest_rows),
        "articles": manifest_rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return records, None


def run_one_index_pages_fetch(
    src: Path,
    out: Path,
    *,
    timeout: float = 30.0,
    delay_s: float = 0.0,
) -> tuple[int, int, str | None]:
    """CLI helper — not used by the MCP server tools."""
    records, fatal = fetch_news_company_pages(src, out, timeout=timeout, delay_s=delay_s)
    if fatal:
        if "not found" in fatal.lower():
            return 2, 0, fatal
        if "No Link" in fatal:
            return 1, 0, None
        return 2, 0, fatal
    ok = sum(1 for r in records if r.error is None and r.http_status and r.http_status < 400)
    print(out / "manifest.json")
    print(f"# articles={len(records)} fetch_ok={ok} source={src.name}", file=sys.stderr)
    return 0, len(records), None
