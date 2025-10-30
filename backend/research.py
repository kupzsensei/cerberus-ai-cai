import os
import logging
import httpx
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from serpapi import GoogleSearch
from typing import Optional
import json
import re
import time
from datetime import datetime
import calendar
from urllib.parse import urlparse
from html import unescape
import database
import utils


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables (optional; we degrade gracefully if absent)
serpapi_api_key = os.environ.get("SERPAPI_API_KEY")
tavily_api_key = os.environ.get("TAVILY_API_KEY")
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
if not openrouter_api_key:
    logger.warning("OPENROUTER_API_KEY not set; proceeding without it (only needed for certain backends)")
if not serpapi_api_key and not tavily_api_key:
    logger.warning("No SERPAPI_API_KEY or TAVILY_API_KEY configured; search fallback will be limited unless seed URLs are provided")

# Corrected domain list
include_domains = [
    "cyberdaily.au",
    "sbs.com.au",
    "infosecurity-magazine.com",
    "crowdstrike.com",
    "blackpointcyber.com",
    "thehackernews.com",
    "darkreading.com",
    # Government/official sources
    "asd.gov.au",
    "acsc.gov.au",
    "cyber.gov.au",
    "oaic.gov.au",
    # Additional reputable sources to reach >=10 incidents
    "abc.net.au",
    "itnews.com.au",
    "smh.com.au",
    "afr.com",
    "news.com.au",
    "9news.com.au",
    "7news.com.au",
    "theguardian.com",
    "securityweek.com",
    "bleepingcomputer.com",
    "csoonline.com",
    "theregister.com",
    "zdnet.com",
    "scmagazine.com",
    "databreaches.net",
    "reuters.com"
]

# Extract date range (YYYY-MM-DD) from the query string
def _parse_date_range_from_query(q: str):
    if not q:
        return None, None
    # from YYYY-MM-DD to YYYY-MM-DD
    m = re.search(r'from\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})', q, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    # from Month YYYY to Month YYYY -> first/last day of months
    m = re.search(r'from\s+([A-Za-z]+)\s+(\d{4})\s+to\s+([A-Za-z]+)\s+(\d{4})', q, re.IGNORECASE)
    if m:
        months = {m: i for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"], start=1)}
        sm = months.get(m.group(1).capitalize())
        em = months.get(m.group(3).capitalize())
        sy = int(m.group(2)); ey = int(m.group(4))
        if sm and em:
            start = f"{sy:04d}-{sm:02d}-01"
            end_day = calendar.monthrange(ey, em)[1]
            end = f"{ey:04d}-{em:02d}-{end_day:02d}"
            return start, end
    return None, None

# Helper: normalize SerpAPI organic results to our common schema
def _normalize_serpapi_results(resp: dict) -> dict:
    results = []
    for r in resp.get("organic_results", []) or []:
        url = r.get("link") or r.get("url")
        title = r.get("title") or ""
        snippet = r.get("snippet") or r.get("snippet_highlighted_words", [])
        if isinstance(snippet, list):
            snippet = " ".join(snippet)
        results.append({
            "url": url or "",
            "title": title,
            "content": snippet or ""
        })
    return {"results": results}

# Primary search via SERPAPI (Google) with AU preference
def _search_serpapi(query: str, num: int = 50, gl: str = "au", hl: str = "en", extra_params: Optional[dict] = None) -> dict:
    params = {
        "engine": "google",
        "q": query,
        "num": num,
        "gl": gl,
        "hl": hl,
        "api_key": serpapi_api_key,
    }
    if extra_params:
        params.update({k: v for k, v in extra_params.items() if v is not None})
    search = GoogleSearch(params)
    resp = search.get_dict()
    return _normalize_serpapi_results(resp)

# Fallback search via Tavily
def _search_tavily(query: str, max_results: int = 50, include_domains_list=None) -> dict:
    t = TavilySearch(
        max_results=max_results,
        topic="general",
        search_depth="advanced",
        include_domains=include_domains_list or None,
    )
    results = t.invoke(query)
    return results

# Config-driven limits
_limits_cfg = utils.config.get('research_limits', {})
MAX_RESULTS_TO_ANALYZE = _limits_cfg.get('max_results_to_analyze', 12)
MAX_ARTICLE_CHARS = _limits_cfg.get('max_article_chars', 4000)
TARGET_MIN_RESULTS = _limits_cfg.get('target_min_results', MAX_RESULTS_TO_ANALYZE)
# Enforce at least 10, or the configured target if higher
MIN_RESULTS_ENFORCED = max(TARGET_MIN_RESULTS, 10)

# Function to perform a search
async def perform_search(query, server_name: str = None, model_name: str = "granite3.3", server_type: str = "ollama", seed_urls: list | None = None, focus_on_seed: bool = True):
    """
    Performs a research search using the specified AI server and model.
    
    Args:
        query: The search query
        server_name: Name of the AI server to use
        model_name: Name of the model to use
        server_type: Type of server (ollama or gemini)
        
    Returns:
        tuple: (result, generation_time) or (error_message, None)
    """
    try:
        # Start timer for the entire research process
        overall_start_time = time.time()

        # Determine which AI server to use
        selected_server = None
        server_url_or_key = None

        if server_type == "ollama":
            if server_name:
                selected_server = await database.get_ollama_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_ollama_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Ollama servers configured.")
            server_url_or_key = selected_server['url']
            llm = ChatOllama(
                model=model_name,
                temperature=0,
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url=server_url_or_key.replace("/api/generate", "/")
            )
            # Test connection to the selected Ollama server using async HTTP client
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{server_url_or_key.replace('/api/generate', '')}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(f"Failed to connect to Ollama server at {server_url_or_key}")
        elif server_type == "gemini":
            if server_name:
                selected_server = await database.get_external_ai_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_external_ai_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Gemini servers configured.")
            server_url_or_key = selected_server['api_key']
            llm = ChatGoogleGenerativeAI(
                model=f"models/gemini-2.5-flash",
                temperature=0,
                google_api_key=server_url_or_key
            )
        else:
            raise ValueError(f"Unsupported server type: {server_type}")

        # Preprocess query with unique timestamp to avoid caching
        if "Australia" not in query:
            query = f"{query} Australia cybersecurity incidents timestamp:{int(time.time())}"
        # Extract date range from the query (used later for filtering and for a second-pass query)
        range_start, range_end = _parse_date_range_from_query(query)
        logger.info(f"Processing query: {query}")
        
        # Get raw results: SERPAPI primary (prefer news), Tavily fallback
        import asyncio
        raw_results = {"results": []}

        # Seed-mode: focus on explicit URLs when provided
        if seed_urls:
            try:
                # Normalize list of URLs
                seeds = []
                for u in seed_urls:
                    u = (u or "").strip()
                    if not u:
                        continue
                    seeds.append({"url": u, "title": u, "content": ""})
                raw_results["results"] = seeds
                logger.info(f"Seed URL mode: {len(seeds)} URLs provided")
            except Exception as e:
                logger.warning(f"Failed to prepare seed URLs: {e}")

        # If not focusing only on seeds, augment with search results
        if (not focus_on_seed) or (not seed_urls):
            try:
                if serpapi_api_key:
                    extra = {"tbm": "nws"}
                    if range_start and range_end:
                        extra["tbs"] = f"cdr:1,cd_min:{range_start},cd_max:{range_end}"
                    sr = await asyncio.get_event_loop().run_in_executor(None, _search_serpapi, query, 100, "au", "en", extra)
                    logger.info("Raw SERPAPI results retrieved")
                    raw_results["results"].extend(sr.get("results", []))
            except Exception as e:
                logger.warning(f"SERPAPI search failed, will try Tavily fallback: {e}")
            if tavily_api_key:
                try:
                    tr = await asyncio.get_event_loop().run_in_executor(None, _search_tavily, query, 50, include_domains)
                    logger.info("Raw Tavily results retrieved (fallback)")
                    raw_results["results"].extend(tr.get("results", []))
                except Exception as e:
                    logger.error(f"Tavily fallback failed: {e}")
        
        # Filter results to ensure regional and incident relevance (looser criteria)
        def _is_candidate_result(item: dict) -> bool:
            url = item.get("url", "") or ""
            content_lc = (item.get("content", "") or "").lower()
            try:
                netloc = urlparse(url).netloc.lower()
            except Exception:
                netloc = ""
            domain_ok = any(d in url for d in include_domains) or netloc.endswith(".au")
            region_ok = ("australia" in content_lc) or ("australian" in content_lc)
            incident_ok = any(t in content_lc for t in [
                "ransomware", "data breach", "breach", "cyberattack", "attack",
                "leak", "exfiltration", "ddos", "exploit", "vulnerability", "malware"
            ])
            return (domain_ok or region_ok) and incident_ok

        raw_list = raw_results.get("results", [])
        filtered_results = [r for r in raw_list if _is_candidate_result(r)]
        logger.info(f"Filtered results count: {len(filtered_results)} (from {len(raw_list)})")

        # If too few candidates, do a second pass (prefer Tavily unrestricted)
        if len(filtered_results) < MIN_RESULTS_ENFORCED:
            range_clause = f" from {range_start} to {range_end}" if range_start and range_end else ""
            enriched_query = f"{query} (ransomware OR \"data breach\" OR cyberattack OR hack){range_clause}"
            more_results = {"results": []}
            if tavily_api_key:
                try:
                    tavily_tool_unrestricted = TavilySearch(
                        max_results=50,
                        topic="general",
                        search_depth="advanced",
                    )
                    more_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool_unrestricted.invoke, enriched_query)
                    logger.info("Second Tavily pass fetched")
                except Exception as e:
                    logger.warning(f"Second-pass Tavily failed: {e}")
            if not more_results.get("results") and serpapi_api_key:
                try:
                    # Prefer Google News vertical with optional custom date range
                    extra = {"tbm": "nws"}
                    if range_start and range_end:
                        extra["tbs"] = f"cdr:1,cd_min:{range_start},cd_max:{range_end}"
                    more_results = await asyncio.get_event_loop().run_in_executor(None, _search_serpapi, enriched_query, 100, "au", "en", extra)
                    logger.info("Second pass via SERPAPI fetched")
                except Exception as e:
                    logger.warning(f"Second-pass SERPAPI failed: {e}")
            # Filter for relevance; allow .au or Australia mentions and cyber keywords
            extra = []
            for r in more_results.get("results", []):
                url = r.get("url", "")
                content_lc = (r.get("content", "") or "").lower()
                try:
                    netloc = urlparse(url).netloc.lower()
                except Exception:
                    netloc = ""
                region_ok = netloc.endswith('.au') or ("australia" in content_lc) or ("australian" in content_lc)
                incident_ok = any(t in content_lc for t in ["ransomware","phishing","ddos","exploit","vulnerability","data breach","cyberattack","breach","leak","malware"])
                if region_ok and incident_ok:
                    extra.append(r)
            # Deduplicate by URL
            seen = {r["url"] for r in filtered_results}
            for r in extra:
                if r.get("url") and r["url"] not in seen:
                    filtered_results.append(r)
                    seen.add(r["url"])
            # If still low, try SERPAPI on top security news + AU news domains
            if len(filtered_results) < MIN_RESULTS_ENFORCED and serpapi_api_key:
                try:
                    top_domains = [
                        "thehackernews.com","securityweek.com","bleepingcomputer.com",
                        "csoonline.com","theregister.com","zdnet.com","scmagazine.com",
                        "databreaches.net","darkreading.com","cyberdaily.au",
                        # AU outlets
                        "abc.net.au","smh.com.au","afr.com","news.com.au","9news.com.au","7news.com.au","theage.com.au","itnews.com.au"
                    ]
                    domain_query = f"{query} (breach OR ransomware OR cyberattack) (" + " OR ".join([f'site:{d}' for d in top_domains]) + ")"
                    extra = {"tbm": "nws"}
                    if range_start and range_end:
                        extra["tbs"] = f"cdr:1,cd_min:{range_start},cd_max:{range_end}"
                    more2 = await asyncio.get_event_loop().run_in_executor(None, _search_serpapi, domain_query, 70, "au", "en", extra)
                    extra_candidates = [
                        r for r in more2.get("results", [])
                        if any(term in (r.get("content", "").lower()) for term in [
                            "australia","australian","ransomware","phishing","ddos","exploit","vulnerability","data breach","cyberattack","breach","leak"
                        ])
                    ]
                    for r in extra_candidates:
                        if r.get("url") and r["url"] not in seen:
                            filtered_results.append(r)
                            seen.add(r["url"])
                    logger.info("Domain-focused SERPAPI pass fetched")
                except Exception as e:
                    logger.warning(f"Domain-focused SERPAPI pass failed: {e}")
        
        # Deduplicate by URL and title before formatting
        def _dedupe_results(items: list[dict]) -> list[dict]:
            seen = set()
            out = []
            for r in items:
                url = (r.get("url") or "").strip().lower()
                # Strip query/fragments
                try:
                    pu = urlparse(url)
                    canon_url = f"{pu.scheme}://{pu.netloc}{pu.path}".rstrip("/")
                except Exception:
                    canon_url = url.rstrip("/")
                title_key = re.sub(r"\W+", "", (r.get("title") or "").lower())[:80]
                key = (canon_url, title_key)
                if key in seen:
                    continue
                seen.add(key)
                out.append(r)
            return out

        filtered_results = _dedupe_results(filtered_results)

        # Generate output from raw results and filter by date range, if provided
        # Run the formatting in a thread pool to avoid blocking
        enforce_min = False if seed_urls else True
        output = await asyncio.get_event_loop().run_in_executor(None, format_raw_results, filtered_results, 0, llm, range_start, range_end, enforce_min)
        
        if not output.strip():
            logger.warning("No relevant results found")
            return "No cybersecurity incidents relevant to Australian businesses found for the requested timeframe.", None
        
        overall_end_time = time.time()
        generation_time = overall_end_time - overall_start_time

        await database.add_research(query, output, generation_time, selected_server['name'], model_name)
        return output, generation_time
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        # Check for model-specific errors
        if "is not supported" in str(e) or "Invalid model" in str(e):
            error_message = f"The selected model '{model_name}' is not suitable for this research task. Please try a different model, such as 'granite3.3'."
            return error_message, None
        return f"Error processing query: {str(e)}", None

# Function to format raw results
def format_raw_results(results, start_count, llm, range_start=None, range_end=None, enforce_min: bool = True):
    output = ""
    included = 0

    incident_keywords = (
        "breach", "attack", "ransomware", "extortion", "data leak", "leaked",
        "hacked", "cyberattack", "intrusion", "compromise", "outage"
    )
    non_incident_keywords = (
        "op-ed", "op ed", "opinion", "analysis", "predictions", "awareness month",
        "legislation", "act passed", "bill", "law", "aggregator", "roundup", "round-up",
        "rules", "policy", "regulation", "regulatory", "report", "trends", "trend report",
        "awareness", "election", "strategy", "framework", "act", "legislation",
        "list of", "complete list", "notifications", "notification", "digest", "weekly",
        "monthly", "annual", "what we know", "explainer", "guide", "webinar", "register",
        "sign up", "panel", "roundtable", "fireside", "forecast", "landscape", "overview",
        "top ransomware groups", "battle", "what to expect"
    )

    def _normalize_method(m: str) -> str:
        if not m:
            return "Not specified"
        t = m.strip().lower()
        if t in {"not specified","n/a","na","none","unknown","-","no"}:
            return "Not specified"
        mapping = {
            "ransom": "Ransomware",
            "lockbit": "Ransomware",
            "blackcat": "Ransomware",
            "double extortion": "Ransomware",
            "extortion": "Ransomware",
            "data breach": "Data breach",
            "breach": "Data breach",
            "leak": "Data breach",
            "exfiltration": "Data breach",
            "phishing": "Phishing",
            "credential": "Credential stuffing",
            "ddos": "DDoS",
            "denial of service": "DDoS",
            "vulnerability": "Vulnerability exploitation",
            "exploit": "Vulnerability exploitation",
            "sql injection": "Vulnerability exploitation",
            "supply chain": "Supply chain compromise",
            "third-party": "Supply chain compromise",
            "bec": "Business email compromise",
            "business email": "Business email compromise",
            "vishing": "Vishing",
            "voice phishing": "Vishing",
            "backdoor": "Malware/Backdoor",
            "malware": "Malware/Backdoor",
            "espionage": "Espionage",
        }
        for k, v in mapping.items():
            if k in t:
                return v
        # If the method doesn't map to a known class, treat as unknown
        return "Not specified"

    def _fetch_page_content(page_url: str, fallback: str):
        try:
            parsed = urlparse(page_url)
            domain = parsed.netloc.lower()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            resp = httpx.get(page_url, headers=headers, timeout=10.0, follow_redirects=True)
            if resp.status_code != 200:
                return fallback, None
            html = resp.text
            # Strip scripts/styles and common boilerplate tags
            html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
            html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
            html = re.sub(r"(?is)<nav[^>]*>.*?</nav>", " ", html)
            html = re.sub(r"(?is)<header[^>]*>.*?</header>", " ", html)
            html = re.sub(r"(?is)<footer[^>]*>.*?</footer>", " ", html)
            # Remove all tags
            text = re.sub(r"(?is)<[^>]+>", " ", html)
            text = unescape(text)
            text = re.sub(r"\s+", " ", text).strip()
            # Limit length to avoid overloading prompt
            if len(text) > MAX_ARTICLE_CHARS:
                text = text[:MAX_ARTICLE_CHARS]
            # Prefer fetched content if it seems longer than the snippet
            if len(text) > max(len(fallback), 1000):
                return text, resp.text
            return fallback, resp.text
        except Exception as e:
            logger.info(f"Full page fetch failed for {page_url}: {e}")
            return fallback, None

    def _format_header_date_range(rs: str | None, re_: str | None) -> str | None:
        try:
            if not rs or not re_:
                return None
            from datetime import datetime as _dt
            sdt = _dt.strptime(rs, "%Y-%m-%d")
            edt = _dt.strptime(re_, "%Y-%m-%d")
            same_year = sdt.year == edt.year
            month_map = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            if same_year:
                if sdt.month == edt.month:
                    return f"{month_map[sdt.month-1]} {sdt.day} - {month_map[edt.month-1]} {edt.day}, {edt.year}"
                else:
                    return f"{month_map[sdt.month-1]} {sdt.day} - {month_map[edt.month-1]} {edt.day}, {edt.year}"
            else:
                return f"{month_map[sdt.month-1]} {sdt.day}, {sdt.year} - {month_map[edt.month-1]} {edt.day}, {edt.year}"
        except Exception:
            return None

    def _pretty_date(date_str: str) -> str:
        if not date_str or date_str.strip().lower() == "not specified":
            return "Not specified"
        s = date_str.strip()
        try:
            # YYYY-MM-DD
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
                y, m, d = s.split("-")
                month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
                return f"{month_names[int(m)-1]} {int(d)}, {y}"
            # YYYY-MM
            if re.fullmatch(r"\d{4}-\d{2}", s):
                y, m = s.split("-")
                month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
                return f"{month_names[int(m)-1]} {y}"
            # YYYY
            if re.fullmatch(r"\d{4}", s):
                return s
        except Exception:
            pass
        return s

    def _extract_cves(text: str) -> list[str]:
        if not text:
            return []
        try:
            matches = re.findall(r"\bCVE-\d{4}-\d{4,7}\b", text, flags=re.IGNORECASE)
            # Normalize to upper and dedupe while preserving order
            seen = set()
            cves = []
            for m in matches:
                up = m.upper()
                if up not in seen:
                    seen.add(up)
                    cves.append(up)
            return cves
        except Exception:
            return []

    def _extract_date_from_url(u: str) -> str:
        try:
            m = re.search(r'/([0-9]{4})/([0-9]{2})/([0-9]{2})(?:/|$)', u)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y:04d}-{mo:02d}-{d:02d}"
            m = re.search(r'([0-9]{4})-([0-9]{2})-([0-9]{2})', u)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y:04d}-{mo:02d}-{d:02d}"
            # Also detect compact YYYYMMDD anywhere in the URL (e.g., -20250915-)
            m = re.search(r'(?:[^0-9]|^)((20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01]))(?:[^0-9]|$)', u)
            if m:
                y = int(m.group(2)); mo = int(m.group(3)); d = int(m.group(4))
                if 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y:04d}-{mo:02d}-{d:02d}"
        except Exception:
            pass
        return None

    def _infer_targets_from_title(title: str) -> str | None:
        try:
            t = title.strip()
            # Patterns like "Acme Corp data breach", "XYZ hit by ransomware"
            m = re.search(r"^([A-Z][A-Za-z0-9&\-\.]+(?:\s+[A-Z][A-Za-z0-9&\-\.]+){0,4})\s+(?:data breach|breach|ransomware|cyber ?attack|hack|incident)", t, re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                # Avoid generic words
                bad = {"The", "A", "An", "Australia", "Australian", "Cyber", "Security", "Data", "Breach"}
                if candidate not in bad and len(candidate) > 2:
                    return candidate
        except Exception:
            pass
        return None

    def _is_specific_target(targets: str) -> bool:
        if not targets or targets.strip().lower() == "not specified":
            return False
        t = targets.strip()
        # Reject overly generic targets
        generic = {
            "businesses","australian businesses","australians","consumers","customers","citizens","residents",
            "industry","industries","sectors","companies","government","governments","public sector",
            "education","universities","schools","healthcare","hospitals","critical infrastructure"
        }
        if t.lower() in generic:
            return False
        # Look for proper nouns/entities
        if re.search(r"\b([A-Z][\w&\-\.]+(?:\s+[A-Z][\w&\-\.]+){0,3})\b", t):
            return True
        # Company suffixes
        if re.search(r"\b(Pty|Ltd|Limited|Corp|Corporation|Inc|LLC|PLC)\b", t, re.IGNORECASE):
            return True
        return False

    def _extract_metadata_date(raw_html: str) -> str:
        if not raw_html:
            return None
        try:
            # Look for JSON-LD datePublished/dateCreated/dateModified
            for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw_html, re.IGNORECASE | re.DOTALL):
                json_text = m.group(1)
                # Find ISO-like timestamps
                d = re.search(r'"date(Published|Created|Modified)"\s*:\s*"([^"]+)"', json_text, re.IGNORECASE)
                if d:
                    iso = d.group(2)
                    # Extract YYYY-MM-DD if present
                    mdate = re.search(r'(\d{4}-\d{2}-\d{2})', iso)
                    if mdate:
                        return mdate.group(1)
                    # Fallback to YYYY-MM
                    mdate = re.search(r'(\d{4}-\d{2})', iso)
                    if mdate:
                        return mdate.group(1)
                    # Fallback to YYYY
                    mdate = re.search(r'(\d{4})', iso)
                    if mdate:
                        return mdate.group(1)
            # OpenGraph/Meta tag
            m = re.search(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']', raw_html, re.IGNORECASE)
            if m:
                iso = m.group(1)
                mdate = re.search(r'(\d{4}-\d{2}-\d{2})', iso)
                if mdate:
                    return mdate.group(1)
                mdate = re.search(r'(\d{4}-\d{2})', iso)
                if mdate:
                    return mdate.group(1)
                mdate = re.search(r'(\d{4})', iso)
                    
                if mdate:
                    return mdate.group(1)
        except Exception as e:
            logger.info(f"Metadata date extraction failed: {e}")
        return None

    def _normalize_date_for_filter(date_str: str):
        # Returns (start_date, end_date) strings for range checks, or (None, None)
        if not date_str or date_str.strip().lower() == "not specified":
            return None, None
        ds = date_str.strip()
        # Exact date
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})", ds)
        if m:
            return m.group(1), m.group(1)
        # Year-month
        m = re.fullmatch(r"(\d{4})-(\d{2})", ds)
        if m:
            y = int(m.group(1)); mo = int(m.group(2))
            last = calendar.monthrange(y, mo)[1]
            return f"{y:04d}-{mo:02d}-01", f"{y:04d}-{mo:02d}-{last:02d}"
        # Quarter (Q1 2025)
        m = re.fullmatch(r"Q([1-4])\s+(\d{4})", ds, re.IGNORECASE)
        if m:
            q = int(m.group(1)); y = int(m.group(2))
            start_mo = (q - 1) * 3 + 1
            end_mo = start_mo + 2
            end_day = calendar.monthrange(y, end_mo)[1]
            return f"{y:04d}-{start_mo:02d}-01", f"{y:04d}-{end_mo:02d}-{end_day:02d}"
        return None, None

    def _within_range(incident_start: str, incident_end: str, rs: str, re_: str) -> bool:
        try:
            if not rs or not re_:
                return True
            if not incident_start and not incident_end:
                return False
            # If only one bound, use it for both
            s = incident_start or incident_end
            e = incident_end or incident_start
            sdt = datetime.strptime(s, "%Y-%m-%d")
            edt = datetime.strptime(e, "%Y-%m-%d")
            rsdt = datetime.strptime(rs, "%Y-%m-%d"); redt = datetime.strptime(re_, "%Y-%m-%d")
            # Overlap check (incident window intersects [rs,re])
            return not (edt < rsdt or sdt > redt)
        except Exception:
            return True

    def _extract_date_from_text(text: str) -> str:
        try:
            # Common patterns: 2025-10-11, 11 October 2025, October 11, 2025, 11 Oct 2025
            m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
            if m:
                return m.group(1)
            m = re.search(r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", text, re.IGNORECASE)
            if m:
                # Normalize to YYYY-MM-DD with day padded
                month_map = {m: i for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"], start=1)}
                day = int(m.group(1))
                month = month_map[m.group(2).capitalize()]
                year = int(m.group(3))
                return f"{year:04d}-{month:02d}-{day:02d}"
            m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})\b", text, re.IGNORECASE)
            if m:
                month_map = {m: i for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"], start=1)}
                month = month_map[m.group(1).capitalize()]
                day = int(m.group(2))
                year = int(m.group(3))
                return f"{year:04d}-{month:02d}-{day:02d}"
            m = re.search(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+(\d{4})\b", text, re.IGNORECASE)
            if m:
                month_map = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Sept":9,"Oct":10,"Nov":11,"Dec":12}
                day = int(m.group(1))
                month = month_map[m.group(2).capitalize()]
                year = int(m.group(3))
                return f"{year:04d}-{month:02d}-{day:02d}"
        except Exception:
            pass
        return None

    def _sanitize_date_field(date_str: str) -> str:
        if not date_str:
            return "Not specified"
        s = date_str.strip()
        if not s or s.lower() == "not specified":
            return "Not specified"
        # Discard obvious mis-parses where another field label bled into the value
        if any(lbl in s for lbl in ("Targets:", "Method:", "Incident")):
            return "Not specified"
        # Prefer strict YYYY-MM-DD if present
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", s)
        if m:
            return m.group(1)
        # Accept YYYY-MM
        m = re.search(r"\b(\d{4}-\d{2})\b", s)
        if m:
            return m.group(1)
        # Try to parse natural language date within the string
        nat = _extract_date_from_text(s)
        if nat:
            return nat
        return "Not specified"

    def _infer_method_from_text(text: str) -> str:
        t = text.lower()
        checks = [
            ("double extortion", "Ransomware"),
            ("ransomware", "Ransomware"),
            ("data breach", "Data breach"),
            ("exfiltration", "Data breach"),
            ("leak", "Data breach"),
            ("phishing", "Phishing"),
            ("business email", "Business email compromise"),
            ("bec", "Business email compromise"),
            ("credential", "Credential stuffing"),
            ("ddos", "DDoS"),
            ("denial of service", "DDoS"),
            ("sql injection", "Vulnerability exploitation"),
            ("vulnerability", "Vulnerability exploitation"),
            ("exploit", "Vulnerability exploitation"),
            ("supply chain", "Supply chain compromise"),
            ("third-party", "Supply chain compromise"),
            ("backdoor", "Malware/Backdoor"),
            ("malware", "Malware/Backdoor"),
            ("espionage", "Espionage"),
        ]
        for k, v in checks:
            if k in t:
                return v
        return "Not specified"

    def _sanitize_summary(s: str) -> str:
        if not s:
            return s
        # Remove any stray field lines the LLM might have echoed
        s = re.sub(r"(?mi)^(?:Date of Incident|Targets|Method|Incident\?):.*$", "", s)
        # Collapse whitespace and keep a single clean paragraph
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _sanitize_field(val: str) -> str:
        if not val:
            return "Not specified"
        v = str(val).strip()
        if not v:
            return "Not specified"
        v = re.sub(r"(?mi)^(?:Date of Incident|Targets|Method|Incident\?):\s*", "", v).strip()
        if v.lower() in {"not specified","n/a","na","none","unknown","-","no"}:
            return "Not specified"
        return v

    def _is_hard_exclude(title_text: str, content_text: str) -> bool:
        tl = (title_text or "").lower()
        cl = (content_text or "").lower()
        terms = [
            "annual cyber threat report",
            "annual report",
            "quarterly report",
            "notifiable data breaches",
            "data breach notifications",
            "list of data breaches",
            "complete list",
            "roundup",
            "round-up",
            "digest",
            "newsletter",
        ]
        return any(t in tl or t in cl for t in terms)

    # Header with date range if available
    header_range = _format_header_date_range(range_start, range_end)
    used_urls = set()

    if header_range:
        output += f"# Cyber Threats and Risks ({header_range})\n\n<br><br>\n\n"
    else:
        output += f"# Cyber Threats and Risks\n\n"

    for _idx, result in enumerate(results[:MAX_RESULTS_TO_ANALYZE], start_count + 1):
        title = result.get("title", "Untitled Incident")
        snippet = result.get("content", "No description available")
        url = result.get("url", "Not specified")
        
        # Skip obvious non-article homepages
        try:
            parsed_for_skip = urlparse(url)
            if parsed_for_skip.path in ("", "/"):
                continue
        except Exception:
            pass

        # Try to fetch full page text to improve extraction quality and metadata
        content, raw_html = _fetch_page_content(url, snippet)

        # Use LLM to extract structured data and summarize the article.
        extraction_prompt = f'''You are a cybersecurity analyst extracting discrete incident details.
Return EXACTLY these lines:
Summary: <one sentence>
Date of Incident: <YYYY-MM-DD or natural date>
Targets: <entities>
Method: <one of [Ransomware, Phishing, Data breach, DDoS, Vulnerability exploitation, Supply chain compromise, Credential stuffing, Business email compromise, Vishing, Malware/Backdoor, Espionage]>
Exploit Used: <CVE IDs and/or exploit mechanism; leave blank if unknown>
Incident?: <yes/no> (yes only if a specific incident is described; no for op-eds, legislation, awareness months, and aggregator pages)

If you cannot determine a field from the article, leave that line blank after the colon.

Article: {content}
'''
        try:
            extracted_data = llm.invoke(extraction_prompt).content
            summary_match = re.search(r"^Summary:\s*(.*)$", extracted_data, re.MULTILINE)
            summary = summary_match.group(1).strip() if summary_match else content[:600] + "..."
            summary = _sanitize_summary(summary)

            date_match = re.search(r"^Date of Incident:\s*(.*)$", extracted_data, re.MULTILINE)
            date = _sanitize_date_field(date_match.group(1).strip() if date_match else "Not specified")
            
            targets_match = re.search(r"^Targets:\s*(.*)$", extracted_data, re.MULTILINE)
            targets = _sanitize_field(targets_match.group(1) if targets_match else "Not specified")
            
            method_match = re.search(r"^Method:\s*(.*)$", extracted_data, re.MULTILINE)
            raw_method = method_match.group(1) if method_match else "Not specified"
            method = _normalize_method(_sanitize_field(raw_method))

            exploit_match = re.search(r"^Exploit Used:\s*(.*)$", extracted_data, re.MULTILINE)
            exploit_used_llm = _sanitize_field(exploit_match.group(1) if exploit_match else "")

            incident_match = re.search(r"Incident\?:\s*(yes|no)", extracted_data, re.IGNORECASE)
            is_incident = bool(incident_match and incident_match.group(1).lower() == "yes")
        except Exception as e:
            logger.error(f"Error extracting data from LLM: {e}")
            summary = content[:600] + "..."
            date = "Not specified"
            targets = "Not specified"
            method = "Not specified"
            exploit_used_llm = ""
            is_incident = False

        # If incident but date not specified, try metadata date
        if is_incident and date == "Not specified":
            meta_date = _extract_metadata_date(raw_html)
            if meta_date:
                date = meta_date
        # If still not specified, try to extract a date from text
        if is_incident and date == "Not specified":
            text_date = _extract_date_from_text(content)
            if text_date:
                date = text_date
        # If still not specified, try to extract a date from the URL
        if is_incident and date == "Not specified":
            url_date = _extract_date_from_url(url)
            if url_date:
                date = url_date

        # Apply date range filtering if provided
        if is_incident and (range_start or range_end):
            ds, de = _normalize_date_for_filter(date)
            # If still missing, try metadata date directly for filter window
            if not ds and not de:
                meta_for_filter = _extract_metadata_date(raw_html)
                ds2, de2 = _normalize_date_for_filter(meta_for_filter) if meta_for_filter else (None, None)
                ds = ds2; de = de2
            # If still missing, try URL-based date for filter window
            if not ds and not de:
                url_for_filter = _extract_date_from_url(url)
                ds3, de3 = _normalize_date_for_filter(url_for_filter) if url_for_filter else (None, None)
                ds = ds3; de = de3
            if not _within_range(ds, de, range_start, range_end):
                continue

        # Heuristic classification: keep only specific, discrete incidents
        content_lc = f"{title} {content}".lower()
        # Hard excludes: annual/quarterly reports, NDB summaries, lists, webinars, landscape pieces
        if _is_hard_exclude(title, content):
            continue
        if any(nk in content_lc for nk in non_incident_keywords):
            # Do not salvage if it looks like a general analysis/marketing/landscape piece
            continue
        # LLM must say it's an incident
        if not is_incident:
            # Only salvage when there are strong indicators and sufficient specificity
            has_signal = any(kw in content_lc for kw in incident_keywords)
            has_date = (date and date.lower() != "not specified")
            has_specific_target = _is_specific_target(targets)
            has_method = (method and method.lower() != "not specified")
            if not (has_signal and (has_date or has_specific_target) and (has_method or has_specific_target)):
                continue
            is_incident = True
        # Enforce specificity even if LLM said yes
        if not _is_specific_target(targets) and not (date and date.lower() != "not specified"):
            continue
        # Additional guard on titles that scream lists/overviews
        title_lc = title.lower()
        if any(nk in title_lc for nk in ("top ", "landscape", "trends", "webinar", "overview", "battle", "threats in")):
            continue

        # Infer method from text if missing (for incidents)
        if is_incident and method == "Not specified":
            inferred = _infer_method_from_text(content)
            method = inferred
        # Method may be unknown; we will omit it from output

        # Infer targets from title if missing
        if targets == "Not specified":
            inferred_targets = _infer_targets_from_title(title)
            if inferred_targets:
                targets = inferred_targets
        # Targets may be generic or unknown; we will omit if unknown

        # Date may be unknown; we will omit if unknown

        # Sanitize final date value to avoid malformed lines
        date = _sanitize_date_field(date)

        # Improved relevance
        relevance = "Relevant to Australian businesses due to potential impact on similar industries or supply chains"
        tlc = title.lower()
        clc = content.lower()
        # Specific relevance for Microsoft PipeMagic zero-day (CVE-2025-29824)
        if (
            "pipemagic" in tlc or "pipemagic" in clc or
            "cve-2025-29824" in (raw_html or "") .lower() or "cve-2025-29824" in clc or
            "clfs" in clc
        ):
            relevance = (
                "Shows attackers rapidly weaponizing new Microsoft zero-days for ransomware. "
                "Highlights that Australian businesses must apply security updates immediately; "
                "any unpatched Windows servers could be hijacked via PipeMagic as soon as patches are released"
            )
        # Trigger direct Qantas impact only when in title or targets
        elif "qantas" in (tlc + " " + targets.lower()):
            relevance = "Directly impacts Qantas, a major Australian airline, affecting customer trust and compliance."
        elif "government" in clc:
            relevance = "Affects Australian government operations and public sector data security."
        elif "superannuation" in clc:
            relevance = "Impacts Australia’s superannuation industry, critical for financial security."
        elif "university" in clc:
            relevance = "Impacts Australian educational institutions, affecting data security and operations."
        elif "australian sectors" in content or "australia" in content:
            relevance = "Impacts Australian businesses across multiple sectors, increasing cybersecurity risks."
        
        # Note speculative data for 2025
        if "2025" in date:
            relevance += " Speculative based on current trends."
        
        included += 1
        # Build details per requested format (omit unknowns)
        details = []
        pretty = _pretty_date(date)
        if pretty and pretty.lower() != "not specified":
            details.append(f"- Date of Incident: {pretty}")
        if targets != "Not specified":
            details.append(f"- Targets: {targets}")
        if method != "Not specified":
            details.append(f"- Method: {method}")
        # Compute Exploit Used: combine LLM field with CVEs detected from page
        exploit_parts = []
        if exploit_used_llm and exploit_used_llm.lower() != "not specified":
            exploit_parts.append(exploit_used_llm)
        # Extract CVEs from the richer available text (raw_html preferred)
        raw_text_source = raw_html if raw_html else content
        cves = _extract_cves(raw_text_source)
        if cves:
            # Avoid duplicate CVEs already present in exploit_used_llm
            existing = " ".join(exploit_parts).upper()
            # Decorate known CVEs with friendly labels
            cve_labels = {
                "CVE-2025-29824": "(now-patched Windows 0-day)"
            }
            addl = []
            for c in cves:
                u = c.upper()
                if u in existing:
                    continue
                label = cve_labels.get(u, "")
                addl.append(f"{u} {label}".strip())
            if addl:
                exploit_parts.append(", ".join(addl))
        if exploit_parts:
            details.append(f"- Exploit Used: {'; '.join(exploit_parts)}")
        # Add relevance and source
        if relevance:
            details.append(f"- Relevance: {relevance}")
        if url and url != "Not specified":
            # Use title as anchor text for better readability
            details.append(f"- Source: [{title}]({url})")

        # Track used URL (canonical form) to avoid duplicates and to support backfill
        try:
            pu = urlparse(url)
            canon_url = f"{pu.scheme}://{pu.netloc}{pu.path}".rstrip("/")
        except Exception:
            canon_url = (url or "").strip()
        used_urls.add(canon_url.lower())

        # Append section using new style
        output += f"## {included}. {title}\n\n**{summary}**\n\n{os.linesep.join(details)}\n\n<br><br>\n\n"
    # Backfill in relaxed mode to reach minimum target when strict filtering yields too few items
    if included < MIN_RESULTS_ENFORCED:
        needed = MIN_RESULTS_ENFORCED - included
        added = 0
        for result in results:
            if added >= needed:
                break
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            # Skip duplicates and homepages
            try:
                pu = urlparse(url)
                canon_url = f"{pu.scheme}://{pu.netloc}{pu.path}".rstrip("/")
            except Exception:
                canon_url = (url or "").strip()
            if not canon_url or canon_url.lower() in used_urls:
                continue
            if 'pu' in locals() and getattr(pu, 'path', None) in ("", "/"):
                continue
            # Fetch content (fallback to snippet)
            snippet = result.get("content", "")
            content, raw_html = _fetch_page_content(url, snippet)
            # Try to infer a date from metadata/url for range filtering
            bf_date = _extract_metadata_date(raw_html) or _extract_date_from_url(url) or "Not specified"
            if range_start or range_end:
                ds, de = _normalize_date_for_filter(bf_date)
                if ds and de and not _within_range(ds, de, range_start, range_end):
                    # If we have a date and it's clearly outside, skip
                    continue
            # Build fields with heuristics
            summary = _sanitize_summary(content[:600] + ("..." if len(content) > 600 else ""))
            date_str = _sanitize_date_field(bf_date)
            pretty = _pretty_date(date_str)
            targets = _infer_targets_from_title(title) or "Not specified"
            method = _infer_method_from_text(content)
            # Exploits/CVEs
            exploit_parts = []
            cves = _extract_cves(raw_html if raw_html else content)
            if cves:
                cve_labels = {
                    "CVE-2025-29824": "(now-patched Windows 0-day)"
                }
                expl_list = []
                for c in cves:
                    label = cve_labels.get(c.upper(), "")
                    expl_list.append(f"{c.upper()} {label}".strip())
                if expl_list:
                    exploit_parts.append(", ".join(expl_list))
            # Relevance
            tlc = title.lower(); clc = content.lower()
            relevance = "Relevant to Australian businesses due to potential impact on similar industries or supply chains"
            if ("pipemagic" in tlc or "pipemagic" in clc or "cve-2025-29824" in clc or "clfs" in clc):
                relevance = (
                    "Shows attackers rapidly weaponizing new Microsoft zero-days for ransomware. "
                    "Highlights that Australian businesses must apply security updates immediately; "
                    "any unpatched Windows servers could be hijacked via PipeMagic as soon as patches are released"
                )
            elif "government" in clc:
                relevance = "Affects Australian government operations and public sector data security."
            elif "university" in clc:
                relevance = "Impacts Australian educational institutions, affecting data security and operations."

            # Assemble details, omitting unknowns
            details = []
            if pretty and pretty.lower() != "not specified":
                details.append(f"- Date of Incident: {pretty}")
            if targets and targets != "Not specified":
                details.append(f"- Targets: {targets}")
            if method and method != "Not specified":
                details.append(f"- Method: {method}")
            if exploit_parts:
                details.append(f"- Exploit Used: {'; '.join(exploit_parts)}")
            if relevance:
                details.append(f"- Relevance: {relevance}")
            if url:
                details.append(f"- Source: [{title}]({url})")

            included += 1
            added += 1
            used_urls.add(canon_url.lower())
            output += f"## {included}. {title}\n\n**{summary}**\n\n{os.linesep.join(details)}\n\n<br><br>\n\n"

    if enforce_min and included < MIN_RESULTS_ENFORCED:
        output += f"\nOnly [{included}] relevant cybersecurity incidents found for the requested timeframe (target: {MIN_RESULTS_ENFORCED})."
    return output

# Main function for testing
if __name__ == "__main__":
    import asyncio
    async def main():
        # Example query
        query = "Cybersecurity incidents in Australia from January 2025 to March 2025"
        output, generation_time = await perform_search(query)
        print(output)
        print(f"Generation time: {generation_time:.2f} seconds")
    asyncio.run(main())

def format_investigation_results(query, results, llm):
    # Extract content and URLs from results
    formatted_results = ""
    for result in results:
        formatted_results += f"URL: {result.get('url', 'N/A')}\nContent: {result.get('content', 'N/A')}\n\n"

    prompt = f"""
    As a senior cybersecurity analyst, your task is to produce a detailed and well-structured threat intelligence report based on the provided web search results. The report should be written in Markdown format and follow the structure below.

    **Objective:** Synthesize the provided data into a comprehensive report on the cybersecurity incident: "{query}".

    **Report Structure:**

    1.  **Heading:**
        - Create a clear, concise heading for the report (e.g., `# {query} Research`).

    2.  **Incident Overview:**
        - **Who & When:**
            - **Date of breach:** Specify the date the breach occurred.
            - **Discovery:** State when the breach was discovered.
            - **Notification:** Detail when the public or relevant authorities were notified.
            - **Customer notifications planned:** Mention any planned dates for notifying customers.
        - **Exposed Data & Scope:**
            - Describe the platform or system that was breached (e.g., third-party CRM, internal network).
            - Explain the method used by the threat actor (e.g., social engineering, malware).
            - List the types of data compromised (e.g., PII, financial credentials).
        - **Organisation Context:**
            - Provide background on the affected organization, including its size and industry.
            - Clarify the scope of the breach (e.g., U.S. operations only).
        - **Response & Remediation:**
            - Detail the immediate actions taken by the organization.
            - Describe the customer protection measures being offered.
            - Mention the ongoing status of the investigation and any attribution to threat groups.

    3.  **Timeline Summary:**
        - Create a Markdown table with two columns: "Date" and "Event".
        - Populate the table with key dates and corresponding events from the incident.

    4.  **MITRE ATT&CK Mapping:**
        - Identify relevant MITRE ATT&CK techniques based on the incident details.
        - **Attack Flow Summary:** Describe the likely attack sequence in a few steps.
        - **Detailed Table:** Create a Markdown table with columns: "MITRE Phase", "Technique/Sub-technique", and "Description & Relevance".
        - **Security Implications:** Analyze the security implications of the attack.
        - **Recommendations:** Provide a table with columns: "Control Area" and "Actions", suggesting measures to prevent similar incidents.

    5.  **References:**
        - List all the source URLs provided in the search results.

    **Input Data:**

    {formatted_results}

    ---
    **Instructions:**
    - Ensure all sections are completed thoroughly and accurately based on the provided data.
    - If specific information is not available from the sources, omit that field rather than writing placeholders.
    - Maintain a professional and analytical tone throughout the report.
    - The final output must be a single, well-formatted Markdown document.
    """

    # Invoke the LLM with the detailed prompt
    response = llm.invoke(prompt)
    return response.content

async def investigate(query: str, server_name: str = None, model_name: str = "granite3.3", server_type: str = "ollama"):
    try:
        # Start timer for the entire research process
        overall_start_time = time.time()

        selected_server = None
        server_url_or_key = None

        if server_type == "ollama":
            if server_name:
                selected_server = await database.get_ollama_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_ollama_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Ollama servers configured.")
            server_url_or_key = selected_server['url']
            llm = ChatOllama(
                model=model_name,
                temperature=0,
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url=server_url_or_key.replace("/api/generate", "/")
            )
            # Test connection to the selected Ollama server using async HTTP client
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{server_url_or_key.replace('/api/generate', '')}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(f"Failed to connect to Ollama server at {server_url_or_key}")
        elif server_type == "gemini":
            if server_name:
                selected_server = await database.get_external_ai_server_by_name(server_name)
            if not selected_server:
                all_servers = await database.get_external_ai_servers()
                if all_servers:
                    selected_server = all_servers[0]
                else:
                    raise ValueError("No Gemini servers configured.")
            server_url_or_key = selected_server['api_key']
            llm = ChatGoogleGenerativeAI(
                model=f"models/gemini-2.5-flash",
                temperature=0,
                google_api_key=server_url_or_key
            )
        else:
            raise ValueError(f"Unsupported server type: {server_type}")

        # Get raw results: SERPAPI primary, Tavily fallback (unrestricted)
        import asyncio
        raw_results = {"results": []}
        try:
            if serpapi_api_key:
                extra = {"tbm": "nws"}
                raw_results = await asyncio.get_event_loop().run_in_executor(None, _search_serpapi, query, 100, "au", "en", extra)
                logger.info("Raw SERPAPI results retrieved")
        except Exception as e:
            logger.warning(f"SERPAPI search failed for investigate, trying Tavily fallback: {e}")
        if (not raw_results.get("results")) and tavily_api_key:
            try:
                tavily_tool_unrestricted = TavilySearch(
                    max_results=15,
                    topic="general",
                    search_depth="advanced",
                )
                raw_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool_unrestricted.invoke, query)
                logger.info("Raw Tavily results retrieved (fallback)")
            except Exception as e:
                logger.error(f"Tavily fallback failed for investigate: {e}")

        # Generate the detailed investigation report
        # Run the formatting in a thread pool to avoid blocking
        output = await asyncio.get_event_loop().run_in_executor(None, format_investigation_results, query, raw_results.get("results", []), llm)

        if not output.strip():
            logger.warning("No relevant results found")
            return "No information found for the requested query.", None

        overall_end_time = time.time()
        generation_time = overall_end_time - overall_start_time

        await database.add_research(query, output, generation_time, selected_server['name'], model_name)
        return output, generation_time
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        # Check for model-specific errors
        if "is not supported" in str(e) or "Invalid model" in str(e):
            error_message = f"The selected model '{model_name}' is not suitable for this research task. Please try a different model, such as 'granite3.3'."
            return error_message, None
        return f"Error processing query: {str(e)}", None
