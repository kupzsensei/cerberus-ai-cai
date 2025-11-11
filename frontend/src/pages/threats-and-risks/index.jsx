import React, { useEffect, useState } from "react";
import { startResearchJob, getResearchJobStatus, getResearchJobDrafts, cancelResearchJob } from "../../api/apiService";
import { useOutletContext, Link } from "react-router-dom";

const ThreatsAndRisksPage = () => {
    const { selectedOllamaServer, selectedModel } = useOutletContext();
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [error, setError] = useState("");
    // New pipeline state
    const [targetCount, setTargetCount] = useState(10);
    const [seedUrls, setSeedUrls] = useState("");
    const [jobId, setJobId] = useState(null);
    const [jobStatus, setJobStatus] = useState(null);
    const [drafts, setDrafts] = useState([]);
    const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({discovered:0,fetched:0,parsed:0,drafts:0,duplicates:0,errors:0});
  const [domainStats, setDomainStats] = useState([]);

    // Load saved config from localStorage
  const [config, setConfig] = useState(null);
  useEffect(() => {
      try {
          const saved = localStorage.getItem('researchPipelineConfig');
          if (saved) setConfig(JSON.parse(saved));
      } catch {}
  }, []);
    useEffect(() => {
        if (config?.ui?.default_target_count != null) {
            setTargetCount(Number(config.ui.default_target_count) || 10);
        }
    }, [config]);

    const buildQuery = () => {
        const tpl = config?.ui?.query_template || 'cybersecurity incidents in Australia from {START_DATE} to {END_DATE}';
        return tpl.replace('{START_DATE}', startDate || '').replace('{END_DATE}', endDate || '');
    };

    const startPipeline = async (e) => {
        e.preventDefault();
        if (!startDate || !endDate || !selectedOllamaServer || !selectedModel) {
            setError("Please select both start and end dates, and ensure a server and model are selected.");
            return;
        }
        setError("");
        setLogs([]);
        setDrafts([]);
        setJobId(null);
        setRunning(true);
        try {
            const query = buildQuery();
            const cfg = config || undefined;
            const payload = {
                query,
                serverName: selectedOllamaServer.name,
                modelName: selectedModel,
                serverType: selectedOllamaServer.type,
                targetCount,
                seedUrls: seedUrls && seedUrls.trim().length > 0 ? seedUrls : undefined,
                focusOnSeed: seedUrls && seedUrls.trim().length > 0 ? true : false,
                config: cfg,
            };
            const { job_id } = await startResearchJob(payload);
            setJobId(job_id);
            const es = new EventSource(`/api/research/jobs/${job_id}/events`);
      es.onmessage = (evt) => {
        if (!evt.data) return;
        try {
          const obj = JSON.parse(evt.data);
          if (obj && obj.level && obj.message) {
            setLogs((prev) => [...prev, obj]);
          } else if (obj && obj.type === 'progress' && obj.counters) {
            setProgress(obj.counters);
            if (Array.isArray(obj.domains)) setDomainStats(obj.domains);
          }
        } catch {}
      };
            es.onerror = () => { es.close(); };
            const poll = async () => {
                try {
                    const st = await getResearchJobStatus(job_id);
                    setJobStatus(st);
                    const dr = await getResearchJobDrafts(job_id);
                    setDrafts(dr);
                    if (["qa","finalized","failed","canceled"].includes(st.status)) { setRunning(false); es.close(); return; }
                } catch {}
                setTimeout(poll, 1500);
            };
            setTimeout(poll, 1000);
        } catch (err) {
            setRunning(false);
            setError(err.response?.data?.detail || err.message);
        }
    };

    return (
    <div className="page-content text-green-500 border-b p-5">
        <h1 className="font-bold">Threats and Risks</h1>
        <div className="flex items-center justify-between">
            <p>Run the research pipeline to draft and finalize a report.</p>
            <Link to="/research/settings" className="px-3 py-1 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white">Settings</Link>
        </div>
        {config?.discovery?.bypass_cache && (
            <div className="mt-3 mb-2 p-2 bg-yellow-900/40 border border-yellow-600 text-yellow-100 rounded">
                Cache bypass is ON: this job will ignore DB cache and fetch fresh content.
            </div>
        )}
        {config && (
            <div className="mt-2 mb-2 text-xs text-gray-400">
                <span className="text-gray-300">Active config:</span>
                <span className="ml-2">mode={(config.discovery && config.discovery.mode) ? config.discovery.mode : ((config.search && (config.search.use_serpapi || config.search.use_tavily)) ? 'search' : 'api_free')}</span>
                <span className="ml-3">min_score={typeof config?.scoring?.min_score === 'number' ? config.scoring.min_score : 'default'}</span>
                <span className="ml-3">incident={config?.filters?.require_incident ? 'on' : 'off'}</span>
                <span className="ml-3">AU filter={config?.filters?.require_au ? 'on' : 'off'}</span>
            </div>
        )}
        {error && <div className="error-message">{error}</div>}

            <div className="mt-10 border-t border-green-800 pt-6">
                <h2 className="text-xl font-semibold mb-3">Research Pipeline</h2>
                <form onSubmit={startPipeline} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="prompt-area">
                            <label htmlFor="startDate">Start Date</label>
                            <input
                                type="date"
                                id="startDate"
                                className="p-2 border border-green-600 rounded-md text-white bg-green-500/50"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>
                        <div className="prompt-area">
                            <label htmlFor="endDate">End Date</label>
                            <input
                                type="date"
                                id="endDate"
                                className="p-2 border border-green-600 rounded-md text-white bg-green-500/50"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="text-xs text-gray-400">Query preview: <span className="text-gray-300">{buildQuery()}</span></div>
                    <div>
                        <label className="block text-sm text-green-300 mb-1">Result Count</label>
                        <input type="number" min={1} max={100} value={targetCount} onChange={(e)=>setTargetCount(parseInt(e.target.value||'0'))}
                            className="w-40 p-2 border border-green-600 rounded-md text-white bg-green-500/20" />
                    </div>
                    <div>
                        <label className="block text-sm text-green-300 mb-1">Seed URLs (optional, newline separated)</label>
                        <textarea value={seedUrls} onChange={(e)=>setSeedUrls(e.target.value)} rows={4}
                            className="w-full p-2 border border-green-600 rounded-md text-white bg-green-500/20" placeholder="https://...\nhttps://..." />
                    </div>
                    {/* Settings moved to dedicated page */}
                    <button type="submit" disabled={running}
                        className="px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white">
                        {running ? 'Running...' : 'Start Pipeline'}
                    </button>
                </form>
                {jobId && (
                  <div className="mt-6">
                        <div className="mb-2 text-sm text-green-300">Job ID: {jobId}</div>
                        <div className="mb-4">
                            <div className="h-2 w-full bg-green-950 rounded">
                                <div className="h-2 bg-green-500 rounded" style={{width: jobStatus && jobStatus.target_count ? `${Math.min(100, Math.round((jobStatus.accepted_count||0)*100/(jobStatus.target_count||1)))}%` : '0%'}} />
                            </div>
                            <div className="text-xs text-green-300 mt-1">Accepted: {jobStatus?.accepted_count || 0} / {jobStatus?.target_count || targetCount}</div>
                            <div className="text-xs text-gray-400 mt-1">Discovered: {progress.discovered} • Fetched: {progress.fetched} • Parsed: {progress.parsed} • Drafts: {progress.drafts} • Duplicates: {progress.duplicates} • Errors: {progress.errors}</div>
                            {domainStats.length > 0 && (
                              <div className="text-xs text-gray-500 mt-1">
                                By domain: {domainStats.map(d=> `${d.domain} ${d.fetched||0}/${d.errors||0}`).join(' • ')}
                              </div>
                            )}
                        </div>
                        <div className="mb-4 flex gap-3 items-center">
                            <button onClick={async ()=>{ try{ await cancelResearchJob(jobId); setRunning(false);}catch(e){} }}
                                className="px-3 py-1 border border-red-500 text-red-500 rounded hover:bg-red-500 hover:text-white" disabled={!running}>Cancel</button>
                            {jobStatus?.status === 'finalized' && jobStatus?.research_id && (
                                <Link to={`/research/${jobStatus.research_id}`}
                                      className="px-3 py-1 border border-green-500 text-green-500 rounded hover:bg-green-500 hover:text-white">
                                    View Final Report
                                </Link>
                            )}
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-gray-900 p-3 rounded">
                                <div className="font-semibold mb-2">Live Logs</div>
                                <div className="h-48 overflow-auto text-xs whitespace-pre-wrap">
                                    {logs.map((l, i)=> (<div key={i}>[{l.ts}] {l.level?.toUpperCase?.() || ''}: {l.message}</div>))}
                                </div>
                            </div>
                            <div className="bg-gray-900 p-3 rounded">
                                <div className="font-semibold mb-2">Drafts</div>
                                <div className="h-48 overflow-auto text-xs">
                                    {drafts.map((d)=> (
                                        <div key={d.id} className="mb-2 border-b border-gray-700 pb-1">
                                            <div className="text-green-400">{d.title}</div>
                                            <div className="text-green-300">{d.date}</div>
                                            <div className="text-gray-400">QA: {d.qa_status || 'pending'}</div>
                                            <div className="text-indigo-400 truncate">{d.source_url}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                        {domainStats.length > 0 && (
                          <div className="bg-gray-900 p-3 rounded mt-4">
                            <div className="font-semibold mb-2">Domains</div>
                            <div className="overflow-auto">
                              <table className="w-full text-xs">
                                <thead>
                                  <tr className="text-left text-gray-400">
                                    <th className="py-1 pr-3">Domain</th>
                                    <th className="py-1 pr-3">Fetched</th>
                                    <th className="py-1 pr-3">Errors</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {domainStats.map((d, i)=> (
                                    <tr key={i} className="border-t border-gray-800">
                                      <td className="py-1 pr-3 text-gray-300">{d.domain}</td>
                                      <td className="py-1 pr-3 text-green-300">{d.fetched||0}</td>
                                      <td className="py-1 pr-3 text-red-400">{d.errors||0}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                  </div>
                )}
            </div>
        </div>
    );
};

export default ThreatsAndRisksPage;
