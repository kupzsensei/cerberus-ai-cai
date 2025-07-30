import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getResearchList, deleteResearchById } from "../../api/apiService";

const ResearchListPage = () => {
    const [researchList, setResearchList] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState("");

    const fetchResearchList = async () => {
        try {
            const data = await getResearchList();
            setResearchList(data);
        } catch (err) {
            setError("Failed to fetch research list.");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchResearchList();
    }, []);

    const handleDelete = async (researchId) => {
        if (!window.confirm(`Are you sure you want to delete research ID: ${researchId}?`)) {
            return;
        }

        try {
            await deleteResearchById(researchId);
            setResearchList(currentList => currentList.filter(item => item.id !== researchId));
        } catch (err) {
            const errorMessage = err.response?.data?.detail || "Failed to delete the research entry.";
            setError(errorMessage);
        }
    };

    return (
        <div className="page-content p-5">
            <h1 className="text-2xl font-bold mb-4">Research List</h1>
            <button
                onClick={fetchResearchList}
                disabled={isLoading}
                className="mb-4 px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white transition-colors duration-200"
            >
                {isLoading ? "Refreshing..." : "Refresh Now"}
            </button>
            {error && <div className="error-message text-red-500 mb-4">{error}</div>}

            <div className="task-table-container overflow-x-auto bg-gray-800 rounded-lg shadow-lg">
                <table className="min-w-full divide-y divide-gray-700">
                    <thead className="bg-gray-700">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">ID</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Query</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Created At</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Generation Time</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Ollama Server (Model)</th>
                            <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">Action</th>
                        </tr>
                    </thead>
                    <tbody className="bg-gray-800 divide-y divide-gray-700">
                        {researchList.length > 0 ? (
                            researchList.map((research) => (
                                <tr key={research.id} className="hover:bg-gray-700">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-400">{research.id}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200 prompt-cell">{research.query}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{new Date(research.created_at).toLocaleString()}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{research.generation_time ? `${research.generation_time.toFixed(2)} seconds` : 'N/A'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{research.ollama_server_name ? `${research.ollama_server_name} (${research.ollama_model || 'N/A'})` : 'N/A'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium flex justify-center items-center space-x-3">
                                        <Link
                                            to={`/research/${research.id}`}
                                            className="px-3 py-1 border border-indigo-400 text-indigo-400 rounded-md hover:bg-indigo-500 hover:text-white transition-colors duration-200"
                                        >
                                            View
                                        </Link>
                                        <button
                                            onClick={() => handleDelete(research.id)}
                                            className="px-3 py-1 border border-red-400 text-red-400 rounded-md hover:bg-red-500 hover:text-white transition-colors duration-200"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="6" className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-400">
                                    No research found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ResearchListPage;