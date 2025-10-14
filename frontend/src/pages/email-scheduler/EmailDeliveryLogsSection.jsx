import React, { useState, useEffect } from "react";
import { getEmailDeliveryLogs } from "../../api/apiService";

const EmailDeliveryLogsSection = ({ scheduledResearch }) => {
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [filterResearchId, setFilterResearchId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load logs on component mount
  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await getEmailDeliveryLogs();
      setLogs(data);
      setFilteredLogs(data);
      setError(null);
    } catch (err) {
      console.error("Error loading email delivery logs:", err);
      setError("Failed to load email delivery logs: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Filter logs when research ID filter changes
  useEffect(() => {
    if (filterResearchId) {
      setFilteredLogs(logs.filter(log => log.scheduled_research_id === parseInt(filterResearchId)));
    } else {
      setFilteredLogs(logs);
    }
  }, [filterResearchId, logs]);

  const getResearchName = (researchId) => {
    const research = scheduledResearch.find(r => r.id === researchId);
    return research ? research.name : `Research #${researchId}`;
  };

  const formatRecipients = (recipients) => {
    if (!recipients || recipients.length === 0) return "None";
    if (recipients.length === 1) return recipients[0];
    return `${recipients[0]} and ${recipients.length - 1} others`;
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      "sent": "bg-green-800/50",
      "failed": "bg-red-800/50"
    };
    
    return (
      <span className={`px-2 py-1 rounded text-xs ${statusClasses[status] || "bg-gray-800/50"}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Email Delivery Logs</h2>
        <button
          className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
          onClick={loadLogs}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh Logs"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded p-4 mb-4">
          <p className="text-red-300">{error}</p>
        </div>
      )}

      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Filter by Scheduled Research</label>
        <select
          value={filterResearchId}
          onChange={(e) => setFilterResearchId(e.target.value)}
          className="w-full md:w-64 p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
        >
          <option value="">All Research</option>
          {scheduledResearch.map(research => (
            <option key={research.id} value={research.id}>{research.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <p>Loading email delivery logs...</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-green-900/30 border border-green-700">
            <thead>
              <tr className="bg-green-800/50">
                <th className="py-2 px-4 text-left">Research</th>
                <th className="py-2 px-4 text-left">Subject</th>
                <th className="py-2 px-4 text-left">Recipients</th>
                <th className="py-2 px-4 text-left">Date Range</th>
                <th className="py-2 px-4 text-left">Status</th>
                <th className="py-2 px-4 text-left">Sent At</th>
                <th className="py-2 px-4 text-left">Error</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id} className="border-t border-green-700 hover:bg-green-800/30">
                  <td className="py-2 px-4">{getResearchName(log.scheduled_research_id)}</td>
                  <td className="py-2 px-4 max-w-xs truncate">{log.subject}</td>
                  <td className="py-2 px-4 max-w-xs truncate" title={log.recipients?.join(", ")}>
                    {formatRecipients(log.recipients)}
                  </td>
                  <td className="py-2 px-4">
                    {log.date_range_start && log.date_range_end 
                      ? `${log.date_range_start} to ${log.date_range_end}`
                      : "N/A"}
                  </td>
                  <td className="py-2 px-4">{getStatusBadge(log.status)}</td>
                  <td className="py-2 px-4">
                    {log.sent_at ? new Date(log.sent_at).toLocaleString() : "N/A"}
                  </td>
                  <td className="py-2 px-4 max-w-xs truncate" title={log.error_message}>
                    {log.error_message || "-"}
                  </td>
                </tr>
              ))}
              {filteredLogs.length === 0 && (
                <tr>
                  <td colSpan="7" className="py-4 px-4 text-center">
                    No email delivery logs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default EmailDeliveryLogsSection;