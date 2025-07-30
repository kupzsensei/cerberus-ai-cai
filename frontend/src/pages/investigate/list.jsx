import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getResearchList, deleteResearchById } from "../../api/apiService";

const InvestigationListPage = () => {
    const [investigations, setInvestigations] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState("");

    const fetchInvestigations = async () => {
        try {
            const researchList = await getResearchList();
            const investigationList = researchList.filter(item => item.query.startsWith("investigation: "));
            setInvestigations(investigationList);
        } catch (err) {
            setError("Failed to fetch investigations.");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchInvestigations();
    }, []);

    const handleDelete = async (id) => {
        if (!window.confirm(`Are you sure you want to delete investigation ID: ${id}?`)) {
            return;
        }

        try {
            await deleteResearchById(id);
            setInvestigations(currentList => currentList.filter(item => item.id !== id));
        } catch (err) {
            const errorMessage = err.response?.data?.detail || "Failed to delete the investigation entry.";
            setError(errorMessage);
        }
    };

    return (
        <div className="page-content p-5">
            <h1 className="text-2xl font-bold mb-4">Investigation List</h1>
            <button
                onClick={fetchInvestigations}
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
                        {investigations.length > 0 ? (
                            investigations.map((investigation) => (
                                <tr key={investigation.id} className="hover:bg-gray-700">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-400">{investigation.id}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200 prompt-cell">{investigation.query.replace("investigation: ", "")}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{new Date(investigation.created_at).toLocaleString()}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{investigation.generation_time ? `${investigation.generation_time.toFixed(2)} seconds` : 'N/A'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{investigation.ollama_server_name ? `${investigation.ollama_server_name} (${investigation.ollama_model || 'N/A'})` : 'N/A'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium flex justify-center items-center space-x-3">
                                        <Link
                                            to={`/investigate/${investigation.id}`}
                                            className="px-3 py-1 border border-indigo-400 text-indigo-400 rounded-md hover:bg-indigo-500 hover:text-white transition-colors duration-200"
                                        >
                                            View
                                        </Link>
                                        <button
                                            onClick={() => handleDelete(investigation.id)}
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
                                    No investigations found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default InvestigationListPage;
