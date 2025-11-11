import React, { useState, useEffect, useRef, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import '../../PdfProfessor.css'
import { getResearchById } from "../../api/apiService";


const ResearchDetailPage = () => {
  const { researchId } = useParams();
  const [research, setResearch] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const resultRef = useRef(null);

  useEffect(() => {
      const fetchResearch = async () => {
      try {
        const data = await getResearchById(researchId);
        setResearch(data);
      } catch (err) {
        setError("Failed to fetch research details.");
      } finally {
        setIsLoading(false);
      }
    };
      fetchResearch();
  }, [researchId]);

  // Prepare markdown and table of contents early so hooks are not conditional
  const researchResult = (research && typeof research.result === 'string') ? research.result : '';

  const sanitizeBreaks = (text) => {
    if (!text) return text;
    return text
      .replace(/<br\s*\/?>\s*<br\s*\/?>/gi, "\n\n")
      .replace(/<br\s*\/?>/gi, "\n");
  };

  const mdText = useMemo(() => sanitizeBreaks(researchResult) || '', [researchResult]);

  const slugify = (str) => {
    return (str || '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');
  };

  // Extract a simple ToC from H2 headings (## ...)
  const toc = useMemo(() => {
    try {
      const items = [];
      const re = /^##\s+(.+)$/gm;
      let m;
      while ((m = re.exec(mdText)) !== null) {
        const title = (m[1] || '').trim();
        items.push({ title, id: slugify(title) });
      }
      return items;
    } catch {
      return [];
    }
  }, [mdText]);

  // Early returns after hooks to keep hook order stable across renders
  if (isLoading)
    return (
      <div className="page-content">
        <h2>Loading Research...</h2>
      </div>
    );
  if (error) return <div className="page-content error-message">{error}</div>;
  if (!research)
    return (
      <div className="page-content">
        <h2>Research not found.</h2>
      </div>
    );

  const safeFileName = (base) => {
    const s = (base || '').toString();
    return s.replace(/[^a-z0-9-_]+/gi, '_').slice(0, 80) || 'report';
  };

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(mdText || '');
      setError('');
    } catch (e) {
      setError('Copy failed');
      setTimeout(()=>setError(''), 1500);
    }
  };

  const downloadStringAsFile = (filename, content, mime) => {
    const blob = new Blob([content], { type: mime || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleDownloadMarkdown = () => {
    const fname = safeFileName(research.query) + '.md';
    downloadStringAsFile(fname, mdText || '', 'text/markdown');
  };

  const escapeHtml = (s) => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const handleDownloadHtml = () => {
    try {
      const bodyInner = resultRef.current ? resultRef.current.innerHTML : '';
      const title = research?.query ? escapeHtml(research.query) : 'Threats and Risks Report';
      const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>${title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;background:#0b0f0f;color:#d1fae5;}
 h1,h2,h3{color:#34d399;margin-top:1.5rem}
 a{color:#60a5fa;text-decoration:underline}
 hr{border:none;border-top:1px solid #1f2937;margin:1rem 0}
 li{margin:0.25rem 0}
 .report{line-height:1.6}
 @media print{ a{color:#0645ad;text-decoration:none} }
</style></head><body><article class="report">${bodyInner}</article></body></html>`;
      const fname = safeFileName(research.query) + '.html';
      downloadStringAsFile(fname, html, 'text/html');
    } catch (e) {
      setError('Download HTML failed');
      setTimeout(()=>setError(''), 1500);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="page-content p-5">
      <div
        className="result-header"
        style={{ display: "flex", flexDirection: "column-reverse" }}
      >
        <h1>Research Query: {research.query}</h1>
        <div className="task-metadata">
            <p><strong>Created At:</strong> {new Date(research.created_at).toLocaleString()}</p>
        </div>
        <div className="result-actions flex flex-wrap items-center gap-2 mt-2">
          <Link to="/research/list" className="text-green-500 border border-green-500 px-3 py-1 rounded hover:bg-green-500 hover:text-white">
            Back to Research List
          </Link>
          <button onClick={handleCopyMarkdown} className="text-indigo-300 border border-indigo-500 px-3 py-1 rounded hover:bg-indigo-600 hover:text-white">Copy Markdown</button>
          <button onClick={handleDownloadMarkdown} className="text-indigo-300 border border-indigo-500 px-3 py-1 rounded hover:bg-indigo-600 hover:text-white">Download .md</button>
          <button onClick={handleDownloadHtml} className="text-indigo-300 border border-indigo-500 px-3 py-1 rounded hover:bg-indigo-600 hover:text-white">Download .html</button>
          <button onClick={handlePrint} className="text-indigo-300 border border-indigo-500 px-3 py-1 rounded hover:bg-indigo-600 hover:text-white">Print</button>
        </div>
      </div>

      {toc && toc.length > 0 && (
        <div className="mt-4 text-sm text-gray-300">
          <div className="font-semibold text-green-300 mb-2">Contents</div>
          <ul className="list-disc ml-6">
            {toc.map((t)=> (
              <li key={t.id} className="mb-1"><a href={`#${t.id}`} className="text-blue-300 hover:underline">{t.title}</a></li>
            ))}
          </ul>
        </div>
      )}

      <div className="markdown-content-container p-1 text-green-100 text-base mt-6 leading-7" ref={resultRef}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline" />,
            h1: ({node, children, ...props}) => {
              const text = React.Children.toArray(children).join('');
              const id = slugify(text);
              return <h1 id={id} {...props} className="text-3xl font-bold text-green-300 mt-6 mb-2">{children}</h1>;
            },
            h2: ({node, children, ...props}) => {
              const text = React.Children.toArray(children).join('');
              const id = slugify(text);
              return <h2 id={id} {...props} className="text-2xl font-bold text-green-300 mt-6 mb-2">{children}</h2>;
            },
            h3: ({node, children, ...props}) => {
              const text = React.Children.toArray(children).join('');
              const id = slugify(text);
              return <h3 id={id} {...props} className="text-xl font-semibold text-green-300 mt-5 mb-2">{children}</h3>;
            },
            p: ({node, ...props}) => <p {...props} className="my-3" />,
            ul: ({node, ...props}) => <ul {...props} className="list-disc ml-6 my-3" />,
            ol: ({node, ...props}) => <ol {...props} className="list-decimal ml-6 my-3" />,
            li: ({node, ...props}) => <li {...props} className="my-1" />,
            hr: ({node, ...props}) => <hr {...props} className="border-gray-700 my-4" />,
          }}
        >
          {mdText}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default ResearchDetailPage;
