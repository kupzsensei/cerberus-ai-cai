import asyncio
import logging
import httpx
import re
import hashlib
from urllib.parse import urlparse
from datetime import datetime
import database
import research
import utils

logger = logging.getLogger(__name__)

# In-memory log streams for SSE
JOB_STREAMS: dict[int, asyncio.Queue] = {}

def _canon_url(url: str) -> str:
    try:
        pu = urlparse(url)
        return f"{pu.scheme}://{pu.netloc}{pu.path}".rstrip("/")
    except Exception:
        return (url or "").strip()

def _title_key(title: str) -> str:
    return re.sub(r"\W+", "", (title or "").lower())[:100]

def _content_hash(text: str) -> str:
    return hashlib.sha1((text or "").encode('utf-8')).hexdigest()

async def _push_log(job_id: int, level: str, message: str):
    ts = datetime.utcnow().isoformat()
    await database.add_research_log(job_id, level, message)
    q = JOB_STREAMS.get(job_id)
    if q:
        try:
            await q.put({"ts": ts, "level": level, "message": message})
        except Exception:
            pass

async def _http_get_text(url: str) -> tuple[str, str | None]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return "", None
            html = resp.text
            # Basic sanitize
            clean = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
            clean = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", clean)
            clean = re.sub(r"(?is)<nav[^>]*>.*?</nav>", " ", clean)
            clean = re.sub(r"(?is)<header[^>]*>.*?</header>", " ", clean)
            clean = re.sub(r"(?is)<footer[^>]*>.*?</footer>", " ", clean)
            text = re.sub(r"(?is)<[^>]+>", " ", clean)
            text = re.sub(r"\s+", " ", text).strip()
            return text, html
    except Exception:
        return "", None

def _extract_cves(text: str) -> list[str]:
    if not text:
        return []
    try:
        m = re.findall(r"\bCVE-\d{4}-\d{4,7}\b", text, flags=re.IGNORECASE)
        out, seen = [], set()
        for c in m:
            u = c.upper()
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out
    except Exception:
        return []

async def _extract_fields_with_llm(llm, content: str) -> dict:
    prompt = f'''You are a cybersecurity analyst extracting discrete incident details.
Return EXACTLY these lines:
Summary: <one sentence>
Date of Incident: <YYYY-MM-DD or natural date>
Targets: <entities>
Method: <one of [Ransomware, Phishing, Data breach, DDoS, Vulnerability exploitation, Supply chain compromise, Credential stuffing, Business email compromise, Vishing, Malware/Backdoor, Espionage]>
Exploit Used: <CVE IDs and/or exploit mechanism; leave blank if unknown>
Incident?: <yes/no>

Article: {content}'''
    try:
        data = (await asyncio.get_event_loop().run_in_executor(None, llm.invoke, prompt)).content
        def grab(label):
            m = re.search(rf"^{label}:\s*(.*)$", data, re.MULTILINE)
            return m.group(1).strip() if m else ""
        return {
            "summary": grab("Summary"),
            "date": grab("Date of Incident"),
            "targets": grab("Targets"),
            "method": grab("Method"),
            "exploit_used": grab("Exploit Used"),
            "incident": (grab("Incident?").lower().startswith("y"))
        }
    except Exception:
        return {"summary": content[:600] + ("..." if len(content) > 600 else ""), "date": "", "targets": "", "method": "", "exploit_used": "", "incident": False}

def _pretty_date(date_str: str) -> str:
    if not date_str:
        return ""
    s = date_str.strip()
    try:
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
            return f"{months[mo-1]} {d}, {y}"
    except Exception:
        pass
    return s

def _build_markdown_snippet(idx: int, title: str, summary: str, date: str, targets: str, method: str, exploit_used: str, relevance: str, source_url: str) -> str:
    lines = []
    lines.append(f"## {idx}. {title}\n")
    lines.append(f"**{summary}**\n")
    if date:
        lines.append(f"- Date of Incident: {date}\n")
    if targets:
        lines.append(f"- Targets: {targets}\n")
    if method:
        lines.append(f"- Method: {method}\n")
    if exploit_used:
        lines.append(f"- Exploit Used: {exploit_used}\n")
    if relevance:
        lines.append(f"- Relevance: {relevance}\n")
    if source_url:
        lines.append(f"- Source: {source_url}\n")
    lines.append("\n<br><br>\n\n")
    return "\n".join(lines)

async def run_research_job(job_id: int, seed_urls: list[str] | None = None, focus_on_seed: bool = True):
    job = await database.get_research_job(job_id)
    if not job:
        return
    # Running with accepted_count=0
    await database.update_research_job(job_id, status='running', started_at=datetime.utcnow(), accepted_count=0)
    await _push_log(job_id, 'info', f"Job {job_id} started: result_count={job['target_count']}")

    # Build LLM
    server_type = job.get('server_type'); server_name = job.get('server_name'); model_name = job.get('model_name')
    llm = None
    try:
        if server_type == 'ollama':
            server = await database.get_ollama_server_by_name(server_name)
            from langchain_ollama import ChatOllama
            llm = ChatOllama(model=model_name, temperature=0, base_url=server['url'].replace('/api/generate', '/'))
        elif server_type == 'gemini':
            server = await database.get_external_ai_server_by_name(server_name)
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model='models/gemini-2.5-flash', temperature=0, google_api_key=server['api_key'])
    except Exception as e:
        await _push_log(job_id, 'error', f"Failed to initialize LLM: {e}")
        await database.update_research_job(job_id, status='failed', finished_at=datetime.utcnow())
        return

    # Parameters
    target = int(job['target_count'] or 10)
    page_size = 30
    max_candidates = max(100, target * 5)
    seen: set[str] = set()
    total_seen = 0

    # Helpers
    async def fetch_page(page_index: int) -> list[dict]:
        results = []
        extra = {"tbm": "nws"}
        s, e = research._parse_date_range_from_query(job['query'])
        if s and e:
            extra["tbs"] = f"cdr:1,cd_min:{s},cd_max:{e}"
        # Focus query on cyber attacks / exploits / breaches
        base_q = job['query']
        focus_tail = ' (ransomware OR "data breach" OR breach OR cyberattack OR exploit OR vulnerability OR malware OR "zero-day" OR CVE)'
        fq = base_q + focus_tail
        # SerpAPI one page (30)
        try:
            serp_extra = dict(extra); serp_extra['start'] = page_index * page_size
            sr = await asyncio.get_event_loop().run_in_executor(None, research._search_serpapi, fq, page_size, 'au', 'en', serp_extra)
            results.extend(sr.get('results', []))
        except Exception:
            await _push_log(job_id, 'warning', f"SERPAPI page {page_index} failed")
        # Tavily fallback page (30)
        try:
            tr = await asyncio.get_event_loop().run_in_executor(None, research._search_tavily, fq, page_size, research.include_domains)
            results.extend(tr.get('results', []))
        except Exception:
            pass
        return results

    async def process_candidate(url: str, title_hint: str = '') -> bool:
        nonlocal total_seen
        if total_seen >= max_candidates:
            return False
        cu = _canon_url(url)
        if not cu or cu.lower() in seen:
            return False
        seen.add(cu.lower()); total_seen += 1
        cur = await database.get_research_job(job_id)
        if not cur or cur.get('status') in ('canceled','failed','finalized','finalizing'):
            return False
        if int(cur.get('accepted_count') or 0) >= target:
            return False
        await _push_log(job_id, 'info', f"Fetching: {url}")
        text, html = await _http_get_text(url)
        if not text:
            await _push_log(job_id, 'warning', f"Failed to fetch: {url}")
            await database.increment_research_job_counts(job_id, errors_delta=1)
            return False
        fields = await _extract_fields_with_llm(llm, text)
        title = title_hint or 'Untitled Incident'
        summary = fields.get('summary', '').strip()
        date = _pretty_date(fields.get('date', '').strip())
        targets = (fields.get('targets') or '').strip()
        method = (fields.get('method') or '').strip()
        exploit_used = (fields.get('exploit_used') or '').strip()
        cves = _extract_cves(html or text)
        if cves:
            existing = exploit_used.upper()
            extra_c = [c for c in cves if c not in existing]
            if extra_c:
                lbl = {"CVE-2025-29824": "(now-patched Windows 0-day)"}
                extra_c = [f"{c} {lbl.get(c, '')}".strip() for c in extra_c]
                exploit_used = ", ".join(filter(None, [exploit_used] + extra_c)).strip(', ')
        # Relevance
        tl = f"{title} {text}".lower(); rel = ""
        if any(k in tl for k in ["australia", ".au", "australian"]):
            rel = "Relevant to Australian organizations and sectors."
        elif any(k in tl for k in ["windows","apple","ios","macos","azure","aws","google cloud","vmware","esxi"]):
            rel = "Global incident impacting widely used platforms; likely to affect Australian businesses."
        # Incident keyword presence (filter to attacks/exploits/breaches)
        content_lc = f"{title} {text}".lower()
        incident_kw = ("ransomware","data breach","breach","cyberattack","attack","exploit","vulnerability","malware","ddos","zero-day","cve-")
        if not any(k in content_lc for k in incident_kw):
            await _push_log(job_id, 'info', f"filtered_non_incident: {url}")
            return False

        # Duplicate check within job
        dupe = False
        try:
            existing = await database.list_research_drafts(job_id, limit=10000, offset=0)
            if any((d.get('source_url')==url) or (d.get('title')==(title)) for d in existing):
                dupe = True
        except Exception:
            dupe = False
        qa_ok = (not dupe) and bool(summary) and bool(url)
        acc = int((await database.get_research_job(job_id)).get('accepted_count') or 0)
        idx = acc + 1
        snippet = _build_markdown_snippet(idx, title, summary, date, targets, method, exploit_used, rel, url)
        draft_id = await database.add_research_draft(job_id, {
            'title': title,
            'summary': summary,
            'date': date,
            'targets': targets,
            'method': method,
            'exploit_used': exploit_used,
            'relevance': rel,
            'source_url': url,
            'canonical_url': cu,
            'title_key': _title_key(title),
            'content_hash': _content_hash(text[:5000]),
            'markdown_snippet': snippet,
            'qa_status': 'ok' if qa_ok else 'failed',
            'qa_message': '' if qa_ok else 'duplicate or insufficient content',
            'link_ok': 1,
            'is_duplicate': 1 if dupe else 0,
        })
        await database.increment_research_job_counts(job_id, drafts_delta=1)
        await _push_log(job_id, 'info', f"Draft saved: id={draft_id}")
        if qa_ok:
            new_acc = acc + 1
            await database.update_research_job(job_id, accepted_count=new_acc)
            await _push_log(job_id, 'info', f"accepted_count: {new_acc}/{target}")
            return True
        else:
            await _push_log(job_id, 'info', f"qa_failed: id={draft_id}")
            return False

    # Seed round
    if seed_urls:
        await _push_log(job_id, 'info', f"search_round: seed ({len(seed_urls)} urls)")
        for u in seed_urls:
            cur = await database.get_research_job(job_id)
            if int(cur.get('accepted_count') or 0) >= target:
                break
            await process_candidate(u, title_hint=u)

    # Paginated search rounds (30 per page)
    page_index = 0
    while True:
        cur = await database.get_research_job(job_id)
        if not cur or cur.get('status') in ('canceled','failed','finalized','finalizing'):
            break
        if int(cur.get('accepted_count') or 0) >= target:
            break
        if total_seen >= max_candidates:
            await _push_log(job_id, 'warning', f"Max candidate budget reached: {total_seen}")
            break
        await _push_log(job_id, 'info', f"search_round: page {page_index}")
        page = await fetch_page(page_index)
        await _push_log(job_id, 'info', f"candidates_found: {len(page)}")
        if not page:
            break
        for it in page:
            url = it.get('url') or ''
            title = it.get('title') or 'Untitled Incident'
            cur = await database.get_research_job(job_id)
            if int(cur.get('accepted_count') or 0) >= target:
                break
            await process_candidate(url, title)
        page_index += 1

    # Auto-finalize
    await _push_log(job_id, 'info', "Finalizing report…")
    await database.update_research_job(job_id, status='finalizing')
    drafts = await database.list_research_drafts_full(job_id)
    # Build header range
    header_range = None
    try:
        rs, re_ = research._parse_date_range_from_query(job.get('query') or '')
        if rs and re_:
            from datetime import datetime as _dt
            sdt = _dt.strptime(rs, "%Y-%m-%d"); edt = _dt.strptime(re_, "%Y-%m-%d")
            months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            header_range = f"{months[sdt.month-1]} {sdt.day} - {months[edt.month-1]} {edt.day}, {edt.year}" if sdt.year==edt.year else f"{months[sdt.month-1]} {sdt.day}, {sdt.year} - {months[edt.month-1]} {edt.day}, {edt.year}"
    except Exception:
        header_range = None
    md_parts = []
    md_parts.append(f"# Cyber Threats and Risks ({header_range})\n\n<br><br>\n\n" if header_range else "# Cyber Threats and Risks\n\n<br><br>\n\n")
    ok = [d for d in drafts if d.get('qa_status')=='ok']
    for i, d in enumerate(ok, start=1):
        sn = d.get('markdown_snippet') or ''
        sn = re.sub(r"^##\s*\d+\.", f"## {i}.", sn, flags=re.MULTILINE)
        md_parts.append(sn)
    final_text = "".join(md_parts)
    try:
        rid = await database.add_research(job.get('query') or '', final_text, 0.0, job.get('server_name') or '', job.get('model_name') or '')
        await database.update_research_job(job_id, status='finalized', research_id=rid, finished_at=datetime.utcnow())
        cur = await database.get_research_job(job_id)
        await _push_log(job_id, 'info', f"finalized: research_id={rid}, accepted={int(cur.get('accepted_count') or 0)}/{target}")
    except Exception as e:
        await database.update_research_job(job_id, status='failed')
        await _push_log(job_id, 'error', f"Finalize failed: {e}")
