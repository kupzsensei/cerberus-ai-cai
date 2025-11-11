from __future__ import annotations

import asyncio
from typing import Iterable
from urllib.parse import urlparse

import httpx

from .utils import extract_links, canon_url, looks_like_article, same_domain, is_allowed_by_robots


async def _crawl_domain_start(domain: str, client: httpx.AsyncClient, max_pages: int = 30) -> list[dict]:
    seeds = [f"https://{domain}/"]
    seen: set[str] = set()
    results: list[dict] = []
    for u in seeds:
        try:
            resp = await client.get(u, headers={"User-Agent": "CerberusAI/1.0"}, timeout=10.0)
            if resp.status_code != 200:
                continue
            for href, text in extract_links(resp.text, u):
                cu = canon_url(href)
                if not cu or cu.lower() in seen:
                    continue
                if not same_domain(cu, domain):
                    continue
                if not looks_like_article(cu):
                    continue
                # Robots.txt allow check
                try:
                    from urllib.parse import urlparse as _urlparse
                    p = _urlparse(cu).path or "/"
                except Exception:
                    p = "/"
                allowed = await is_allowed_by_robots(domain, p, client)
                if not allowed:
                    continue
                seen.add(cu.lower())
                results.append({"url": cu, "title": (text or '').strip() or cu})
                if len(results) >= max_pages:
                    break
        except Exception:
            continue
        if len(results) >= max_pages:
            break
    return results


async def discover(domains: Iterable[str], max_pages_per_domain: int = 30) -> list[dict]:
    results: list[dict] = []
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [asyncio.create_task(_crawl_domain_start(d, client, max_pages=max_pages_per_domain)) for d in (domains or [])]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
    seen: set[str] = set()
    for page in pages:
        if isinstance(page, Exception):
            continue
        for it in page:
            url = canon_url(it.get("url") or "")
            title = (it.get("title") or '').strip()
            if not url:
                continue
            k = url.lower()
            if k in seen:
                continue
            seen.add(k)
            results.append({"url": url, "title": title or url})
    return results
