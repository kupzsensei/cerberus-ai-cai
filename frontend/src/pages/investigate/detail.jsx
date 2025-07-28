import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { getResearchById } from "../../api/apiService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

    return (
        <div className="page-content text-green-500 border-b p-5">
            {isLoading && <p>Loading...</p>}
            {error && <p className="error-message">{error}</p>}
            {investigation && (
                <div>
                    <h1 className="font-bold">{investigation.query.replace("investigation: ", "")}</h1>
                    <p>Created at: {new Date(investigation.created_at).toLocaleString()}</p>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {investigation.result}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default InvestigationDetailPage;
