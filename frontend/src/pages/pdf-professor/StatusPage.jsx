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
        className="mb-4 px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white transition-colors duration-200"
      >
        {isLoading ? "Refreshing..." : "Refresh Now"}
      </button>
      {error && <div className="error-message text-red-500 mb-4">{error}</div>}

      <div className="task-table-container overflow-x-auto bg-gray-800 rounded-lg shadow-lg">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Task ID (Filename)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Model</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Processing Time (s)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Prompt</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Last Updated</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="bg-gray-800 divide-y divide-gray-700">
            {tasks.length > 0 ? (
              tasks.map((task) => (
                <tr key={task.task_id} className="hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-400">{task.task_id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{getStatusChip(task.status)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{task.ollama_server_name ? `${task.ollama_server_name} (${task.ollama_model || 'N/A'})` : (task.ollama_model || 'N/A')}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{task.processing_time_seconds +" sec" ?? 'N/A'}</td>
                  <td className="px-6 py-4 text-sm text-gray-200 prompt-cell max-w-[400px] max-h-[100px] overflow-ellipsis">{task.prompt}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{new Date(task.updated_at).toLocaleString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex justify-center items-center space-x-3 h-full">
                      {task.status === "completed" && (
                        <Link
                          to={`/task-status/${task.task_id}`}
                          className="px-3 py-1 border border-indigo-400 text-indigo-400 rounded-md hover:bg-indigo-500 hover:text-white transition-colors duration-200"
                        >
                          View
                        </Link>
                      )}
                      <button
                          onClick={() => handleDelete(task.task_id)}
                          className="px-3 py-1 border border-red-400 text-red-400 rounded-md hover:bg-red-500 hover:text-white transition-colors duration-200"
                      >
                          Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="7" className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-400">
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