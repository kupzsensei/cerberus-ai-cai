import os
import logging
import httpx
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
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

# Validate environment variables
tavily_api_key = os.environ.get("TAVILY_API_KEY")
openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY is not set in the .env file")
if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY is not set in the .env file")

# Corrected domain list
include_domains = [
    "cyberdaily.au",
    "sbs.com.au",
    "infosecurity-magazine.com",
    "crowdstrike.com",
    "blackpointcyber.com",
    "thehackernews.com",
    "darkreading.com",
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

# Create search tool
tavily_tool = TavilySearch(
    max_results=50,
    topic="general",
    search_depth="advanced",
    include_domains=include_domains
)

# Function to perform a search
async def perform_search(query, server_name: str = None, model_name: str = "granite3.3", server_type: str = "ollama"):
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
        
        # Get raw Tavily results
        # Since TavilySearch doesn't have an async version, we'll run it in a thread pool
        import asyncio
        raw_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool.invoke, query)
        logger.info(f"Raw Tavily results retrieved")
        
        # Filter results to ensure domain compliance and relevance
        filtered_results = [
            r for r in raw_results.get("results", [])
            if any(domain in r["url"] for domain in include_domains)
            and any(term in r["content"].lower() for term in [
                "australia", "australian", "qantas", "government", "superannuation",
                "business", "sector", "ransomware", "phishing", "ddos", "keylogger",
                "exploit", "vulnerability", "data breach", "cyberattack"
            ])
        ]
        for r in raw_results.get("results", []):
            if any(domain in r["url"] for domain in include_domains) and not any(term in r["content"].lower() for term in [
                "australia", "australian", "qantas", "government", "superannuation",
                "business", "sector", "ransomware", "phishing", "ddos", "keylogger",
                "exploit", "vulnerability", "data breach", "cyberattack"
            ]):
                logger.info(f"Excluded result: {r['url']} - No relevant keywords found")
        logger.info(f"Filtered results count: {len(filtered_results)}")

        # If too few candidates, do a second Tavily pass (unrestricted) to reach >=10 incidents
        if len(filtered_results) < 30:
            tavily_tool_unrestricted = TavilySearch(
                max_results=50,
                topic="general",
                search_depth="advanced",
            )
            range_clause = f" from {range_start} to {range_end}" if range_start and range_end else ""
            enriched_query = f"{query} (ransomware OR \"data breach\" OR cyberattack OR hack){range_clause} site:.au"
            more_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool_unrestricted.invoke, enriched_query)
            logger.info("Second Tavily pass fetched")
            # Filter for relevance; allow any domain but keep Australia/cyber keywords
            extra = [
                r for r in more_results.get("results", [])
                if any(term in r["content"].lower() for term in [
                    "australia", "australian", "ransomware", "phishing", "ddos",
                    "exploit", "vulnerability", "data breach", "cyberattack", "breach", "leak"
                ])
            ]
            # Deduplicate by URL
            seen = {r["url"] for r in filtered_results}
            for r in extra:
                if r["url"] not in seen:
                    filtered_results.append(r)
                    seen.add(r["url"])
        
        # Generate output from raw results and filter by date range, if provided
        # Run the formatting in a thread pool to avoid blocking
        output = await asyncio.get_event_loop().run_in_executor(None, format_raw_results, filtered_results, 0, llm, range_start, range_end)
        
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
def format_raw_results(results, start_count, llm, range_start=None, range_end=None):
    output = ""
    included = 0

    incident_keywords = (
        "breach", "attack", "ransomware", "extortion", "data leak", "leaked",
        "hacked", "cyberattack", "intrusion", "compromise", "outage"
    )
    non_incident_keywords = (
        "op-ed", "op ed", "opinion", "analysis", "predictions", "awareness month",
        "legislation", "act passed", "bill", "law", "aggregator", "roundup",
        "rules", "policy", "regulation", "regulatory", "report", "trends",
        "awareness", "election", "strategy", "framework", "act", "legislation"
    )

    def _normalize_method(m: str) -> str:
        if not m or m.strip().lower() == "not specified":
            return "Not specified"
        t = m.lower()
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
        return m.strip()

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
            if len(text) > 12000:
                text = text[:12000]
            # Prefer fetched content if it seems longer than the snippet
            if len(text) > max(len(fallback), 1000):
                return text, resp.text
            return fallback, resp.text
        except Exception as e:
            logger.info(f"Full page fetch failed for {page_url}: {e}")
            return fallback, None

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
        except Exception:
            pass
        return None

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

    for _idx, result in enumerate(results[:50], start_count + 1):
        title = result.get("title", "Untitled Incident")
        snippet = result.get("content", "No description available")
        url = result.get("url", "Not specified")
        
        # Try to fetch full page text to improve extraction quality and metadata
        content, raw_html = _fetch_page_content(url, snippet)

        # Use LLM to extract structured data and summarize the article.
        extraction_prompt = f'''You are a cybersecurity analyst extracting discrete incident details.
Return EXACTLY these lines:
Summary: <one sentence>
Date of Incident: <YYYY-MM-DD or natural date or Not specified>
Targets: <entities or Not specified>
Method: <one of [Ransomware, Phishing, Data breach, DDoS, Vulnerability exploitation, Supply chain compromise, Credential stuffing, Business email compromise, Vishing, Malware/Backdoor, Espionage] or Not specified>
Incident?: <yes/no> (yes only if a specific incident is described; no for op-eds, legislation, awareness months, and aggregator pages)

Article: {content}
'''
        try:
            extracted_data = llm.invoke(extraction_prompt).content
            summary_match = re.search(r"Summary: (.*)", extracted_data, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else content[:600] + "..."

            date_match = re.search(r"Date of Incident: (.*)", extracted_data)
            date = date_match.group(1).strip() if date_match else "Not specified"
            
            targets_match = re.search(r"Targets: (.*)", extracted_data)
            targets = targets_match.group(1).strip() if targets_match else "Not specified"
            
            method_match = re.search(r"Method: (.*)", extracted_data)
            method = _normalize_method(method_match.group(1).strip()) if method_match else "Not specified"

            incident_match = re.search(r"Incident\?:\s*(yes|no)", extracted_data, re.IGNORECASE)
            is_incident = bool(incident_match and incident_match.group(1).lower() == "yes")
        except Exception as e:
            logger.error(f"Error extracting data from LLM: {e}")
            summary = content[:600] + "..."
            date = "Not specified"
            targets = "Not specified"
            method = "Not specified"
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

        # Heuristic fallback classification to skip non-incident pages
        content_lc = f"{title} {content}".lower()
        if any(nk in content_lc for nk in non_incident_keywords):
            is_incident = False
        if not is_incident:
            has_any_signal = any(kw in content_lc for kw in incident_keywords)
            has_any_field = any(v != "Not specified" for v in (date, targets, method))
            if has_any_signal and has_any_field:
                is_incident = True

        # Title-based non-incident hint (keeps the item, marks as non-incident)
        title_lc = title.lower()
        if any(nk in title_lc for nk in non_incident_keywords):
            is_incident = False

        # Infer method from text if missing (for incidents)
        if is_incident and method == "Not specified":
            inferred = _infer_method_from_text(content)
            method = inferred

        # For non-incident entries, fill Date with posted time if missing
        if (not is_incident) and date == "Not specified":
            posted = _extract_metadata_date(raw_html) or _extract_date_from_url(url)
            if posted:
                date = posted

        # Drop only if absolutely no structured info present
        if (date == "Not specified" and targets == "Not specified" and method == "Not specified"):
            continue

        # Improved relevance
        relevance = "Relevant to Australian businesses due to potential impact on similar industries or supply chains"
        # Trigger direct Qantas impact only when in title or targets
        if "qantas" in (title.lower() + " " + targets.lower()):
            relevance = "Directly impacts Qantas, a major Australian airline, affecting customer trust and compliance."
        elif "government" in content.lower():
            relevance = "Affects Australian government operations and public sector data security."
        elif "superannuation" in content.lower():
            relevance = "Impacts Australia’s superannuation industry, critical for financial security."
        elif "university" in content.lower():
            relevance = "Impacts Australian educational institutions, affecting data security and operations."
        elif "Australian sectors" in content or "Australia" in content:
            relevance = "Impacts Australian businesses across multiple sectors, increasing cybersecurity risks."
        
        # Note speculative data for 2025
        if "2025" in date:
            relevance += " Speculative based on current trends."
        
        included += 1
        output += f'''
# [{included}]. {title}

{summary}

- **Date of Incident**: {date}
- **Targets**: {targets}
- **Method**: {method}
- **Relevance to Australian Business**: {relevance}
- **Source**: {url}



---


'''
    if included < 10:
        output += f"\nOnly [{included}] relevant cybersecurity incidents found for the requested timeframe."
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
    - If specific information is not available in the results, state "Not specified" or "N/A".
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

        # Get raw Tavily results
        # Since TavilySearch doesn't have an async version, we'll run it in a thread pool
        import asyncio
        tavily_tool_unrestricted = TavilySearch(
            max_results=15,
            topic="general",
            search_depth="advanced",
        )
        raw_results = await asyncio.get_event_loop().run_in_executor(None, tavily_tool_unrestricted.invoke, query)
        logger.info(f"Raw Tavily results retrieved")

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
