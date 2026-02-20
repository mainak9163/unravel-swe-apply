import re
import time
from html import unescape
from urllib.parse import urlparse

import requests
from ddgs import DDGS

from .config import (
    MAX_FETCH_PAGES,
    REQUEST_TIMEOUT_SEC,
    SERPER_API_KEY,
    TAVILY_API_KEY,
)
from .logging_setup import logger


def _dedupe_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in results:
        url = (item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped


def _search_serper(query: str, max_results: int) -> list[dict[str, str]]:
    if not SERPER_API_KEY:
        return []
    logger.info("search provider=serper query=%r", query)
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    data = response.json()
    organic = data.get("organic") or []
    return [
        {
            "title": str(item.get("title") or ""),
            "url": str(item.get("link") or ""),
            "snippet": str(item.get("snippet") or ""),
            "provider": "serper",
        }
        for item in organic
    ]


def _search_tavily(query: str, max_results: int) -> list[dict[str, str]]:
    if not TAVILY_API_KEY:
        return []
    logger.info("search provider=tavily query=%r", query)
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
        },
        timeout=REQUEST_TIMEOUT_SEC,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    return [
        {
            "title": str(item.get("title") or ""),
            "url": str(item.get("url") or ""),
            "snippet": str(item.get("content") or ""),
            "provider": "tavily",
        }
        for item in results
    ]


def _search_ddg(query: str, max_results: int) -> list[dict[str, str]]:
    logger.info("search provider=ddg query=%r", query)
    with DDGS(timeout=15) as ddgs:
        raw = list(
            ddgs.text(
                query,
                max_results=max_results,
                backend="lite",
                safesearch="off",
            )
        )
    return [
        {
            "title": str(item.get("title") or ""),
            "url": str(item.get("href") or ""),
            "snippet": str(item.get("body") or ""),
            "provider": "ddg",
        }
        for item in raw
    ]


def search_web(query: str, max_results: int = 6) -> list[dict[str, str]]:
    """Search using Serper/Tavily when available, with DDG fallback."""
    start = time.perf_counter()
    cleaned_query = (query or "").strip()
    safe_max_results = max(1, min(int(max_results or 6), 10))

    if not cleaned_query:
        logger.warning("search_web called with empty query")
        return []

    logger.info(
        "search_web start query=%r max_results=%d",
        cleaned_query,
        safe_max_results,
    )
    try:
        provider_calls = [
            ("serper", _search_serper),
            ("tavily", _search_tavily),
            ("ddg", _search_ddg),
        ]
        combined: list[dict[str, str]] = []
        for provider_name, provider_fn in provider_calls:
            try:
                provider_results = provider_fn(cleaned_query, safe_max_results)
                logger.info(
                    "search_web provider=%s results=%d",
                    provider_name,
                    len(provider_results),
                )
                combined.extend(provider_results)
            except Exception:
                logger.exception("search_web provider=%s failed", provider_name)
                continue
        results = _dedupe_results(combined)[:safe_max_results]
        logger.info(
            "search_web done query=%r results=%d total_duration_ms=%.1f",
            cleaned_query,
            len(results),
            (time.perf_counter() - start) * 1000,
        )
        return results
    except Exception:
        logger.exception(
            "search_web failed query=%r max_results=%d",
            cleaned_query,
            safe_max_results,
        )
        return []


def web_search(query: str, max_results: int = 6) -> str:
    """Compatibility formatter over search_web()."""
    results = search_web(query=query, max_results=max_results)
    if not results:
        return "No results found."
    lines = []
    for i, item in enumerate(results, 1):
        lines.append(f"[{i}] {item.get('title', '')}")
        lines.append(f"    URL: {item.get('url', '')}")
        lines.append(f"    {item.get('snippet', '')}")
        lines.append("")
    return "\n".join(lines)


def _domain_priority(url: str) -> int:
    domain = urlparse(url).netloc.lower()
    if "unravel.tech" in domain:
        return 0
    if "linkedin.com" in domain:
        return 1
    if "x.com" in domain or "twitter.com" in domain:
        return 2
    return 3


def _extract_text_from_html(html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def fetch_page_text(url: str) -> str:
    """Fetch and clean page text. Returns empty string if unavailable."""
    logger.info("fetch_page_text start url=%s", url)
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
            timeout=REQUEST_TIMEOUT_SEC,
        )
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            logger.info(
                "fetch_page_text skipped_non_html url=%s content_type=%s",
                url,
                content_type,
            )
            return ""
        text = _extract_text_from_html(response.text)
        if not text:
            return ""
        logger.info("fetch_page_text done url=%s chars=%d", url, len(text))
        return text[:6000]
    except Exception:
        logger.exception("fetch_page_text failed url=%s", url)
        return ""


def _extract_founder_excerpt(text: str) -> str:
    """Return a compact segment around founder-related keywords."""
    lowered = text.lower()
    keywords = ["founder", "co-founder", "founded", "founding", "ceo"]
    for keyword in keywords:
        idx = lowered.find(keyword)
        if idx != -1:
            start = max(0, idx - 350)
            end = min(len(text), idx + 950)
            return text[start:end]
    return text[:1200]


def collect_search_context() -> str:
    """Run multi-provider search, fetch top pages, and build evidence context."""
    queries = [
        "Unravel.tech founders startup founded in 2023",
        "site:unravel.tech founder",
        "site:linkedin.com/company unravel.tech founders",
        "site:linkedin.com/in unravel tech founder",
        "Unravel.tech AI startup founder profile",
    ]
    chunks = []
    all_results: list[dict[str, str]] = []

    for idx, query in enumerate(queries, 1):
        logger.info("collect_search_context query_%d=%r", idx, query)
        results = search_web(query=query, max_results=8)
        all_results.extend(results)
        if not results:
            chunks.append(f"Search Query {idx}: {query}\nNo results found.")
            continue
        lines = []
        for rank, item in enumerate(results, 1):
            lines.append(
                f"[{rank}] ({item.get('provider', 'unknown')}) {item.get('title', '')}\n"
                f"    URL: {item.get('url', '')}\n"
                f"    {item.get('snippet', '')}"
            )
        chunks.append(f"Search Query {idx}: {query}\n" + "\n".join(lines))

    seed_urls = [
        "https://unravel.tech/",
        "https://www.unravel.tech/",
        "https://unravel.tech/about",
        "https://www.unravel.tech/about",
    ]
    for url in seed_urls:
        all_results.append(
            {"title": "Seed URL", "url": url, "snippet": "", "provider": "seed"}
        )

    deduped = _dedupe_results(all_results)
    deduped.sort(key=lambda item: _domain_priority(item.get("url", "")))
    top_results = deduped[:MAX_FETCH_PAGES]
    logger.info(
        "collect_search_context unique_urls=%d fetched_urls=%d",
        len(deduped),
        len(top_results),
    )

    page_chunks = []
    for item in top_results:
        url = item.get("url", "")
        if not url:
            continue
        page_text = fetch_page_text(url)
        if not page_text:
            continue
        excerpt = _extract_founder_excerpt(page_text)
        page_chunks.append(
            f"URL: {url}\nTitle: {item.get('title', '')}\nExcerpt:\n{excerpt}\n"
        )

    if page_chunks:
        chunks.append("Fetched Page Evidence:\n" + "\n".join(page_chunks))

    return "\n\n".join(chunks)

