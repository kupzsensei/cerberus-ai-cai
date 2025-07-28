import React, { useState } from "react";
import { investigate } from "../../api/apiService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useOutletContext } from "react-router-dom";

const InvestigatePage = () => {
    const { selectedOllamaServer, selectedModel, handleModelChange } = useOutletContext();
    const [query, setQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState(null);
    const [error, setError] = useState("");

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!query) {
            setError("Please enter a query.");
            return;
        }

        setIsLoading(true);
        setResponse(null);
        setError("");

        try {
            const result = await investigate(query, selectedOllamaServer?.name, selectedModel);
            console.log("API Result:", result);
            setResponse(result);
        } catch (err) {
            const errorMessage =
                err.response?.data?.detail ||
                err.message ||
                "An unknown error occurred.";
            setError(
                typeof errorMessage === "string"
                    ? errorMessage
                    : JSON.stringify(errorMessage)
            );
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="page-content text-green-500 border-b p-5">
            <h1 className="font-bold">Investigate</h1>
            <p>Enter a query to investigate an incident or company.</p>

            <form onSubmit={handleSubmit}>
                <div className="prompt-area">
                    <label htmlFor="query">Query</label>
                    <input
                        type="text"
                        id="query"
                        className="p-2 border border-green-600 rounded-md text-white bg-green-500/50"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                </div>

                <button
                    type="submit"
                    className="mt-5"
                    disabled={isLoading || !query || !selectedOllamaServer}
                >
                    {isLoading ? "Investigating..." : "Investigate"}
                </button>
            </form>

            {error && <div className="error-message">{error}</div>}

            {response && response.result && (
                <div className="response-area">
                    <h3>Investigation Results</h3>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {response.result}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default InvestigatePage;
