import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCacheDomains, getCacheEntries, deleteCache, refetchCacheUrl, refetchCacheDomain } from '../../api/apiService';

const STORAGE_KEY = 'researchPipelineConfig';

const DEFAULTS = {
  ui: {
    // Single editable query template used to build the search query
    query_template: 'Cyber threats and risks from {START_DATE} to {END_DATE}',
    default_target_count: 12,
  },
  discovery: {
    mode: 'api_free',
    recency_days: 30,
    crawl_depth: 1,
    max_pages_per_domain: 40,
    per_domain_rps: 0.5,
    global_concurrency: 8,
    cache_ttl_hours: 24,
    bypass_cache: false,
    keyword_include: 'ransomware,breach,cyberattack,exploit,vulnerability,CVE',
    keyword_exclude: 'opinion,weekly,digest,podcast,webinar',
  },
  sources: {
    rss_urls: [
      'https://isc.sans.edu/rssfeed.xml',
      'https://www.cisa.gov/news-events/cybersecurity-advisories.xml',
      'https://www.bleepingcomputer.com/feed/',
      'https://www.securityweek.com/feed/',
      'https://www.darkreading.com/rss.xml',
      'https://krebsonsecurity.com/feed/',
      'https://www.tenable.com/blog/feed',
      'https://www.rapid7.com/blog/feed/',
      'https://blog.qualys.com/feed',
      'https://unit42.paloaltonetworks.com/feed/',
      'https://blog.talosintelligence.com/feed/',
      'https://www.crowdstrike.com/blog/feed/',
      'https://www.mandiant.com/resources/blog/rss.xml',
      'https://thehackernews.com/feeds/posts/default',
      'https://security.googleblog.com/feeds/posts/default',
      'https://www.microsoft.com/en-us/security/blog/feed/',
      'https://securelist.com/feed/',
      'https://research.checkpoint.com/feed/',
      'https://blog.cloudflare.com/tag/security/rss/'
    ].join('\n'),
    sitemap_domains: '',
    allowlist_domains: '',
  },
  search: {
    // Only provider toggles; no focus query tail
    use_serpapi: true,
    use_tavily: true,
    focus_query_tail: '',
    // Keep advanced knobs but hide them in UI; retain sane defaults
    page_size: 30,
    max_candidates: 150,
    concurrency: 6,
  },
  scoring: {
    // QA: acceptance threshold
    min_score: 2.0,
    incident_keywords: 'ransomware,data breach,breach,cyberattack,attack,exploit,vulnerability,malware,ddos,zero-day,cve-',
    au_bias: 1.2,
    domain_weights: ''
  },
  filters: {
    // Preserve aggregator list internally (not exposed in simplified UI)
    aggregator_keywords: 'op-ed,opinion,analysis,weekly,monthly,annual,roundup,digest,newsletter,webinar,podcast,press release,press-release,what we know,explainer,guide,landscape,overview,predictions,trends,report',
    require_incident: false,
    require_au: false,
  },
  qa: {
    // Single prompt to instruct how QA should accept/reject incidents
    prompt: 'QA rules: Accept only specific cyber incidents or clearly actionable, high-likelihood threats. Prefer Australian relevance (mentions of Australia/Australian or .au domains); otherwise accept global platform incidents that materially impact Australian businesses (Windows, Apple iOS/macos, cloud platforms, VMware, etc.). Reject aggregators/op-eds/weekly roundups/trend reports. Ensure a one-sentence summary is factual and concise; populate Date of Incident if present; infer Method from context (Ransomware, Data breach, Phishing, Vulnerability exploitation, DDoS, Supply chain, Credential stuffing, BEC, Vishing, Malware/Backdoor, Espionage). Include detected CVEs in Exploit Used. Keep tone neutral and analytic.',
    enabled: true,
  },
  // Keep extraction + domains in config (not exposed); users can still edit JSON manually if needed
  extraction: {
    prompt: 'You are a cybersecurity analyst focused on incidents impacting Australian businesses. Return ONLY minified JSON with keys {"summary","date","targets","method","exploit_used","incident"}. Method must be one of [Ransomware, Phishing, Data breach, DDoS, Vulnerability exploitation, Supply chain compromise, Credential stuffing, Business email compromise, Vishing, Malware/Backdoor, Espionage]. Set incident=true only if this article describes an actual cyberattack/breach/exploit/outage affecting an organization, or a high-likelihood threat relevant to Australian businesses. Prefer concise, factual summary. Leave unknown fields as empty string. No prose or markdown, JSON only. Article: {ARTICLE}'
  },
  domains: {
    include: ''
  }
};

const ResearchSettingsPage = () => {
  const [state, setState] = useState(DEFAULTS);
  const [savedMsg, setSavedMsg] = useState('');
  const [cacheDomains, setCacheDomains] = useState([]);
  const [selectedDomain, setSelectedDomain] = useState('');
  const [cacheEntries, setCacheEntries] = useState([]);
  const [loadingCache, setLoadingCache] = useState(false);
  const [forceRefetch, setForceRefetch] = useState(false);
  const [domainRefetchLimit, setDomainRefetchLimit] = useState(50);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setState({
          ui: {
            query_template: parsed?.ui?.query_template || DEFAULTS.ui.query_template,
            default_target_count: parsed?.ui?.default_target_count ?? DEFAULTS.ui.default_target_count,
          },
          discovery: {
            mode: parsed?.discovery?.mode || DEFAULTS.discovery.mode,
            recency_days: parsed?.discovery?.recency_days ?? DEFAULTS.discovery.recency_days,
            crawl_depth: parsed?.discovery?.crawl_depth ?? DEFAULTS.discovery.crawl_depth,
            max_pages_per_domain: parsed?.discovery?.max_pages_per_domain ?? DEFAULTS.discovery.max_pages_per_domain,
            per_domain_rps: parsed?.discovery?.per_domain_rps ?? DEFAULTS.discovery.per_domain_rps,
            global_concurrency: parsed?.discovery?.global_concurrency ?? DEFAULTS.discovery.global_concurrency,
            cache_ttl_hours: parsed?.discovery?.cache_ttl_hours ?? DEFAULTS.discovery.cache_ttl_hours,
            bypass_cache: parsed?.discovery?.bypass_cache ?? DEFAULTS.discovery.bypass_cache,
            keyword_include: Array.isArray(parsed?.discovery?.keyword_include)
              ? parsed.discovery.keyword_include.join(',')
              : (parsed?.discovery?.keyword_include || DEFAULTS.discovery.keyword_include),
            keyword_exclude: Array.isArray(parsed?.discovery?.keyword_exclude)
              ? parsed.discovery.keyword_exclude.join(',')
              : (parsed?.discovery?.keyword_exclude || DEFAULTS.discovery.keyword_exclude),
          },
          sources: {
            rss_urls: Array.isArray(parsed?.sources?.rss_urls) ? parsed.sources.rss_urls.join('\n') : (parsed?.sources?.rss_urls || DEFAULTS.sources.rss_urls),
            sitemap_domains: Array.isArray(parsed?.sources?.sitemap_domains) ? parsed.sources.sitemap_domains.join('\n') : (parsed?.sources?.sitemap_domains || DEFAULTS.sources.sitemap_domains),
            allowlist_domains: Array.isArray(parsed?.sources?.allowlist_domains) ? parsed.sources.allowlist_domains.join('\n') : (parsed?.sources?.allowlist_domains || DEFAULTS.sources.allowlist_domains),
          },
          search: {
            use_serpapi: !!parsed?.search?.use_serpapi,
            use_tavily: parsed?.search?.use_tavily ?? true,
            // enforce no focus tail in simplified settings
            focus_query_tail: '',
            page_size: parsed?.search?.page_size ?? DEFAULTS.search.page_size,
            max_candidates: parsed?.search?.max_candidates ?? DEFAULTS.search.max_candidates,
            concurrency: parsed?.search?.concurrency ?? DEFAULTS.search.concurrency,
          },
          scoring: {
            min_score: parsed?.scoring?.min_score ?? DEFAULTS.scoring.min_score,
            incident_keywords: Array.isArray(parsed?.scoring?.incident_keywords)
              ? parsed.scoring.incident_keywords.join(',')
              : (parsed?.scoring?.incident_keywords || DEFAULTS.scoring.incident_keywords),
            au_bias: parsed?.scoring?.au_bias ?? DEFAULTS.scoring.au_bias,
            domain_weights: (parsed?.scoring?.domain_weights && typeof parsed.scoring.domain_weights === 'object')
              ? Object.entries(parsed.scoring.domain_weights).map(([k,v])=>`${k},${v}`).join('\n')
              : (parsed?.scoring?.domain_weights || DEFAULTS.scoring.domain_weights),
          },
          filters: {
            aggregator_keywords: Array.isArray(parsed?.filters?.aggregator_keywords)
              ? parsed.filters.aggregator_keywords.join(',')
              : (parsed?.filters?.aggregator_keywords || DEFAULTS.filters.aggregator_keywords),
            require_incident: parsed?.filters?.require_incident ?? DEFAULTS.filters.require_incident,
            require_au: parsed?.filters?.require_au ?? DEFAULTS.filters.require_au,
          },
          qa: {
            prompt: parsed?.qa?.prompt || DEFAULTS.qa.prompt,
            enabled: parsed?.qa?.enabled ?? DEFAULTS.qa.enabled,
          },
          extraction: {
            prompt: parsed?.extraction?.prompt || DEFAULTS.extraction.prompt,
          },
          domains: {
            include: Array.isArray(parsed?.domains?.include)
              ? parsed.domains.include.join('\n')
              : (parsed?.domains?.include || DEFAULTS.domains.include)
          }
        });
      }
    } catch {}
  }, []);

  const save = () => {
    const cfg = {
      ui: {
        query_template: state.ui.query_template,
        default_target_count: Number(state.ui.default_target_count) || 10,
      },
      discovery: {
        mode: state.discovery?.mode || 'api_free',
        recency_days: Number(state.discovery?.recency_days) || 14,
        crawl_depth: Number(state.discovery?.crawl_depth) || 1,
        max_pages_per_domain: Number(state.discovery?.max_pages_per_domain) || 40,
        per_domain_rps: Number(state.discovery?.per_domain_rps) || 0.5,
        global_concurrency: Number(state.discovery?.global_concurrency) || 8,
        cache_ttl_hours: Number(state.discovery?.cache_ttl_hours) || 24,
        bypass_cache: !!state.discovery?.bypass_cache,
        keyword_include: (state.discovery?.keyword_include || '')
          .split(',').map(s=>s.trim()).filter(Boolean),
        keyword_exclude: (state.discovery?.keyword_exclude || '')
          .split(',').map(s=>s.trim()).filter(Boolean),
      },
      sources: {
        rss_urls: (state.sources?.rss_urls || '')
          .split(/\r?\n/).map(s=>s.trim()).filter(Boolean),
        sitemap_domains: (state.sources?.sitemap_domains || '')
          .split(/\r?\n/).map(s=>s.trim()).filter(Boolean),
        allowlist_domains: (state.sources?.allowlist_domains || '')
          .split(/\r?\n/).map(s=>s.trim()).filter(Boolean),
      },
      search: {
        use_serpapi: !!state.search.use_serpapi,
        use_tavily: !!state.search.use_tavily,
        focus_query_tail: '', // enforce no focus tail
        page_size: Number(state.search.page_size) || 30,
        max_candidates: Number(state.search.max_candidates) || 150,
        concurrency: Number(state.search.concurrency) || 6,
      },
      scoring: {
        min_score: Number(state.scoring.min_score) || 0,
        // preserve keywords
        incident_keywords: (state.scoring.incident_keywords || '')
          .split(',').map(s=>s.trim()).filter(Boolean),
        au_bias: Number(state.scoring.au_bias) || 1.0,
        domain_weights: (()=>{
          const lines = (state.scoring.domain_weights || '').split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
          const map = {};
          for (const line of lines) {
            const idx = line.indexOf(',');
            if (idx > 0) {
              const k = line.slice(0, idx).trim();
              const v = parseFloat(line.slice(idx+1).trim());
              if (k && !isNaN(v)) map[k] = v;
            }
          }
          return map;
        })(),
      },
      filters: {
        // preserve aggregator keywords
        aggregator_keywords: (state.filters.aggregator_keywords || '')
          .split(',').map(s=>s.trim()).filter(Boolean),
        require_incident: !!state.filters.require_incident,
        require_au: !!state.filters.require_au,
      },
      qa: { prompt: state.qa.prompt, enabled: !!state.qa.enabled },
      extraction: { prompt: state.extraction.prompt },
      domains: { include: (state.domains.include || '').split('\n').map(s=>s.trim()).filter(Boolean) }
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    setSavedMsg('Saved');
    setTimeout(()=>setSavedMsg(''), 1500);
  };

  const reset = () => {
    setState(DEFAULTS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULTS));
  };

  const loadDomains = async () => {
    setLoadingCache(true);
    try {
      const doms = await getCacheDomains();
      setCacheDomains(doms || []);
    } catch {}
    setLoadingCache(false);
  };

  const viewDomain = async (domain) => {
    setSelectedDomain(domain);
    setLoadingCache(true);
    try {
      const res = await getCacheEntries(domain, 100, 0);
      setCacheEntries(res.entries || []);
    } catch {}
    setLoadingCache(false);
  };

  const clearDomain = async (domain) => {
    if (!confirm(`Clear cache for ${domain}?`)) return;
    await deleteCache(domain);
    await loadDomains();
    if (selectedDomain === domain) {
      setCacheEntries([]);
    }
  };

  const clearAll = async () => {
    if (!confirm('Clear ALL cache entries?')) return;
    await deleteCache();
    setCacheDomains([]);
    setCacheEntries([]);
    setSelectedDomain('');
  };

  const refetchDomain = async (domain) => {
    if (!domain) return;
    if (!confirm(`Refetch up to ${domainRefetchLimit} URLs for ${domain}?`)) return;
    setLoadingCache(true);
    try {
      await refetchCacheDomain(domain, Number(domainRefetchLimit)||50, Number(state.discovery?.cache_ttl_hours)||24, !!forceRefetch);
      await viewDomain(domain);
    } catch {}
    setLoadingCache(false);
  };

  return (
    <div className="page-content p-5">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Research Settings</h1>
        <Link to="/threats-and-risks" className="px-3 py-1 border border-green-500 text-green-500 rounded hover:bg-green-500 hover:text-white">Back to Research</Link>
      </div>
      {savedMsg && <div className="text-green-400 mb-2">{savedMsg}</div>}
      <div className="mb-4 flex items-center gap-3 flex-wrap">
        <button
          onClick={()=>{ setState(DEFAULTS); }}
          className="px-3 py-1 border border-indigo-500 text-indigo-300 rounded hover:bg-indigo-600 hover:text-white"
        >
          Apply AU Business Focus Preset
        </button>
        <span className="text-xs text-gray-400">Recommended for incidents affecting Australian businesses</span>
        <button
          onClick={()=>{
            setState(s=>({
              ...s,
              scoring: { ...s.scoring, min_score: 0.5 },
              filters: { ...s.filters, require_incident: false, require_au: false },
            }));
            setSavedMsg('Lenient preset applied (not yet saved)');
            setTimeout(()=>setSavedMsg(''), 1500);
          }}
          className="px-3 py-1 border border-yellow-500 text-yellow-300 rounded hover:bg-yellow-600 hover:text-white"
        >
          Apply Lenient Preset
        </button>
        <span className="text-xs text-gray-400">Sets min_score=0.5, incident/AU filters off</span>
      </div>
      <div className="text-sm text-green-300 mb-6">Simplified: set your query, choose providers, and tune QA. Stored in your browser.</div>

      <div className="grid grid-cols-1 gap-4">
        {/* 1) Query used for Searching */}
        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">Query & Defaults</div>
          <label className="block text-sm text-green-300 mb-1">Query Template</label>
          <input type="text" value={state.ui.query_template} onChange={(e)=>setState(s=>({...s, ui:{...s.ui, query_template:e.target.value}}))}
                 className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          <div className="text-xs text-gray-400 mt-1">Use placeholders: {'{START_DATE}'} and {'{END_DATE}'}</div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Default Result Count</label>
            <input type="number" value={state.ui.default_target_count}
                   onChange={(e)=>setState(s=>({...s, ui:{...s.ui, default_target_count:e.target.value}}))}
                   className="w-40 p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          </div>
          <div className="mt-3">
            <div className="block text-sm text-green-300 mb-1">Source Mode</div>
            <label className="mr-4 text-sm">
              <input type="radio" name="srcmode" className="mr-1" checked={(state.discovery?.mode||'api_free')==='api_free'}
                     onChange={()=>setState(s=>({...s, discovery:{...s.discovery, mode:'api_free'}}))} />
              RSS/Sitemaps (API-free)
            </label>
            <label className="text-sm">
              <input type="radio" name="srcmode" className="mr-1" checked={(state.discovery?.mode||'api_free')==='search'}
                     onChange={()=>setState(s=>({...s, discovery:{...s.discovery, mode:'search'}}))} />
              Search APIs (SerpAPI/Tavily)
            </label>
          </div>
        </section>

        <section className="bg-gray-900 p-4 rounded border border-gray-700 md:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold">Cache Admin</div>
            <div className="flex items-center gap-2">
              <button onClick={loadDomains} className="px-3 py-1 border border-green-600 text-green-400 rounded hover:bg-green-600 hover:text-white">{loadingCache ? 'Loading…' : 'Load Domains'}</button>
              <button onClick={clearAll} className="px-3 py-1 border border-red-600 text-red-400 rounded hover:bg-red-600 hover:text-white">Clear All</button>
            </div>
          </div>
          <div className="flex items-center gap-4 mb-3 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={forceRefetch} onChange={(e)=>setForceRefetch(e.target.checked)} />
              <span>Force bypass cache on refetch</span>
            </label>
            <label className="flex items-center gap-2">
              <span>Domain refetch limit</span>
              <input type="number" className="w-24 p-1 bg-green-950 border border-green-700 rounded" value={domainRefetchLimit}
                     onChange={(e)=>setDomainRefetchLimit(e.target.value)} />
            </label>
          </div>
          {cacheDomains && cacheDomains.length > 0 ? (
            <div className="overflow-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-400">
                    <th className="py-1 pr-3">Domain</th>
                    <th className="py-1 pr-3">Entries</th>
                    <th className="py-1 pr-3">Last Fetched</th>
                    <th className="py-1 pr-3">Total Bytes</th>
                    <th className="py-1 pr-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {cacheDomains.map((d, i)=> (
                    <tr key={i} className="border-t border-gray-800">
                      <td className="py-1 pr-3 text-gray-300">{d.domain}</td>
                      <td className="py-1 pr-3 text-green-300">{d.entries}</td>
                      <td className="py-1 pr-3 text-gray-400">{d.last_fetched}</td>
                      <td className="py-1 pr-3 text-gray-400">{d.total_bytes || 0}</td>
                      <td className="py-1 pr-3">
                        <button onClick={()=>viewDomain(d.domain)} className="px-2 py-0.5 border border-indigo-500 text-indigo-300 rounded hover:bg-indigo-600 hover:text-white mr-2">View</button>
                        <button onClick={()=>refetchDomain(d.domain)} className="px-2 py-0.5 border border-green-600 text-green-300 rounded hover:bg-green-600 hover:text-white mr-2">Refetch All</button>
                        <button onClick={()=>clearDomain(d.domain)} className="px-2 py-0.5 border border-red-500 text-red-300 rounded hover:bg-red-600 hover:text-white">Clear</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-sm text-gray-400">No domain stats loaded.</div>
          )}

          {selectedDomain && (
            <div className="mt-4">
              <div className="font-semibold mb-2">Entries for {selectedDomain}</div>
              <div className="overflow-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-gray-400">
                      <th className="py-1 pr-3">Status</th>
                      <th className="py-1 pr-3">URL</th>
                      <th className="py-1 pr-3">Fetched</th>
                      <th className="py-1 pr-3">Bytes</th>
                      <th className="py-1 pr-3">ETag</th>
                      <th className="py-1 pr-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cacheEntries.map((e, i)=> (
                      <tr key={i} className="border-t border-gray-800">
                        <td className="py-1 pr-3 text-gray-300">{e.status}</td>
                        <td className="py-1 pr-3 text-indigo-300 truncate" title={e.url}>{e.url}</td>
                        <td className="py-1 pr-3 text-gray-400">{e.fetched_at}</td>
                        <td className="py-1 pr-3 text-gray-400">{e.bytes || 0}</td>
                        <td className="py-1 pr-3 text-gray-500 truncate" title={e.etag}>{e.etag || ''}</td>
                        <td className="py-1 pr-3">
                          <button onClick={async()=>{ try{ await refetchCacheUrl(e.url, Number(state.discovery?.cache_ttl_hours)||24, !!forceRefetch); await viewDomain(selectedDomain);}catch{} }}
                                  className="px-2 py-0.5 border border-green-600 text-green-300 rounded hover:bg-green-600 hover:text-white">Refetch</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
        {(state.discovery?.mode||'api_free')==='api_free' && (
        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">Discovery (API-free)</div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-green-300">Use API-free discovery</label>
            <input type="checkbox" checked={(state.discovery?.mode||'api_free')==='api_free'}
                   onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, mode: e.target.checked ? 'api_free' : 'search'}}))} />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm text-green-300 mb-1">Recency (days)</label>
              <input type="number" value={state.discovery?.recency_days}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, recency_days:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Crawl Depth</label>
              <input type="number" min={1} max={2} value={state.discovery?.crawl_depth}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, crawl_depth:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Max Pages / Domain</label>
              <input type="number" value={state.discovery?.max_pages_per_domain}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, max_pages_per_domain:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm text-green-300 mb-1">Per-domain RPS</label>
              <input type="number" step="0.1" value={state.discovery?.per_domain_rps}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, per_domain_rps:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Global Concurrency</label>
              <input type="number" value={state.discovery?.global_concurrency}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, global_concurrency:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Cache TTL (hours)</label>
              <input type="number" value={state.discovery?.cache_ttl_hours}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, cache_ttl_hours:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
          </div>
          <div className="mt-3">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!state.discovery?.bypass_cache}
                     onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, bypass_cache:e.target.checked}}))} />
              <span>Bypass DB cache for jobs (fetch fresh content)</span>
            </label>
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Include Keywords (comma separated)</label>
            <input type="text" value={state.discovery?.keyword_include}
                   onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, keyword_include:e.target.value}}))}
                   className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Exclude Keywords (comma separated)</label>
            <input type="text" value={state.discovery?.keyword_exclude}
                   onChange={(e)=>setState(s=>({...s, discovery:{...s.discovery, keyword_exclude:e.target.value}}))}
                   className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          </div>
        </section>
        )}

        {(state.discovery?.mode||'api_free')==='search' && (
        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">2) Search Providers</div>
          <div className="text-xs text-gray-400 mb-4">Focus query tail is disabled for simpler, direct searches.</div>
          <div className="flex flex-col gap-3">
            <label className="flex items-center gap-3 text-sm text-green-300">
              <input type="checkbox" checked={state.search.use_serpapi}
                     onChange={(e)=>setState(s=>({...s, search:{...s.search, use_serpapi:e.target.checked}}))} />
              Use SerpAPI
            </label>
            <label className="flex items-center gap-3 text-sm text-green-300">
              <input type="checkbox" checked={state.search.use_tavily}
                     onChange={(e)=>setState(s=>({...s, search:{...s.search, use_tavily:e.target.checked}}))} />
              Use Tavily
            </label>
          </div>
          {/* API keys are configured via server environment; no frontend editing */}
        </section>
        )}

        {(state.discovery?.mode||'api_free')==='api_free' && (
        <section className="bg-gray-900 p-4 rounded border border-gray-700 md:col-span-2">
          <div className="font-semibold mb-2">Sources</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-green-300 mb-1">Allowlist Domains (one per line)</label>
              <textarea rows={6} value={state.sources?.allowlist_domains}
                        onChange={(e)=>setState(s=>({...s, sources:{...s.sources, allowlist_domains:e.target.value}}))}
                        className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">RSS URLs (one per line)</label>
              <textarea rows={6} value={state.sources?.rss_urls}
                        onChange={(e)=>setState(s=>({...s, sources:{...s.sources, rss_urls:e.target.value}}))}
                        className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Sitemap Domains (one per line)</label>
              <textarea rows={6} value={state.sources?.sitemap_domains}
                        onChange={(e)=>setState(s=>({...s, sources:{...s.sources, sitemap_domains:e.target.value}}))}
                        className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
            </div>
          </div>
        </section>
        )}

        {/* 3) QA (enable/disable + instructions) */}
        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">Scoring & Filters</div>
          <div className="text-xs text-gray-400 mb-2">Tighten or loosen acceptance. Higher minimum score and AU requirement reduce noise.</div>
          <div>
            <label className="block text-sm text-green-300 mb-1">Minimum Score</label>
            <input type="number" step="0.1" value={state.scoring.min_score}
                   onChange={(e)=>setState(s=>({...s, scoring:{...s.scoring, min_score:e.target.value}}))}
                   className="w-40 p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">AU Bias Multiplier</label>
            <input type="number" step="0.1" value={state.scoring.au_bias}
                   onChange={(e)=>setState(s=>({...s, scoring:{...s.scoring, au_bias:e.target.value}}))}
                   className="w-40 p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Incident Keywords (comma separated)</label>
            <textarea rows={3} value={state.scoring.incident_keywords}
                      onChange={(e)=>setState(s=>({...s, scoring:{...s.scoring, incident_keywords:e.target.value}}))}
                      className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Domain Weights (one per line: domain,weight)</label>
            <textarea rows={4} value={state.scoring.domain_weights}
                      onChange={(e)=>setState(s=>({...s, scoring:{...s.scoring, domain_weights:e.target.value}}))}
                      className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Aggregator Keywords (comma separated)</label>
            <textarea rows={3} value={state.filters.aggregator_keywords}
                      onChange={(e)=>setState(s=>({...s, filters:{...s.filters, aggregator_keywords:e.target.value}}))}
                      className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
          </div>
          <div className="flex items-center gap-3 mt-3">
            <label className="text-sm text-green-300">Require Incident</label>
            <input type="checkbox" checked={state.filters.require_incident}
                   onChange={(e)=>setState(s=>({...s, filters:{...s.filters, require_incident:e.target.checked}}))} />
          </div>
          <div className="flex items-center gap-3 mt-2">
            <label className="text-sm text-green-300">Require AU Relevance</label>
            <input type="checkbox" checked={state.filters.require_au}
                   onChange={(e)=>setState(s=>({...s, filters:{...s.filters, require_au:e.target.checked}}))} />
          </div>
        </section>

        <section className="bg-gray-900 p-4 rounded border border-gray-700 md:col-span-2">
          <div className="font-semibold mb-2">Extraction Prompt Template</div>
          <div className="text-xs text-gray-400 mb-2">Use the placeholder {'{ARTICLE}'} for the fetched article text. The model must return strict JSON with keys: summary, date, targets, method, exploit_used, incident. Tailor tone or acceptance criteria here.</div>
          <textarea rows={10} value={state.extraction.prompt}
                    onChange={(e)=>setState(s=>({...s, extraction:{...s.extraction, prompt:e.target.value}}))}
                    className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
        </section>

        <section className="bg-gray-900 p-4 rounded border border-gray-700 md:col-span-2">
          <div className="font-semibold mb-2">Include Domains (one per line, optional)</div>
          <textarea rows={6} value={state.domains.include}
                    onChange={(e)=>setState(s=>({...s, domains:{...s.domains, include:e.target.value}}))}
                    className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
        </section>
      </div>

      <div className="mt-6 flex gap-3">
        <button onClick={save} className="px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white">Save Settings</button>
        <button onClick={reset} className="px-4 py-2 border border-gray-500 text-gray-300 rounded-md hover:bg-gray-700">Restore Defaults</button>
      </div>

      {/* Simple toast indicator for settings save */}
      {savedMsg && (
        <div className="fixed bottom-6 right-6 bg-green-600 text-white px-4 py-2 rounded shadow-lg">
          {savedMsg}
        </div>
      )}
    </div>
  );
};

export default ResearchSettingsPage;
