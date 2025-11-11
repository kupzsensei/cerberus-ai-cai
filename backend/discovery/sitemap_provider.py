from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Iterable
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import httpx

from .utils import canon_url, within_recency, filter_by_keywords


async def _fetch_sitemap(domain: str, client: httpx.AsyncClient) -> list[dict]:
    # Try common sitemap paths
    candidates = [
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"https://{domain}/sitemap-index.xml",
    ]
    for url in candidates:
        try:
            resp = await client.get(url, headers={"User-Agent": "CerberusAI/1.0"}, timeout=10.0)
            if resp.status_code != 200 or not resp.text.strip():
                continue
            return _parse_sitemap_xml(resp.text)
        except Exception:
            continue
    return []


def _parse_sitemap_xml(xml_text: str) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items
    ns = {
        'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'
    }
    # If this is an index, there will be <sitemap><loc> entries
    for sm_entry in root.findall('.//sm:sitemap', ns):
        loc_el = sm_entry.find('sm:loc', ns)
        if loc_el is not None and loc_el.text:
            items.append({"url": loc_el.text.strip(), "title": loc_el.text.strip(), "dt": None})
    # If this is a urlset, parse urls
    for url_el in root.findall('.//sm:url', ns):
        loc_el = url_el.find('sm:loc', ns)
        lastmod_el = url_el.find('sm:lastmod', ns)
        if loc_el is None or not (loc_el.text or '').strip():
            continue
        link = (loc_el.text or '').strip()
        dt = None
        if lastmod_el is not None and lastmod_el.text:
            try:
                # Lastmod may be ISO8601
                dt = datetime.fromisoformat(lastmod_el.text.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                dt = None
        items.append({"url": link, "title": link, "dt": dt})
    return items


async def discover(
    sitemap_domains: Iterable[str],
    recency_days: int = 14,
    keyword_include: Iterable[str] | None = None,
    keyword_exclude: Iterable[str] | None = None,
) -> list[dict]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [asyncio.create_task(_fetch_sitemap(d, client)) for d in (sitemap_domains or [])]
        pages = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[dict] = []
    seen: set[str] = set()
    for page in pages:
        if isinstance(page, Exception):
            continue
        # If this was an index, page may contain nested sitemap URLs; ignore deep recursion for now
        for it in page:
            url = canon_url(it.get("url") or "")
            title = (it.get("title") or "").strip()
            dt = it.get("dt")
            if not url:
                continue
            k = url.lower()
            if k in seen:
                continue
            if not within_recency(dt, recency_days):
                continue
            if not filter_by_keywords(f"{title} {url}", keyword_include, keyword_exclude):
                continue
            seen.add(k)
            results.append({"url": url, "title": title or url})
    return results

