import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getAllLocalStorageJobs, deleteLocalStorageJob } from "../../api/apiService";
import '../../PdfProfessor.css'; // Import the CSS for status chips

const LocalStorageHistoryPage = () => {
  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchJobs = async () => {
    try {
      const data = await getAllLocalStorageJobs();
      setJobs(data);
    } catch (err) {
      setError("Failed to fetch job statuses.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs(); // Fetch on initial load
    const intervalId = setInterval(fetchJobs, 5000); // Poll every 5 seconds

    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

  const handleDelete = async (jobId) => {
    if (!window.confirm(`Are you sure you want to delete the job: ${jobId}?`)) {
        return;
    }

    try {
        await deleteLocalStorageJob(jobId);
        setJobs(currentJobs => currentJobs.filter(job => job.job_id !== jobId));
    } catch (err) {
        const errorMessage = err.response?.data?.detail || "Failed to delete the job.";
        setError(errorMessage);
    }
  };

  const getStatusChip = (status) => {
    return <span className={`status-chip ${status}`}>{status}</span>;
  };

  return (
    <div className="page-content">
      <h1>LocalStorage Query History</h1>
      <button
        onClick={() => { setIsLoading(true); fetchJobs(); }}
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Job ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Model</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Processing Time (s)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Prompt</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Files</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Last Updated</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="bg-gray-800 divide-y divide-gray-700">
            {jobs.length > 0 ? (
              jobs.map((job) => (
                <tr key={job.job_id} className="hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-400">
                    <Link to={`/local-storage/result/${job.job_id}`}>{job.job_id}</Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{getStatusChip(job.status)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{job.server_name ? `${job.server_name} (${job.model_name || 'N/A'})` : (job.model_name || 'N/A')} ({job.server_type || 'N/A'})</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{job.processing_time_seconds ? `${job.processing_time_seconds} sec` : 'N/A'}</td>
                  <td className="px-6 py-4 text-sm text-gray-200 prompt-cell max-w-[300px] overflow-ellipsis">{job.prompt}</td>
                  <td className="px-6 py-4 text-sm text-gray-200 prompt-cell max-w-[300px] overflow-ellipsis">{job.filenames.join(', ')}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-200">{new Date(job.updated_at).toLocaleString()}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex justify-center items-center space-x-3 h-full">
                      {job.status === "completed" && (
                        <Link
                          to={`/local-storage/result/${job.job_id}`}
                          className="px-3 py-1 border border-indigo-400 text-indigo-400 rounded-md hover:bg-indigo-500 hover:text-white transition-colors duration-200"
                        >
                          View
                        </Link>
                      )}
                      <button
                          onClick={() => handleDelete(job.job_id)}
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
                <td colSpan="8" className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-400">
                  No query history found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LocalStorageHistoryPage;
