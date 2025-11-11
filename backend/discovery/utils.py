import asyncio
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from typing import Iterable

import httpx

try:
    # stdlib robots.txt parser
    import urllib.robotparser as robotparser
except Exception:  # pragma: no cover
    robotparser = None


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CerberusAI/1.0"


def canon_url(url: str) -> str:
    try:
        pu = urlparse(url)
        if not pu.scheme:
            return url
        # Remove query/fragment for canonicalization; keep path
        return f"{pu.scheme}://{pu.netloc}{pu.path}".rstrip("/")
    except Exception:
        return (url or "").strip()


def same_domain(url: str, domain: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        return host == domain.lower() or host.endswith("." + domain.lower())
    except Exception:
        return False


def looks_like_article(url: str) -> bool:
    u = url.lower()
    # Heuristics to avoid media files and utility pages
    if any(u.endswith(ext) for ext in [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".mp4", ".mp3", ".avi", ".mov", ".wmv",
        ".pdf", ".zip", ".rar", ".7z",
    ]):
        return False
    if any(seg in u for seg in ["/tag/", "/category/", "/page/", "/author/", "/feed"]):
        return False
    return True


def within_recency(dt: datetime | None, days: int) -> bool:
    if not dt:
        return True
    try:
        return dt >= (datetime.utcnow() - timedelta(days=days))
    except Exception:
        return True


def filter_by_keywords(text: str, include: Iterable[str] | None, exclude: Iterable[str] | None) -> bool:
    tl = (text or "").lower()
    if include:
        if not any(k.lower() in tl for k in include):
            return False
    if exclude:
        if any(k.lower() in tl for k in exclude):
            return False
    return True


_robots_cache: dict[str, tuple[datetime, object]] = {}


async def is_allowed_by_robots(domain: str, path: str, client: httpx.AsyncClient, cache_ttl_seconds: int = 3600) -> bool:
    if robotparser is None:
        return True
    try:
        now = datetime.utcnow()
        rp_rec = _robots_cache.get(domain)
        if not rp_rec or (now - rp_rec[0]).total_seconds() > cache_ttl_seconds:
            url = f"https://{domain}/robots.txt"
            try:
                resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=10.0)
                txt = resp.text if resp.status_code == 200 else ""
            except Exception:
                txt = ""
            rp = robotparser.RobotFileParser()
            rp.set_url(url)
            try:
                rp.parse(txt.splitlines())
            except Exception:
                pass
            _robots_cache[domain] = (now, rp)
        else:
            rp = rp_rec[1]
        try:
            return rp.can_fetch(USER_AGENT, f"https://{domain}{path}")
        except Exception:
            return True
    except Exception:
        return True


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    # Simple regex-based anchor extraction to avoid extra deps
    results: list[tuple[str, str]] = []
    for m in re.finditer(r"<a\s+[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", html or "", flags=re.IGNORECASE|re.DOTALL):
        href = m.group(1)
        text = re.sub(r"<[^>]+>", " ", m.group(2) or "").strip()
        if not href:
            continue
        abs_url = urljoin(base_url, href)
        results.append((abs_url, text))
    return results


async def fetch_text(url: str, client: httpx.AsyncClient) -> tuple[str, str | None, int]:
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT}, timeout=10.0, follow_redirects=True)
        if resp.status_code != 200:
            return "", None, resp.status_code
        html = resp.text
        # Strip some heavy sections and tags
        clean = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
        clean = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", clean)
        text = re.sub(r"(?is)<[^>]+>", " ", clean)
        text = re.sub(r"\s+", " ", text).strip()
        return text, html, 200
    except Exception:
        return "", None, 0

