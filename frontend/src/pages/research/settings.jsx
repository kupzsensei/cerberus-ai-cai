import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const STORAGE_KEY = 'researchPipelineConfig';

const DEFAULTS = {
  ui: {
    query_template: 'Cyber incidents impacting or likely to impact Australian businesses from {START_DATE} to {END_DATE}',
    default_target_count: 12,
  },
  search: {
    use_serpapi: false,
    use_tavily: true,
    focus_query_tail: ' (ransomware OR "data breach" OR breach OR cyberattack OR exploit OR vulnerability OR malware OR "zero-day" OR CVE)',
    page_size: 30,
    max_candidates: 150,
    concurrency: 6,
  },
  scoring: {
    min_score: 2.0,
    incident_keywords: 'ransomware,data breach,breach,cyberattack,attack,exploit,vulnerability,malware,ddos,zero-day,cve-'
  },
  filters: {
    aggregator_keywords: 'op-ed,opinion,analysis,weekly,monthly,annual,roundup,digest,newsletter,webinar,podcast,press release,press-release,what we know,explainer,guide,landscape,overview,predictions,trends,report',
    require_incident: true,
    require_au: true,
  },
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
          search: {
            use_serpapi: !!parsed?.search?.use_serpapi,
            use_tavily: parsed?.search?.use_tavily ?? true,
            focus_query_tail: parsed?.search?.focus_query_tail ?? DEFAULTS.search.focus_query_tail,
            page_size: parsed?.search?.page_size ?? DEFAULTS.search.page_size,
            max_candidates: parsed?.search?.max_candidates ?? DEFAULTS.search.max_candidates,
            concurrency: parsed?.search?.concurrency ?? DEFAULTS.search.concurrency,
          },
          scoring: {
            min_score: parsed?.scoring?.min_score ?? DEFAULTS.scoring.min_score,
            incident_keywords: Array.isArray(parsed?.scoring?.incident_keywords)
              ? parsed.scoring.incident_keywords.join(',')
              : (parsed?.scoring?.incident_keywords || DEFAULTS.scoring.incident_keywords),
          },
          filters: {
            aggregator_keywords: Array.isArray(parsed?.filters?.aggregator_keywords)
              ? parsed.filters.aggregator_keywords.join(',')
              : (parsed?.filters?.aggregator_keywords || DEFAULTS.filters.aggregator_keywords),
            require_incident: parsed?.filters?.require_incident ?? DEFAULTS.filters.require_incident,
            require_au: parsed?.filters?.require_au ?? DEFAULTS.filters.require_au,
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
      search: {
        use_serpapi: !!state.search.use_serpapi,
        use_tavily: !!state.search.use_tavily,
        focus_query_tail: state.search.focus_query_tail,
        page_size: Number(state.search.page_size) || 30,
        max_candidates: Number(state.search.max_candidates) || 150,
        concurrency: Number(state.search.concurrency) || 6,
      },
      scoring: {
        min_score: Number(state.scoring.min_score) || 0,
        incident_keywords: (state.scoring.incident_keywords || '')
          .split(',').map(s=>s.trim()).filter(Boolean),
      },
      filters: {
        aggregator_keywords: (state.filters.aggregator_keywords || '')
          .split(',').map(s=>s.trim()).filter(Boolean),
        require_incident: !!state.filters.require_incident,
        require_au: !!state.filters.require_au,
      },
      extraction: {
        prompt: state.extraction.prompt || '',
      },
      domains: (state.domains.include && state.domains.include.trim().length > 0) ? {
        include: state.domains.include.split(/\r?\n/).map(s=>s.trim()).filter(Boolean)
      } : undefined,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
    setSavedMsg('Settings saved');
    setTimeout(()=>setSavedMsg(''), 1500);
  };

  const reset = () => {
    setState(DEFAULTS);
  };

  return (
    <div className="page-content p-5">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Research Settings</h1>
        <Link to="/threats-and-risks" className="px-3 py-1 border border-green-500 text-green-500 rounded hover:bg-green-500 hover:text-white">Back to Research</Link>
      </div>
      {savedMsg && <div className="text-green-400 mb-2">{savedMsg}</div>}
      <div className="mb-4">
        <button onClick={()=>{ setState(DEFAULTS); }} className="px-3 py-1 border border-indigo-500 text-indigo-300 rounded hover:bg-indigo-600 hover:text-white">Apply AU Business Focus Preset</button>
        <span className="text-xs text-gray-400 ml-3">Recommended for incidents affecting Australian businesses</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
        </section>

        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">Search</div>
          <div className="text-xs text-gray-400 mb-2">Control which web search sources are used to find incidents.</div>
          <div className="flex items-center gap-3">
            <label className="text-sm text-green-300">Use SERPAPI</label>
            <input type="checkbox" checked={state.search.use_serpapi} onChange={(e)=>setState(s=>({...s, search:{...s.search, use_serpapi:e.target.checked}}))} />
          </div>
          <div className="flex items-center gap-3 mt-2">
            <label className="text-sm text-green-300">Use Tavily</label>
            <input type="checkbox" checked={state.search.use_tavily} onChange={(e)=>setState(s=>({...s, search:{...s.search, use_tavily:e.target.checked}}))} />
          </div>
          <div className="mt-3">
            <label className="block text-sm text-green-300 mb-1">Focus Query Tail</label>
            <input type="text" value={state.search.focus_query_tail} onChange={(e)=>setState(s=>({...s, search:{...s.search, focus_query_tail:e.target.value}}))}
                   className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm text-green-300 mb-1">Page Size</label>
              <input type="number" value={state.search.page_size} onChange={(e)=>setState(s=>({...s, search:{...s.search, page_size:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Max Candidates</label>
              <input type="number" value={state.search.max_candidates} onChange={(e)=>setState(s=>({...s, search:{...s.search, max_candidates:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
            <div>
              <label className="block text-sm text-green-300 mb-1">Concurrency</label>
              <input type="number" value={state.search.concurrency} onChange={(e)=>setState(s=>({...s, search:{...s.search, concurrency:e.target.value}}))}
                     className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/10" />
            </div>
          </div>
        </section>

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
            <label className="block text-sm text-green-300 mb-1">Incident Keywords (comma separated)</label>
            <textarea rows={3} value={state.scoring.incident_keywords}
                      onChange={(e)=>setState(s=>({...s, scoring:{...s.scoring, incident_keywords:e.target.value}}))}
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
    </div>
  );
};

export default ResearchSettingsPage;
