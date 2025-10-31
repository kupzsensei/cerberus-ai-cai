import React, { useState, useEffect, useRef } from "react";
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

  const researchResult =
    research.result || "No result text found for this research.";

  const sanitizeBreaks = (text) => {
    if (!text) return text;
    return text
      .replace(/<br\s*\/?>\s*<br\s*\/?>/gi, "\n\n")
      .replace(/<br\s*\/?>/gi, "\n");
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
        <div
          className="result-actions"
          style={{ display: "flex", alignItems: "center", gap: "20px" }}
        >
          <Link to="/research/list" className="download-btn text-green-500 border-green-500 border p-2 font-bold">
            Back to Research List
          </Link>
        </div>
      </div>

      <div
        className="markdown-content-container p-1 text-green-500 text-lg mt-10"
        ref={resultRef}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {sanitizeBreaks(researchResult)}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default ResearchDetailPage;
