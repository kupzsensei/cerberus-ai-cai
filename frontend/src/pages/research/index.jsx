import React, { useState } from "react";
import { researchByDate, startResearchJob, getResearchJobStatus, getResearchJobDrafts, cancelResearchJob } from "../../api/apiService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useOutletContext, Link } from "react-router-dom";

const ResearchPage = () => {
  const { selectedOllamaServer, selectedModel } = useOutletContext();
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState("");
  const [targetCount, setTargetCount] = useState(10);
  const [seedUrls, setSeedUrls] = useState("");
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(false);

  const sanitizeBreaks = (text) => {
    if (!text) return text;
    return text
      .replace(/<br\s*\/?>\s*<br\s*\/?>/gi, "\n\n")
      .replace(/<br\s*\/?>/gi, "\n");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!startDate || !endDate || !selectedOllamaServer || !selectedModel) {
      setError("Please select both start and end dates, and ensure a server and model are selected.");
      return;
    }
    setIsLoading(true);
    setResponse(null);
    setError("");
    try {
      const query = `cybersecurity incidents in Australia from ${startDate} to ${endDate}`;
      const formData = new FormData();
      formData.append("query", query);
      formData.append("server_name", selectedOllamaServer.name);
      formData.append("model_name", selectedModel);
      formData.append("server_type", selectedOllamaServer.type);
      const result = await researchByDate(formData);
      setResponse(result);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "An unknown error occurred.");
    } finally {
      setIsLoading(false);
    }
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
      const query = `cybersecurity incidents in Australia from ${startDate} to ${endDate}`;
      const payload = {
        query,
        serverName: selectedOllamaServer.name,
        modelName: selectedModel,
        serverType: selectedOllamaServer.type,
        targetCount,
        seedUrls: seedUrls && seedUrls.trim().length > 0 ? seedUrls : undefined,
        focusOnSeed: seedUrls && seedUrls.trim().length > 0 ? true : false,
      };
      const { job_id } = await startResearchJob(payload);
      setJobId(job_id);
      const es = new EventSource(`/api/research/jobs/${job_id}/events`);
      es.onmessage = (evt) => {
        if (!evt.data) return;
        try {
          setLogs((prev) => [...prev, JSON.parse(evt.data)]);
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
    <div className="page-content p-5">
      <h1 className="text-2xl font-bold mb-4">Cybersecurity Research</h1>
      <p className="text-gray-300 mb-6">Select a date range to search for cybersecurity threats and risks.</p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="prompt-area">
          <label htmlFor="startDate" className="block text-lg font-medium text-white mb-2">Start Date</label>
          <input type="date" id="startDate" className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/20"
            value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>
        <div className="prompt-area">
          <label htmlFor="endDate" className="block text-lg font-medium text-white mb-2">End Date</label>
          <input type="date" id="endDate" className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/20"
            value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>
        <button type="submit" className="w-full px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white"
          disabled={isLoading || !startDate || !endDate || !selectedOllamaServer}>
          {isLoading ? "Researching..." : "Start Research"}
        </button>
      </form>

      {error && <div className="error-message text-red-500 mt-4">{error}</div>}

      {response && response.result && (
        <div className="response-area mt-4 p-4 bg-gray-800 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-white mb-2">Research Results</h3>
          <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-invert max-w-none">
            {sanitizeBreaks(response.result)}
          </ReactMarkdown>
        </div>
      )}

      <div className="mt-10 border-t border-green-800 pt-6">
        <h2 className="text-xl font-semibold mb-3">New Research Pipeline (Draft-first)</h2>
        <form onSubmit={startPipeline} className="space-y-4">
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
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchPage;
