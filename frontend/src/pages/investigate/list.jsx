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
        <div className="page-content">
            <h1>Investigation List</h1>
            <button
                onClick={fetchInvestigations}
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
                        {investigations.length > 0 ? (
                            investigations.map((investigation) => (
                                <tr key={investigation.id}>
                                    <td>{investigation.id}</td>
                                    <td className="prompt-cell">{investigation.query.replace("investigation: ", "")}</td>
                                    <td>{new Date(investigation.created_at).toLocaleString()}</td>
                                    <td>{investigation.generation_time ? `${investigation.generation_time.toFixed(2)} seconds` : 'N/A'}</td>
                                    <td>{investigation.ollama_server_name ? `${investigation.ollama_server_name} (${investigation.ollama_model || 'N/A'})` : 'N/A'}</td>
                                    <td className="action-cell flex gap-3 " style={{padding: '2rem'}}>
                                        <Link
                                            to={`/investigate/${investigation.id}`}
                                            className="view-link"
                                        >
                                            View
                                        </Link>
                                        <button
                                            onClick={() => handleDelete(investigation.id)}
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
