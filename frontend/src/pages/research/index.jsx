import React, { useState } from "react";
import { researchByDate } from "../../api/apiService";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useOutletContext } from "react-router-dom";

const ResearchPage = () => {
    const { selectedOllamaServer, selectedModel } = useOutletContext();
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState(null);
    const [error, setError] = useState("");

    const handleSubmit = async (e) => {
        console.log("research submit is triggered!")
        e.preventDefault();
        console.log("startDate before validation:", startDate);
        console.log("endDate before validation:", endDate);
        console.log("selectedOllamaServer before validation:", selectedOllamaServer);
        console.log("selectedModel before validation:", selectedModel);
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
            if (selectedOllamaServer?.name) {
                formData.append("server_name", selectedOllamaServer.name);
            }
            if (selectedModel) {
                formData.append("model_name", selectedModel);
            }
            if (selectedOllamaServer?.type) {
                console.log("selectedOllamaServer.type before append:", selectedOllamaServer.type);
                formData.append("server_type", selectedOllamaServer.type);
            }
            for (let [key, value] of formData.entries()) {
                console.log(`${key}: ${value}`);
            }
            const result = await researchByDate(formData);
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
            <h1 className="text-2xl font-bold mb-4">Cybersecurity Research</h1>
            <p className="text-gray-300 mb-6">Select a date range to search for cybersecurity threats and risks.</p>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="prompt-area">
                    <label htmlFor="startDate" className="block text-lg font-medium text-white mb-2">Start Date</label>
                    <input
                        type="date"
                        id="startDate"
                        className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/20 focus:ring-green-500 focus:border-green-500 outline-none"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                    />
                </div>
                <div className="prompt-area">
                    <label htmlFor="endDate" className="block text-lg font-medium text-white mb-2">End Date</label>
                    <input
                        type="date"
                        id="endDate"
                        className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/20 focus:ring-green-500 focus:border-green-500 outline-none"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                    />
                </div>

                <button
                    type="submit"
                    className="w-full px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isLoading || !startDate || !endDate || !selectedOllamaServer}
                >
                    {isLoading ? "Researching..." : "Start Research"}
                </button>
            </form>

            {error && <div className="error-message text-red-500 mt-4">{error}</div>}

            {response && response.result && (
                <div className="response-area mt-4 p-4 bg-gray-800 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-white mb-2">Research Results</h3>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-invert max-w-none">
                        {response.result}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

export default ResearchPage;
