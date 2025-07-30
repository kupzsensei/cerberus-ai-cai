import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { getResearchById } from "../../api/apiService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import jsPDF from "jspdf";

const InvestigationDetailPage = () => {
    const { investigationId } = useParams();
    const [investigation, setInvestigation] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        const fetchInvestigation = async () => {
            setIsLoading(true);
            try {
                const result = await getResearchById(investigationId);
                setInvestigation(result);
            } catch (err) {
                setError("Failed to fetch investigation details.");
            } finally {
                setIsLoading(false);
            }
        };
        fetchInvestigation();
    }, [investigationId]);

    const handleExportToPdf = () => {
        if (!investigation) return;

        const doc = new jsPDF();
        const margin = 20;
        let y = margin;
        const lineHeight = 7;
        const pageHeight = doc.internal.pageSize.height;
        const contentWidth = doc.internal.pageSize.getWidth() - 2 * margin;

        const addPageIfNeeded = () => {
            if (y > pageHeight - margin) {
                doc.addPage();
                y = margin;
            }
        };

        // Title
        doc.setFont("helvetica", "bold");
        doc.setFontSize(18);
        const title = investigation.query.replace("investigation: ", "");
        doc.text(title, margin, y);
        y += 10;

        // Created At
        doc.setFont("helvetica", "normal");
        doc.setFontSize(10);
        doc.text(`Created at: ${new Date(investigation.created_at).toLocaleString()}`, margin, y);
        y += 10;

        // Main Content
        const content = investigation.result;
        const lines = content.split('\n');

        lines.forEach(line => {
            addPageIfNeeded();
            let currentLine = line.trim();

            // Handle Headings
            if (currentLine.startsWith('### ')) {
                doc.setFont("helvetica", "bold");
                doc.setFontSize(14);
                doc.text(currentLine.replace('### ', ''), margin, y);
                y += lineHeight * 1.5;
            } else if (currentLine.startsWith('## ')) {
                doc.setFont("helvetica", "bold");
                doc.setFontSize(16);
                doc.text(currentLine.replace('## ', ''), margin, y);
                y += lineHeight * 1.5;
            } else if (currentLine.startsWith('# ')) {
                doc.setFont("helvetica", "bold");
                doc.setFontSize(18);
                doc.text(currentLine.replace('# ', ''), margin, y);
                y += lineHeight * 1.5;
            }
            // Handle List Items (bulleted or numbered)
            else if (currentLine.match(/^[*-]\s/)) { // Bulleted list item
                doc.setFont("helvetica", "bold"); // Make bold
                doc.setFontSize(12);
                const cleanedLine = currentLine.replace(/^[*-]\s*\*\*?/, '').replace(/\*\*$/, ''); // Remove bullet/asterisk and bold markers
                const splitText = doc.splitTextToSize(cleanedLine, contentWidth - 5);
                splitText.forEach(l => {
                    addPageIfNeeded();
                    doc.text(l, margin + 5, y);
                    y += lineHeight;
                });
            } else if (currentLine.match(/^\d+\.\s/)) { // Numbered list item
                doc.setFont("helvetica", "bold"); // Make bold
                doc.setFontSize(12);
                const cleanedLine = currentLine.replace(/^\d+\.\s*\*\*?/, '').replace(/\*\*$/, ''); // Remove number/dot and bold markers
                const splitText = doc.splitTextToSize(cleanedLine, contentWidth - 5);
                splitText.forEach(l => {
                    addPageIfNeeded();
                    doc.text(l, margin + 5, y);
                    y += lineHeight;
                });
            }
            // Handle Horizontal Rule
            else if (currentLine === '---') {
                doc.setDrawColor(0); // Black color
                doc.line(margin, y + lineHeight / 2, doc.internal.pageSize.getWidth() - margin, y + lineHeight / 2);
                y += lineHeight;
            }
            // Handle Empty Lines
            else if (currentLine === '') {
                y += lineHeight * 0.5;
            }
            // Handle Paragraphs
            else {
                doc.setFont("helvetica", "normal");
                doc.setFontSize(12);
                // Remove any remaining bold markers from paragraphs if they exist
                const cleanedLine = currentLine.replace(/\*\*(.*?)\*\*/g, '$1');
                const splitText = doc.splitTextToSize(cleanedLine, contentWidth);
                splitText.forEach(l => {
                    addPageIfNeeded();
                    doc.text(l, margin, y);
                    y += lineHeight;
                });
            }
        });

        doc.save(`investigation-${investigationId}.pdf`);
    };

    return (
        <div className="page-content text-green-500 border-b p-5">
            {isLoading && <p>Loading...</p>}
            {error && <p className="error-message">{error}</p>}
            {investigation && (
                <div>
                    <div className="flex justify-between items-center mb-4">
                        <h1 className="font-bold text-2xl">{investigation.query.replace("investigation: ", "")}</h1>
                        <button onClick={handleExportToPdf} className="view-link">
                            Export to PDF
                        </button>
                    </div>
                    <div className="p-5 bg-gray-900 text-white">
                        <p className="text-sm text-gray-400 mb-4">Created at: {new Date(investigation.created_at).toLocaleString()}</p>
                        <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                                h1: ({node, ...props}) => <h1 className="text-xl font-bold my-4" {...props} />,
                                h2: ({node, ...props}) => <h2 className="text-lg font-bold my-3" {...props} />,
                                h3: ({node, ...props}) => <h3 className="text-md font-bold my-2" {...props} />,
                                p: ({node, ...props}) => <p className="my-2" {...props} />,
                                ul: ({node, ...props}) => <ul className="list-disc list-inside my-2" {...props} />,
                                li: ({node, ...props}) => <li className="ml-4" {...props} />,
                            }}
                        >
                            {investigation.result}
                        </ReactMarkdown>
                    </div>
                </div>
            )}
        </div>
    );
};

export default InvestigationDetailPage;
