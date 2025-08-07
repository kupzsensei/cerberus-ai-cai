import React, { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import jsPDF from "jspdf";
import '../../PdfProfessor.css'
import { getTaskById } from "../../api/apiService";
import MarkdownRenderer from "../../components/MarkdownRenderer";


const ResultPage = () => {
  const { taskId } = useParams();
  const [task, setTask] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [error, setError] = useState("");
  const resultRef = useRef(null);

  useEffect(() => {
    const fetchTask = async () => {
      try {
        const data = await getTaskById(taskId);
        setTask(data);
      } catch (err) {
        setError("Failed to fetch task details.");
      } finally {
        setIsLoading(false);
      }
    };
    fetchTask();
  }, [taskId]);

  const handleDownloadPdf = () => {
    const input = resultRef.current;
    if (!input) return;

    setIsGeneratingPdf(true);

    const pdf = new jsPDF({
      orientation: "portrait",
      unit: "pt",
      format: "a4",
    });

    pdf
      .html(input, {
        callback: function (doc) {
          doc.save(`${taskId || "result"}.pdf`);
          setIsGeneratingPdf(false);
        },
        margin: [60, 40, 60, 40],
        autoPaging: "slice",
        width: 515,
        windowWidth: 1000,
      })
      .catch((err) => {
        console.error("Error generating PDF:", err);
        setIsGeneratingPdf(false);
      });
  };

  if (isLoading)
    return (
      <div className="page-content">
        <h2>Loading Result...</h2>
      </div>
    );
  if (error) return <div className="page-content error-message">{error}</div>;
  if (!task)
    return (
      <div className="page-content">
        <h2>Task not found.</h2>
      </div>
    );

  const processedText =
    task.result?.processed_text || "No result text found for this task.";

  return (
    <div className="page-content p-5">
      <div
        className="result-header"
        style={{ display: "flex", flexDirection: "column-reverse" }}
      >
        <h1>Result for: {task.task_id}</h1>
        {/* --- ADDED: Task metadata --- */}
        <div className="task-metadata">
            <p><strong>Query:</strong> {task.prompt || 'N/A'}</p>
            <p><strong>Model Used:</strong> {task.model_name || 'N/A'}</p>
            <p><strong>Server:</strong> {task.server_name || 'N/A'} ({task.server_type || 'N/A'})</p>
            <p><strong>Processing Time:</strong> {task.processing_time_seconds ? `${task.processing_time_seconds} seconds` : 'N/A'}</p>
        </div>
        <div
          className="result-actions"
          style={{ display: "flex", alignItems: "center", gap: "20px" }}
        >
          <span
            onClick={handleDownloadPdf}
            className="download-btn text-green-500 border-green-500 border p-2 font-bold cursor-pointer"
            disabled={isGeneratingPdf}
          >
            {isGeneratingPdf ? "Generating PDF..." : "Download as PDF"}
          </span>
          <Link to="/task-status" className="download-btn text-green-500 border-green-500 border p-2 font-bold">
            Back to Status List
          </Link>
        </div>
      </div>

      <div
        className="markdown-content-container p-1 text-green-500 text-lg mt-10"
        ref={resultRef}
      >
        <MarkdownRenderer content={processedText} />
      </div>
    </div>
  );
};

export default ResultPage;