import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getStatus, deleteTaskById } from "../../api/apiService"; // <-- Import deleteTaskById
import '../../PdfProfessor.css'


const StatusPage = () => {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStatus = async () => {
    try {
      const data = await getStatus();
      setTasks(data);
    } catch (err) {
      setError("Failed to fetch task statuses.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus(); // Fetch on initial load
    const intervalId = setInterval(fetchStatus, 5000); // Poll every 5 seconds

    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

  const handleDelete = async (taskId) => {
    // Add a confirmation dialog for safety
    if (!window.confirm(`Are you sure you want to delete the task: ${taskId}?`)) {
        return;
    }

    try {
        await deleteTaskById(taskId);
        // If successful, remove the task from the local state to update the UI
        setTasks(currentTasks => currentTasks.filter(task => task.task_id !== taskId));
    } catch (err) {
        const errorMessage = err.response?.data?.detail || "Failed to delete the task.";
        setError(errorMessage); // Show an error if deletion fails
    }
  };

  const getStatusChip = (status) => {
    return <span className={`status-chip ${status}`}>{status}</span>;
  };

  return (
    <div className="page-content">
      <h1>Background Task Status</h1>
      <button
        onClick={fetchStatus}
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
              <th>Task ID (Filename)</th>
              <th>Status</th>
              <th>Model</th>
              <th>Processing Time (s)</th>
              <th>Prompt</th>
              <th>Last Updated</th>
              <th style={{textAlign:'center'}}>Action</th>
            </tr>
          </thead>
          <tbody>
            {tasks.length > 0 ? (
              tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>{task.task_id}</td>
                  <td>{getStatusChip(task.status)}</td>
                  <td>{task.ollama_server_name ? `${task.ollama_server_name} (${task.ollama_model || 'N/A'})` : (task.ollama_model || 'N/A')}</td>
                  <td>{task.processing_time_seconds +" sec" ?? 'N/A'}</td>
                  <td className="prompt-cell">{task.prompt}</td>
                  <td>{new Date(task.updated_at).toLocaleString()}</td>
                  <td className="action-cell flex gap-3 " style={{padding: '2rem'}}>
                    {task.status === "completed" && (
                      <Link
                        to={`/task-status/${task.task_id}`}
                        className="view-link"
                      >
                        View
                      </Link>
                    )}
                     <button
                        onClick={() => handleDelete(task.task_id)}
                        className="view-link"
                     >
                        Delete
                     </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="7">
                  No background tasks found. Upload a file to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StatusPage;