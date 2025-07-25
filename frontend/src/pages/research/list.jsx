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
        <div className="page-content">
            <h1>Research List</h1>
            <button
                onClick={fetchResearchList}
                disabled={isLoading}
                className="refresh-btn mt-5 border border-green-500 p-2 text-green-50"
                style={{backgroundColor: 'transparent' , color: 'green' , border: '2px solid green'}}
            >
                {isLoading ? "Refreshing..." : "Refresh Now"}
            </button>
            {error && <div className="error-message">{error}</div>}

            <div className="task-table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Query</th>
                            <th>Created At</th>
                            <th>Generation Time</th>
                            <th>Ollama Server (Model)</th>
                            <th style={{textAlign:'center'}}>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {researchList.length > 0 ? (
                            researchList.map((research) => (
                                <tr key={research.id}>
                                    <td>{research.id}</td>
                                    <td className="prompt-cell">{research.query}</td>
                                    <td>{new Date(research.created_at).toLocaleString()}</td>
                                    <td>{research.generation_time ? `${research.generation_time.toFixed(2)} seconds` : 'N/A'}</td>
                                    <td>{research.ollama_server_name ? `${research.ollama_server_name} (${research.ollama_model || 'N/A'})` : 'N/A'}</td>
                                    <td className="action-cell flex gap-3 " style={{padding: '2rem'}}>
                                        <Link
                                            to={`/research/${research.id}`}
                                            className="view-link"
                                        >
                                            View
                                        </Link>
                                        <button
                                            onClick={() => handleDelete(research.id)}
                                            className="view-link"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="6">
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