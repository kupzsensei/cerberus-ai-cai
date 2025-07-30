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
        <div className="page-content p-5">
            <h1 className="text-2xl font-bold mb-4">Investigate</h1>
            <p className="text-gray-300 mb-6">Enter a query to investigate an incident or company.</p>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="prompt-area">
                    <label htmlFor="query" className="block text-lg font-medium text-white mb-2">Query</label>
                    <input
                        type="text"
                        id="query"
                        className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/20 focus:ring-green-500 focus:border-green-500 outline-none"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                </div>

                <button
                    type="submit"
                    className="w-full px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isLoading || !query || !selectedOllamaServer}
                >
                    {isLoading ? "Investigating..." : "Investigate"}
                </button>
            </form>

            {error && <div className="error-message text-red-500 mt-4">{error}</div>}

            {response && response.result && (
                <div className="response-area mt-4 p-4 bg-gray-800 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-white mb-2">Investigation Results</h3>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-invert max-w-none">
                        {response.result}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default InvestigatePage;
