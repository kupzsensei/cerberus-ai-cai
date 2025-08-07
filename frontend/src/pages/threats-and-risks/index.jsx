import React, { useState } from "react";
import { researchByDate } from "../../api/apiService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useOutletContext } from "react-router-dom";

const ThreatsAndRisksPage = () => {
    const { selectedOllamaServer, selectedModel, handleModelChange } = useOutletContext();
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState(null);
    const [error, setError] = useState("");

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!startDate || !endDate) {
            setError("Please select both start and end dates.");
            return;
        }

        setIsLoading(true);
        setResponse(null);
        setError("");

        try {
            const query = `cybersecurity incidents in Australia from ${startDate} to ${endDate}`;
            const result = await researchByDate(query, selectedOllamaServer?.name, selectedModel , selectedOllamaServer?.type);
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
            <h1 className="font-bold">Threats and Risks</h1>
            <p>Select a date range to search for cybersecurity threats and risks.</p>

            <form onSubmit={handleSubmit}>
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

                <button
                    type="submit"
                    className="mt-5"
                    disabled={isLoading || !startDate || !endDate || !selectedOllamaServer}
                >
                    {isLoading ? "Researching..." : "Start Research"}
                </button>
            </form>

            {error && <div className="error-message">{error}</div>}

            {response && response.result && (
                <div className="response-area">
                    <h3>Research Results</h3>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {response.result}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default ThreatsAndRisksPage;
