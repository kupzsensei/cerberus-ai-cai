import React, { useState, useEffect } from "react";
import { 
  testScheduledResearch,
  getEmailConfigs,
  getEmailRecipientGroups,
  getOllamaServers,
  getExternalAIServers,
  getOllamaModels,
  getExternalAIModels
} from "../../api/apiService";

const TestSection = () => {
  const [testData, setTestData] = useState({
    name: "Test Research",
    description: "Immediate test of email scheduling functionality",
    recipient_group_id: "",
    date_range_days: 7,
    model_name: "",
    server_name: "",
    server_type: "ollama",
    test_email: "", // For sending test to a specific email instead of group
    email_config_id: ""  // New field
  });
  
  const [emailConfigs, setEmailConfigs] = useState([]);
  const [recipientGroups, setRecipientGroups] = useState([]);
  const [availableServers, setAvailableServers] = useState([]);
  const [availableModels, setAvailableModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [taskId, setTaskId] = useState(null);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [configs, groups, ollamaServers, externalServers] = await Promise.all([
          getEmailConfigs(),
          getEmailRecipientGroups(),
          getOllamaServers(),
          getExternalAIServers()
        ]);
        
        setEmailConfigs(configs);
        setRecipientGroups(groups);
        
        // Combine all servers
        const allServers = [
          ...ollamaServers.map(s => ({ ...s, type: "ollama" })),
          ...externalServers.map(s => ({ ...s, type: "gemini" }))
        ];
        setAvailableServers(allServers);
      } catch (error) {
        console.error("Error fetching initial data:", error);
        setMessage("Error loading data: " + error.message);
      }
    };
    
    fetchData();
  }, []);

  // Fetch models when server type or server name changes
  useEffect(() => {
    const fetchModels = async () => {
      if (!testData.server_type || !testData.server_name) {
        setAvailableModels([]);
        return;
      }
      
      setLoadingModels(true);
      try {
        let models = [];
        if (testData.server_type === "ollama") {
          const server = availableServers.find(s => s.name === testData.server_name && s.type === "ollama");
          if (server) {
            models = await getOllamaModels(server.url);
          }
        } else if (testData.server_type === "gemini") {
          models = await getExternalAIModels(testData.server_type);
        }
        setAvailableModels(models);
        
        // Reset model name if it's not in the new list
        if (testData.model_name && !models.includes(testData.model_name)) {
          setTestData(prev => ({ ...prev, model_name: "" }));
        }
      } catch (error) {
        console.error("Error fetching models:", error);
        setAvailableModels([]);
      } finally {
        setLoadingModels(false);
      }
    };
    
    fetchModels();
  }, [testData.server_type, testData.server_name, availableServers]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setTestData({
      ...testData,
      [name]: type === "checkbox" ? checked : value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    
    try {
      const formData = new FormData();
      
      // Add all form data
      Object.keys(testData).forEach(key => {
        // Handle boolean values
        if (key === "is_active") {
          formData.append(key, testData[key] ? "true" : "false");
        } else {
          formData.append(key, testData[key]);
        }
      });

      const result = await testScheduledResearch(formData);
      
      // The new API returns a task ID instead of immediate success/failure
      if (result.task_id) {
        setMessage("Test started successfully! Task ID: " + result.task_id + ". Check the delivery logs for status updates.");
        setTaskId(result.task_id);
      } else {
        setMessage("Test failed: Unexpected response format");
      }
    } catch (error) {
      console.error("Error testing scheduled research:", error);
      setMessage("Test failed: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-bold mb-2">Test Email Scheduler</h2>
        <p className="text-green-300">
          This allows you to immediately test your email configuration and research functionality.
          The test will perform research and send an email right away, without waiting for the schedule.
        </p>
      </div>

      {message && (
        <div className={`p-4 mb-4 rounded ${message.includes("failed") || message.includes("Error") ? "bg-red-900/50 text-red-200" : "bg-green-900/50 text-green-200"}`}>
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-green-900/30 border border-green-700 rounded p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Test Name *</label>
            <input
              type="text"
              name="name"
              value={testData.name}
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
              value={testData.description}
              onChange={handleChange}
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Date Range (Days) *</label>
            <input
              type="number"
              name="date_range_days"
              min="1"
              max="365"
              value={testData.date_range_days}
              onChange={handleChange}
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
              required
            />
            <p className="text-xs text-green-300 mt-1">Number of days to look back for research</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Test Email (Optional)</label>
            <input
              type="email"
              name="test_email"
              value={testData.test_email}
              onChange={handleChange}
              placeholder="Leave blank to use recipient group"
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            />
            <p className="text-xs text-green-300 mt-1">If provided, sends test to this email instead of group</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Server Type</label>
            <select
              name="server_type"
              value={testData.server_type}
              onChange={handleChange}
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            >
              <option value="ollama">Ollama</option>
              <option value="gemini">Gemini</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Server Name</label>
            <select
              name="server_name"
              value={testData.server_name}
              onChange={handleChange}
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            >
              <option value="">Select a server</option>
              {availableServers
                .filter(server => server.type === testData.server_type)
                .map(server => (
                  <option key={server.name} value={server.name}>
                    {server.name}
                  </option>
                ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email Configuration</label>
            <select
              name="email_config_id"
              value={testData.email_config_id}
              onChange={handleChange}
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            >
              <option value="">Use default email configuration</option>
              {emailConfigs.map(config => (
                <option key={config.id} value={config.id}>
                  {config.smtp_server}:{config.smtp_port} ({config.username})
                </option>
              ))}
            </select>
            <p className="text-xs text-green-300 mt-1">Select specific email configuration for this test</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Model Name</label>
            <select
              name="model_name"
              value={testData.model_name}
              onChange={handleChange}
              disabled={loadingModels}
              className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            >
              <option value="">Select a model</option>
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

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Recipient Group (Required if Test Email not provided)</label>
          <select
            name="recipient_group_id"
            value={testData.recipient_group_id}
            onChange={handleChange}
            className="w-full p-2 border border-green-600 rounded-md bg-green-900/50 text-white"
            required={!testData.test_email}
          >
            <option value="">Select a recipient group</option>
            {recipientGroups.map(group => (
              <option key={group.id} value={group.id}>{group.name}</option>
            ))}
          </select>
          {!testData.test_email && (
            <p className="text-xs text-red-300 mt-1">Either select a recipient group or provide a test email address</p>
          )}
        </div>

        <div className="flex space-x-2">
          <button
            type="submit"
            disabled={loading}
            className="bg-green-700 hover:bg-green-600 text-white py-2 px-4 rounded disabled:opacity-50"
          >
            {loading ? "Sending Test..." : "Send Test Email Now"}
          </button>
        </div>
      </form>

      <div className="bg-green-900/30 border border-green-700 rounded p-4">
        <h3 className="text-lg font-bold mb-2">How Testing Works</h3>
        <ul className="list-disc pl-5 space-y-1 text-green-200">
          <li>Click "Send Test Email Now" to immediately run a research task and send an email</li>
          <li>The test will use your current AI model and server configuration</li>
          <li>It will research cybersecurity incidents for the specified date range</li>
          <li>The results will be sent to the selected recipient group (or test email if provided)</li>
          <li>This runs immediately without waiting for any schedule</li>
        </ul>
      </div>
    </div>
  );
};

export default TestSection;