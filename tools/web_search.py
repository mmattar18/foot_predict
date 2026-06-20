"""Lightweight web-search backend for the qualitative tools (news, injuries).

Two free options, auto-selected:
- Tavily (if TAVILY_API_KEY is set) — more reliable, free tier ~1000/month;
  called via plain HTTP (no extra dependency).
- DuckDuckGo (default, no API key) via the `ddgs` package.

Returns an LLM-readable string, or None if no backend is available (so callers
can fall back to a clear message).
"""

import json
import os
import urllib.error
import urllib.request
from functools import lru_cache


def _format(results: list[dict]) -> str:
    lines = []
    for r in results:
        title = (r.get("title") or "").strip()
        body = (r.get("body") or r.get("content") or "").strip()
        href = (r.get("href") or r.get("url") or "").strip()
        snippet = f"{title}: {body}" if title else body
        snippet = snippet[:280]
        lines.append(f"- {snippet}" + (f" ({href})" if href else ""))
    return "\n".join(lines)


def _tavily(query: str, max_results: int) -> str | None:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, ValueError) as exc:
        return f"Web search unavailable (Tavily: {exc})."
    results = data.get("results", [])
    return _format(results) if results else None


def _duckduckgo(query: str, max_results: int) -> str | None:
    try:
        from ddgs import DDGS  # maintained package
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # legacy name
        except ImportError:
            return None
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as exc:  # noqa: BLE001 — network/ratelimit, stay graceful
        return f"Web search unavailable (DuckDuckGo: {exc})."
    return _format(results) if results else None


@lru_cache(maxsize=128)
def web_search(query: str, max_results: int = 5) -> str | None:
    """Run a web search. Prefers Tavily (if configured), else DuckDuckGo.

    Returns a formatted string, or None if no backend is available.
    """
    return _tavily(query, max_results) or _duckduckgo(query, max_results)
