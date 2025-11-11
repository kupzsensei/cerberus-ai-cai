from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Iterable

import httpx
import feedparser  # type: ignore

from .utils import canon_url, within_recency, filter_by_keywords


async def _fetch_feed(url: str, client: httpx.AsyncClient) -> list[dict]:
    try:
        resp = await client.get(url, headers={"User-Agent": "CerberusAI/1.0"}, timeout=10.0)
        if resp.status_code != 200:
            return []
        parsed = feedparser.parse(resp.text)
        out = []
        for e in parsed.entries or []:
            link = getattr(e, "link", "") or getattr(e, "id", "")
            title = getattr(e, "title", "")
            # Prefer `published_parsed` then `updated_parsed`
            dt = None
            for attr in ("published_parsed", "updated_parsed"):
                v = getattr(e, attr, None)
                if v:
                    try:
                        dt = datetime(*v[:6])
                        break
                    except Exception:
                        dt = None
            out.append({"url": link, "title": title, "dt": dt})
        return out
    except Exception:
        return []


async def discover(
    rss_urls: Iterable[str],
    recency_days: int = 14,
    keyword_include: Iterable[str] | None = None,
    keyword_exclude: Iterable[str] | None = None,
) -> list[dict]:
    results: list[dict] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [asyncio.create_task(_fetch_feed(u, client)) for u in (rss_urls or [])]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
    seen: set[str] = set()
    for page in pages:
        if isinstance(page, Exception):
            continue
        for it in page:
            url = canon_url(it.get("url") or "")
            title = (it.get("title") or "").strip()
            dt = it.get("dt")
            if not url:
                continue
            key = url.lower()
            if key in seen:
                continue
            if not within_recency(dt, recency_days):
                continue
            if not filter_by_keywords(f"{title} {url}", keyword_include, keyword_exclude):
                continue
            seen.add(key)
            results.append({"url": url, "title": title})
    return results

