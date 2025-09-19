import React, { useState, useEffect } from "react";
import { addScheduledResearch, updateScheduledResearch, deleteScheduledResearch, getOllamaServers, getExternalAIServers, getOllamaModels, getExternalAIModels } from "../../api/apiService";

const ScheduledResearchSection = ({ scheduledResearch, recipientGroups, emailConfigs, onRefresh }) => {
  const [isAdding, setIsAdding] = useState(false);
  const [editingResearch, setEditingResearch] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    frequency: "daily",
    day_of_week: 0,
    day_of_month: 1,
    hour: 9,
    minute: 0,
    start_date: "",
    end_date: "",
    is_active: true,
    recipient_group_id: "",
    date_range_days: 7,
    model_name: "",
    server_name: "",
    server_type: "ollama"
  });
  
  // State for available servers and models
  const [availableServers, setAvailableServers] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Fetch available servers
  useEffect(() => {
    const fetchServers = async () => {
      try {
        const ollamaServers = await getOllamaServers();
        const externalServers = await getExternalAIServers();
        const allServers = [
          ...ollamaServers.map(s => ({ ...s, type: "ollama" })),
          ...externalServers.map(s => ({ ...s, type: "gemini" }))
        ];
        setAvailableServers(allServers);
      } catch (error) {
        console.error("Error fetching servers:", error);
      }
    };
    
    fetchServers();
  }, []);

  // Fetch models when server type or server name changes
  useEffect(() => {
    const fetchModels = async () => {
      if (!formData.server_type || !formData.server_name) {
        setAvailableModels([]);
        return;
      }
      
      setLoadingModels(true);
      try {
        let models = [];
        if (formData.server_type === "ollama") {
          const server = availableServers.find(s => s.name === formData.server_name && s.type === "ollama");
          if (server) {
            models = await getOllamaModels(server.url);
          }
        } else if (formData.server_type === "gemini") {
          models = await getExternalAIModels(formData.server_type);
        }
        setAvailableModels(models);
        
        // Reset model name if it's not in the new list
        if (formData.model_name && !models.includes(formData.model_name)) {
          setFormData(prev => ({ ...prev, model_name: "" }));
        }
      } catch (error) {
        console.error("Error fetching models:", error);
        setAvailableModels([]);
      } finally {
        setLoadingModels(false);
      }
    };
    
    fetchModels();
  }, [formData.server_type, formData.server_name, availableServers]);

  const handleAddNew = () => {
    setIsAdding(true);
    setEditingResearch(null);
    setFormData({
      name: "",
      description: "",
      frequency: "daily",
      day_of_week: 0,
      day_of_month: 1,
      hour: 9,
      minute: 0,
      start_date: "",
      end_date: "",
      is_active: true,
      recipient_group_id: "",
      date_range_days: 7,
      model_name: "",
      server_name: "",
      server_type: "ollama"
    });
  };

  const handleEdit = (research) => {
    setEditingResearch(research);
    setIsAdding(false);
    setFormData({
      name: research.name || "",
      description: research.description || "",
      frequency: research.frequency || "daily",
      day_of_week: research.day_of_week !== null ? research.day_of_week : 0,
      day_of_month: research.day_of_month !== null ? research.day_of_month : 1,
      hour: research.hour || 9,
      minute: research.minute || 0,
      start_date: research.start_date || "",
      end_date: research.end_date || "",
      is_active: research.is_active !== undefined ? research.is_active : true,
      recipient_group_id: research.recipient_group_id || "",
      date_range_days: research.date_range_days || 7,
      model_name: research.model_name || "",
      server_name: research.server_name || "",
      server_type: research.server_type || "ollama"
    });
  };

  const handleDelete = async (researchId) => {
    if (window.confirm("Are you sure you want to delete this scheduled research configuration?")) {
      try {
        await deleteScheduledResearch(researchId);
        onRefresh();
      } catch (error) {
        console.error("Error deleting scheduled research:", error);
        alert("Failed to delete scheduled research: " + (error.response?.data?.detail || error.message));
      }
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    let newValue = type === "checkbox" ? checked : value;
    
    // Convert numeric values
    if (name === "day_of_week" || name === "day_of_month" || name === "hour" || 
        name === "minute" || name === "recipient_group_id" || name === "date_range_days") {
      newValue = value === "" ? "" : Number(value);
    }
    
    setFormData({
      ...formData,
      [name]: newValue
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const form = new FormData();
      
      // Add all form data
      Object.keys(formData).forEach(key => {
        // Skip conditional fields based on frequency
        if (key === "day_of_week" && formData.frequency !== "weekly") return;
        if (key === "day_of_month" && formData.frequency !== "monthly") return;
        
        // Handle boolean values
        if (key === "is_active") {
          form.append(key, formData[key] ? "true" : "false");
        } else {
          form.append(key, formData[key]);
        }
      });

      if (editingResearch) {
        await updateScheduledResearch(editingResearch.id, form);
      } else {
        await addScheduledResearch(form);
      }
      
      setIsAdding(false);
      setEditingResearch(null);
      onRefresh();
    } catch (error) {
      console.error("Error saving scheduled research:", error);
      alert("Failed to save scheduled research: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleCancel = () => {
    setIsAdding(false);
    setEditingResearch(null);
  };

  const formatFrequency = (frequency, dayOfWeek, dayOfMonth) => {
    switch (frequency) {
      case "daily":
        return "Daily";
      case "weekly":
        const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
        return `Weekly on ${days[dayOfWeek] || "Monday"}`;
      case "monthly":
        return `Monthly on day ${dayOfMonth}`;
      default:
        return frequency;
    }
  };

  const formatTime = (hour, minute) => {
    const h = hour < 10 ? `0${hour}` : hour;
    const m = minute < 10 ? `0${minute}` : minute;
    return `${h}:${m}`;
  };

  const getRecipientGroupName = (groupId) => {
    const group = recipientGroups.find(g => g.id === groupId);
    return group ? group.name : "Unknown Group";
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Scheduled Research</h2>
        <button
          className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
          onClick={handleAddNew}
        >
          Add New Schedule
        </button>
      </div>

      {(isAdding || editingResearch) && (
        <div className="bg-green-900/30 border border-green-700 rounded p-4 mb-6">
          <h3 className="text-lg font-bold mb-3">
            {editingResearch ? "Edit Scheduled Research" : "Add New Scheduled Research"}
          </h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name *</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <input
                  type="text"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Frequency *</label>
                <select
                  name="frequency"
                  value={formData.frequency}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              {formData.frequency === "weekly" && (
                <div>
                  <label className="block text-sm font-medium mb-1">Day of Week *</label>
                  <select
                    name="day_of_week"
                    value={formData.day_of_week}
                    onChange={handleChange}
                    className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                    required
                  >
                    <option value="0">Monday</option>
                    <option value="1">Tuesday</option>
                    <option value="2">Wednesday</option>
                    <option value="3">Thursday</option>
                    <option value="4">Friday</option>
                    <option value="5">Saturday</option>
                    <option value="6">Sunday</option>
                  </select>
                </div>
              )}
              {formData.frequency === "monthly" && (
                <div>
                  <label className="block text-sm font-medium mb-1">Day of Month *</label>
                  <input
                    type="number"
                    name="day_of_month"
                    min="1"
                    max="31"
                    value={formData.day_of_month}
                    onChange={handleChange}
                    className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                    required
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium mb-1">Time (Hour) *</label>
                <input
                  type="number"
                  name="hour"
                  min="0"
                  max="23"
                  value={formData.hour}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Time (Minute) *</label>
                <input
                  type="number"
                  name="minute"
                  min="0"
                  max="59"
                  value={formData.minute}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Date Range (Days) *</label>
                <input
                  type="number"
                  name="date_range_days"
                  min="1"
                  max="365"
                  value={formData.date_range_days}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                />
                <p className="text-xs text-green-300 mt-1">Number of days to look back for research</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Recipient Group *</label>
                <select
                  name="recipient_group_id"
                  value={formData.recipient_group_id}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                  required
                >
                  <option value="">Select a recipient group</option>
                  {recipientGroups.map(group => (
                    <option key={group.id} value={group.id}>{group.name}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  name="is_active"
                  checked={formData.is_active}
                  onChange={handleChange}
                  className="mr-2"
                />
                <label className="text-sm">Active</label>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Start Date</label>
                <input
                  type="date"
                  name="start_date"
                  value={formData.start_date}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">End Date</label>
                <input
                  type="date"
                  name="end_date"
                  value={formData.end_date}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Server Type</label>
                <select
                  name="server_type"
                  value={formData.server_type}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                >
                  <option value="ollama">Ollama</option>
                  <option value="gemini">Gemini</option>
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">Server Name</label>
                <select
                  name="server_name"
                  value={formData.server_name}
                  onChange={handleChange}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                >
                  <option value="">Select a server (optional)</option>
                  {availableServers
                    .filter(server => server.type === formData.server_type)
                    .map(server => (
                      <option key={server.name} value={server.name}>
                        {server.name}
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Model Name</label>
                <select
                  name="model_name"
                  value={formData.model_name}
                  onChange={handleChange}
                  disabled={loadingModels}
                  className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
                >
                  <option value="">Select a model (optional)</option>
                  {loadingModels ? (
                    <option>Loading models...</option>
                  ) : (
                    availableModels.map(model => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            <div className="flex space-x-2">
              <button
                type="submit"
                className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded"
              >
                {editingResearch ? "Update Schedule" : "Add Schedule"}
              </button>
              <button
                type="button"
                className="bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded"
                onClick={handleCancel}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full bg-green-900/30 border border-green-700">
          <thead>
            <tr className="bg-green-800/50">
              <th className="py-2 px-4 text-left">Name</th>
              <th className="py-2 px-4 text-left">Frequency</th>
              <th className="py-2 px-4 text-left">Time</th>
              <th className="py-2 px-4 text-left">Recipients</th>
              <th className="py-2 px-4 text-left">Date Range</th>
              <th className="py-2 px-4 text-left">Status</th>
              <th className="py-2 px-4 text-left">Last Run</th>
              <th className="py-2 px-4 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {scheduledResearch.map((research) => (
              <tr key={research.id} className="border-t border-green-700 hover:bg-green-800/30">
                <td className="py-2 px-4">
                  <div className="font-medium">{research.name}</div>
                  {research.description && (
                    <div className="text-sm text-green-300">{research.description}</div>
                  )}
                </td>
                <td className="py-2 px-4">{formatFrequency(research.frequency, research.day_of_week, research.day_of_month)}</td>
                <td className="py-2 px-4">{formatTime(research.hour, research.minute)}</td>
                <td className="py-2 px-4">{getRecipientGroupName(research.recipient_group_id)}</td>
                <td className="py-2 px-4">{research.date_range_days} days</td>
                <td className="py-2 px-4">
                  <span className={`px-2 py-1 rounded text-xs ${research.is_active ? 'bg-green-800/50' : 'bg-red-800/50'}`}>
                    {research.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="py-2 px-4">
                  {research.last_run ? new Date(research.last_run).toLocaleString() : 'Never'}
                </td>
                <td className="py-2 px-4">
                  <button
                    className="text-blue-400 hover:text-blue-300 mr-2"
                    onClick={() => handleEdit(research)}
                  >
                    Edit
                  </button>
                  <button
                    className="text-red-400 hover:text-red-300"
                    onClick={() => handleDelete(research.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {scheduledResearch.length === 0 && (
              <tr>
                <td colSpan="8" className="py-4 px-4 text-center">
                  No scheduled research configurations found. Add a new schedule to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ScheduledResearchSection;