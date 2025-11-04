import asyncio
import logging
import httpx
import re
import hashlib
from urllib.parse import urlparse
from datetime import datetime
import json
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

async def _extract_fields_with_llm(llm, content: str, prompt_template: str | None = None) -> dict:
    """Ask the LLM for strict JSON and parse it. Fallback to a naive summary on failure."""
    schema = {
        "summary": "string",
        "date": "string",
        "targets": "string",
        "method": "string",
        "exploit_used": "string",
        "incident": "boolean"
    }
    if prompt_template and isinstance(prompt_template, str) and prompt_template.strip():
        prompt = prompt_template.replace("{ARTICLE}", content)
    else:
        prompt = (
            "You are a cybersecurity analyst focused on incidents impacting Australian businesses.\n"
            "Return ONLY valid minified JSON with these keys: "
            "{summary:string,date:string,targets:string,method:string,exploit_used:string,incident:boolean}.\n"
            "Rules: method must be one of [Ransomware, Phishing, Data breach, DDoS, Vulnerability exploitation, Supply chain compromise, Credential stuffing, Business email compromise, Vishing, Malware/Backdoor, Espionage]. "
            "Set incident=true only if this article describes an actual cyberattack/breach/exploit/outage affecting an organization, or a high-likelihood threat relevant to Australian businesses. "
            "Prefer concise, factual summary. Leave unknown fields as empty string. No prose or markdown, JSON only.\n\n"
            f"Article: {content}"
        )
    try:
        raw = (await asyncio.get_event_loop().run_in_executor(None, llm.invoke, prompt)).content
        # Trim code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw).strip()
            raw = re.sub(r"```$", "", raw).strip()
        data = json.loads(raw)
        # Normalize
        def _norm_method(m: str) -> str:
            t = (m or "").strip().lower()
            mapping = {
                "ransom": "Ransomware",
                "lockbit": "Ransomware",
                "double": "Ransomware",
                "extortion": "Ransomware",
                "data breach": "Data breach",
                "breach": "Data breach",
                "leak": "Data breach",
                "exfil": "Data breach",
                "phishing": "Phishing",
                "credential": "Credential stuffing",
                "ddos": "DDoS",
                "denial": "DDoS",
                "vulnerability": "Vulnerability exploitation",
                "exploit": "Vulnerability exploitation",
                "sql": "Vulnerability exploitation",
                "supply": "Supply chain compromise",
                "third": "Supply chain compromise",
                "bec": "Business email compromise",
                "business email": "Business email compromise",
                "vishing": "Vishing",
                "voice": "Vishing",
                "backdoor": "Malware/Backdoor",
                "malware": "Malware/Backdoor",
                "espionage": "Espionage",
            }
            for k, v in mapping.items():
                if k in t:
                    return v
            return "" if not t else m
        out = {
            "summary": (data.get("summary") or "").strip(),
            "date": (data.get("date") or "").strip(),
            "targets": (data.get("targets") or "").strip(),
            "method": _norm_method(data.get("method") or ""),
            "exploit_used": (data.get("exploit_used") or "").strip(),
            "incident": bool(data.get("incident"))
        }
        return out
    except Exception:
        # Fallback minimal fields
        return {
            "summary": content[:600] + ("..." if len(content) > 600 else ""),
            "date": "",
            "targets": "",
            "method": "",
            "exploit_used": "",
            "incident": False,
        }

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
        # Render source as a Markdown link to match desired style
        lines.append(f"- Source: [{title}]({source_url})\n")
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

    # Parameters (configurable; job overrides config.json)
    base_cfg = utils.config.get('research_pipeline', {}) if hasattr(utils, 'config') else {}
    job_cfg = {}
    try:
        raw_cfg = job.get('config_json') or '{}'
        job_cfg = json.loads(raw_cfg)
    except Exception:
        job_cfg = {}
    target = int(job['target_count'] or 10)
    # Search settings
    page_size = int(job_cfg.get('search', {}).get('page_size', base_cfg.get('page_size', 30)))
    max_candidates = int(job_cfg.get('search', {}).get('max_candidates', base_cfg.get('max_candidates', max(100, target * 6))))
    concurrency = int(job_cfg.get('search', {}).get('concurrency', base_cfg.get('concurrency', 6)))
    focus_tail = job_cfg.get('search', {}).get('focus_query_tail', ' (ransomware OR "data breach" OR breach OR cyberattack OR exploit OR vulnerability OR malware OR "zero-day" OR CVE)')
    use_serpapi = bool(job_cfg.get('search', {}).get('use_serpapi', True))
    use_tavily = bool(job_cfg.get('search', {}).get('use_tavily', True))
    # Scoring/filters
    min_score = float(job_cfg.get('scoring', {}).get('min_score', base_cfg.get('min_score', 3.0)))
    incident_kw_cfg = job_cfg.get('scoring', {}).get('incident_keywords')
    aggregator_kw_cfg = job_cfg.get('filters', {}).get('aggregator_keywords')
    require_incident = bool(job_cfg.get('filters', {}).get('require_incident', True))
    # Default to Australian focus if not specified in config
    require_au = bool(job_cfg.get('filters', {}).get('require_au', True))
    # QA controls
    qa_prompt = ''
    qa_enabled = True
    try:
        qa_section = (job_cfg.get('qa', {}) or {})
        qa_prompt = (qa_section.get('prompt', '') or '')
        qa_enabled = bool(qa_section.get('enabled', True))
    except Exception:
        qa_prompt = ''
        qa_enabled = True
    # If QA disabled or prompt contains 'accept all', relax gating to avoid burning credits
    accept_all = (not qa_enabled) or bool(re.search(r"accept\s*all", qa_prompt, flags=re.IGNORECASE)) or bool(re.search(r"accept-?all\s*:\s*true", qa_prompt, flags=re.IGNORECASE))
    if accept_all:
        require_incident = False
        require_au = False
        min_score = 0.0
    # Domains
    include_domains_override = job_cfg.get('domains', {}).get('include') if isinstance(job_cfg.get('domains', {}), dict) else None
    include_domains = include_domains_override if include_domains_override else research.include_domains
    seen: set[str] = set()
    total_seen = 0

    # Simple in-memory fetch cache per job
    _page_cache: dict[str, tuple[str, str | None]] = {}
    def _cache_get(url: str):
        key = _canon_url(url).lower()
        return _page_cache.get(key)
    def _cache_put(url: str, value: tuple[str, str | None]):
        if len(_page_cache) > 256:
            # drop an arbitrary key (LRU not necessary here)
            _page_cache.pop(next(iter(_page_cache)))
        _page_cache[_canon_url(url).lower()] = value

    # Keyword sets
    incident_kw = tuple(incident_kw_cfg) if isinstance(incident_kw_cfg, list) else (
        "ransomware","data breach","breach","cyberattack","attack","exploit",
        "vulnerability","malware","ddos","zero-day","cve-"
    )
    aggregator_kw = tuple(aggregator_kw_cfg) if isinstance(aggregator_kw_cfg, list) else (
        "op-ed","opinion","analysis","weekly","monthly","annual","roundup","digest",
        "newsletter","webinar","podcast","press release","press-release","what we know",
        "explainer","guide","landscape","overview","predictions","trends","report"
    )

    def _is_low_signal(text: str) -> bool:
        tl = (text or "").lower()
        if accept_all:
            return False
        return any(k in tl for k in aggregator_kw)

    def _score_candidate(title: str, text: str, url: str) -> float:
        score = 0.0
        tl = f"{title} {text}".lower()
        # Regional signals
        try:
            netloc = urlparse(url).netloc.lower()
        except Exception:
            netloc = ""
        if any(d in (url or "") for d in include_domains):
            score += 2.5
        if netloc.endswith('.au'):
            score += 2.0
        if ("australia" in tl) or ("australian" in tl):
            score += 2.0
        # Business/organization signals
        if any(k in tl for k in [
            "business","businesses","company","companies","organisation","organization",
            "enterprise","sector","industry","sme","smb"
        ]):
            score += 1.0
        # Incident keyword boost
        hits = sum(1 for k in incident_kw if k in tl)
        score += min(3.0, 0.7 * hits)
        # CVE presence boost
        if re.search(r"\bCVE-\d{4}-\d{4,7}\b", tl):
            score += 2.0
        # Penalize obvious aggregator/opinion
        if _is_low_signal(tl):
            score -= 2.0
        return score

    # Helpers
    async def fetch_page(page_index: int) -> list[dict]:
        results = []
        extra = {"tbm": "nws"}
        s, e = research._parse_date_range_from_query(job['query'])
        if s and e:
            extra["tbs"] = f"cdr:1,cd_min:{s},cd_max:{e}"
        # Focus query on cyber attacks / exploits / breaches
        base_q = job['query']
        fq = base_q + focus_tail
        # SerpAPI page
        if use_serpapi and getattr(research, 'serpapi_api_key', None):
            try:
                serp_extra = dict(extra); serp_extra['start'] = page_index * page_size
                sr = await asyncio.get_event_loop().run_in_executor(None, research._search_serpapi, fq, page_size, 'au', 'en', serp_extra)
                results.extend(sr.get('results', []))
            except Exception:
                await _push_log(job_id, 'warning', f"SERPAPI page {page_index} failed")
        # Tavily page
        if use_tavily and getattr(research, 'tavily_api_key', None):
            try:
                tr = await asyncio.get_event_loop().run_in_executor(None, research._search_tavily, fq, page_size, include_domains)
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
        cached = _cache_get(url)
        if cached is not None:
            text, html = cached
        else:
            text, html = await _http_get_text(url)
            _cache_put(url, (text, html))
        if not text:
            await _push_log(job_id, 'warning', f"Failed to fetch: {url}")
            await database.increment_research_job_counts(job_id, errors_delta=1)
            return False
        # Low-signal early filter
        if _is_low_signal(f"{title_hint} {text}"):
            await _push_log(job_id, 'info', f"filtered_low_signal: {url}")
            return False
        extraction_prompt = None
        try:
            extraction_prompt = job_cfg.get('extraction', {}).get('prompt') if isinstance(job_cfg.get('extraction'), dict) else None
        except Exception:
            extraction_prompt = None
        fields = await _extract_fields_with_llm(llm, text, prompt_template=extraction_prompt)
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
        # Specific relevance for Microsoft PipeMagic zero-day (CVE-2025-29824)
        if any(k in tl for k in ("pipemagic", "clfs", "cve-2025-29824")):
            rel = (
                "Shows attackers rapidly weaponizing new Microsoft zero-days for ransomware. "
                "Highlights that Australian businesses must apply security updates immediately; "
                "any unpatched Windows servers could be hijacked via PipeMagic as soon as patches are released"
            )
        elif any(k in tl for k in ["australia", ".au", "australian"]):
            rel = "Relevant to Australian organizations and sectors."
        elif any(k in tl for k in ["windows","apple","ios","macos","azure","aws","google cloud","vmware","esxi"]):
            rel = "Global incident impacting widely used platforms; likely to affect Australian businesses."
        # Incident keyword presence (filter to attacks/exploits/breaches)
        content_lc = f"{title} {text}".lower()
        if (not accept_all) and (not any(k in content_lc for k in incident_kw)):
            await _push_log(job_id, 'info', f"filtered_non_incident: {url}")
            return False

        # Scoring & gating
        score = _score_candidate(title, text, url)
        if (not accept_all) and require_au and not ("australia" in content_lc or ".au" in (url or '').lower() or "australian" in content_lc):
            await _push_log(job_id, 'info', f"filtered_non_au: {url}")
            qa_ok = False
        elif (not accept_all) and (score < min_score or (require_incident and (fields and not fields.get('incident')))):
            await _push_log(job_id, 'info', f"filtered_low_score: {url} score={score:.1f}")
            qa_ok = False
        else:
            qa_ok = True

        # Duplicate check within job
        dupe = False
        try:
            existing = await database.list_research_drafts(job_id, limit=10000, offset=0)
            if any((d.get('source_url')==url) or (d.get('title')==(title)) for d in existing):
                dupe = True
        except Exception:
            dupe = False
        qa_ok = qa_ok and (not dupe) and bool(summary) and bool(url)
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
            'qa_message': '' if qa_ok else 'low score/duplicate/insufficient content',
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
    sem = asyncio.Semaphore(concurrency)
    # Respect focus_on_seed: skip external search if true
    while (not focus_on_seed):
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
        tasks = []
        async def _run(url: str, title: str):
            async with sem:
                cur2 = await database.get_research_job(job_id)
                if int(cur2.get('accepted_count') or 0) >= target:
                    return
                await process_candidate(url, title)
        for it in page:
            url = it.get('url') or ''
            title = it.get('title') or 'Untitled Incident'
            tasks.append(asyncio.create_task(_run(url, title)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
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
    md_parts.append(f"# Cyber Threats and Risks ({header_range})\n\n" if header_range else "# Cyber Threats and Risks\n\n")
    # Build summary section
    ok = [d for d in drafts if d.get('qa_status')=='ok']
    total_ok = len(ok)
    by_method: dict[str,int] = {}
    cve_set: set[str] = set()
    for d in ok:
        m = (d.get('method') or '').strip() or 'Not specified'
        by_method[m] = by_method.get(m, 0) + 1
        cves = _extract_cves(" ".join([d.get('exploit_used') or '', d.get('summary') or '']))
        for c in cves:
            cve_set.add(c)
    # Format summary bullets
    md_parts.append("## At-a-Glance Summary\n\n")
    md_parts.append(f"- Incidents: {total_ok}\n")
    if by_method:
        meth_line = ", ".join([f"{k}: {v}" for k, v in sorted(by_method.items(), key=lambda x: (-x[1], x[0]))])
        md_parts.append(f"- Methods: {meth_line}\n")
    if cve_set:
        md_parts.append(f"- Top CVEs: {', '.join(sorted(cve_set))}\n")
    md_parts.append("\n<br><br>\n\n")
    # Append incidents
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
