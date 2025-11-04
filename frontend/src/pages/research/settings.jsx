import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const STORAGE_KEY = 'researchPipelineConfig';

const DEFAULTS = {
  ui: {
    // Single editable query template used to build the search query
    query_template: 'Cyber threats and risks from {START_DATE} to {END_DATE}',
    default_target_count: 12,
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
    // Preserve keywords internally (not exposed in simplified UI)
    incident_keywords: 'ransomware,data breach,breach,cyberattack,attack,exploit,vulnerability,malware,ddos,zero-day,cve-'
  },
  filters: {
    // Preserve aggregator list internally (not exposed in simplified UI)
    aggregator_keywords: 'op-ed,opinion,analysis,weekly,monthly,annual,roundup,digest,newsletter,webinar,podcast,press release,press-release,what we know,explainer,guide,landscape,overview,predictions,trends,report',
    require_incident: true,
    require_au: true,
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

  return (
    <div className="page-content p-5">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Research Settings</h1>
        <Link to="/research" className="px-3 py-1 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white">Back</Link>
      </div>
      <div className="text-sm text-green-300 mb-6">Simplified: set your query, choose providers, and tune QA. Stored in your browser.</div>

      <div className="grid grid-cols-1 gap-4">
        {/* 1) Query used for Searching */}
        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">1) Query used for Searching</div>
          <div className="text-xs text-gray-400 mb-2">Optional placeholders: {'{START_DATE}'} and {'{END_DATE}'}.</div>
          <textarea rows={3} value={state.ui.query_template}
                    onChange={(e)=>setState(s=>({...s, ui:{...s.ui, query_template:e.target.value}}))}
                    className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/10 font-mono text-sm" />
        </section>

        {/* 2) Search SerpAPI and Tavily (no focus query tail) */}
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

        {/* 3) QA (enable/disable + instructions) */}
        <section className="bg-gray-900 p-4 rounded border border-gray-700">
          <div className="font-semibold mb-2">3) QA</div>
          <div className="text-xs text-gray-400 mb-2">Toggle QA to apply strict acceptance filters. Add instructions to influence acceptance behavior (hint: include "accept all" for permissive mode).</div>
          <div className="flex items-center gap-3 mb-3">
            <label className="flex items-center gap-2 text-sm text-green-300">
              <input type="checkbox" checked={!!state.qa.enabled}
                     onChange={(e)=>setState(s=>({...s, qa:{...s.qa, enabled:e.target.checked}}))} />
              Enable QA
            </label>
          </div>
          <textarea rows={8} value={state.qa.prompt}
                    onChange={(e)=>setState(s=>({...s, qa:{...s.qa, prompt:e.target.value}}))}
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
