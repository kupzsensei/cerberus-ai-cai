// frontend/src/api/apiService.js

import axios from "axios";

// Make the base URL a relative path. The Nginx proxy will handle it.
const API_BASE_URL = "/api";

// --- Ensure ALL functions below use this relative path ---

export const processSingleFile = async (prompt, file, modelName, serverName, serverType) => {
  const formData = new FormData();
  formData.append("prompt", prompt);
  formData.append("file", file);
  formData.append("model_name", modelName);
  formData.append("server_name", serverName);
  formData.append("server_type", serverType);
  const response = await axios.post(`${API_BASE_URL}/pdfprofessor`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const processMultipleFiles = async (prompt, files, modelName, serverName, serverType) => {
  const formData = new FormData();
  formData.append("user_prompt", prompt);
  formData.append("model_name", modelName);
  formData.append("server_name", serverName);
  formData.append("server_type", serverType);
  files.forEach((file) => {
    formData.append("files", file);
  });
  const response = await axios.post(`${API_BASE_URL}/process-pdfs/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getStatus = async () => {
  const response = await axios.get(`${API_BASE_URL}/status`);
  return response.data;
};

export const getTaskById = async (taskId) => {
  const response = await axios.get(`${API_BASE_URL}/status/${taskId}`);
  return response.data;
};

export const deleteTaskById = async (taskId) => {
  const response = await axios.delete(`${API_BASE_URL}/task/${taskId}`);
  return response.data;
};

export const researchByDate = async (query, serverName, modelName, serverType) => {
  const formData = new FormData();
  formData.append("query", query);
  if (serverName) {
    formData.append("server_name", serverName);
  }
  if (modelName) {
    formData.append("model_name", modelName);
  }
  if (serverType) {
    formData.append("server_type", serverType);
  }
  const response = await axios.post(`${API_BASE_URL}/research`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const investigate = async (query, serverName, modelName, serverType) => {
  const formData = new FormData();
  formData.append("query", query);
  if (serverName) {
    formData.append("server_name", serverName);
  }
  if (modelName) {
    formData.append("model_name", modelName);
  }
  if (serverType) {
    formData.append("server_type", serverType);
  }
  const response = await axios.post(`${API_BASE_URL}/investigate`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getOllamaServers = async () => {
  const response = await axios.get(`${API_BASE_URL}/ollama-servers`);
  return response.data.servers;
};

export const addOllamaServer = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/ollama-servers`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteOllamaServer = async (name) => {
  const response = await axios.delete(`${API_BASE_URL}/ollama-servers/${name}`);
  return response.data;
};

export const getExternalAIServers = async () => {
  const response = await axios.get(`${API_BASE_URL}/external-ai-servers`);
  return response.data.servers;
};

export const addExternalAIServer = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/external-ai-servers`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteExternalAIServer = async (name) => {
  const response = await axios.delete(`${API_BASE_URL}/external-ai-servers/${name}`);
  return response.data;
};

export const getResearchList = async () => {
  const response = await axios.get(`${API_BASE_URL}/research`);
  return response.data;
};

export const getResearchById = async (researchId) => {
  const response = await axios.get(`${API_BASE_URL}/research/${researchId}`);
  return response.data;
};

export const deleteResearchById = async (researchId) => {
  const response = await axios.delete(`${API_BASE_URL}/research/${researchId}`);
  return response.data;
};

// --- New Research Job Pipeline APIs ---

export const startResearchJob = async ({
  query,
  serverName,
  modelName,
  serverType,
  targetCount,
  seedUrls,
  focusOnSeed = true,
  config,
}) => {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("server_name", serverName);
  formData.append("model_name", modelName);
  formData.append("server_type", serverType);
  formData.append("target_count", String(targetCount));
  if (seedUrls) formData.append("seed_urls", seedUrls);
  formData.append("focus_on_seed", String(focusOnSeed));
  if (config) {
    try {
      const cfgStr = typeof config === 'string' ? config : JSON.stringify(config);
      formData.append('config', cfgStr);
    } catch {}
  }
  const response = await axios.post(`${API_BASE_URL}/research/jobs/start`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data; // { job_id }
};

export const getResearchJobStatus = async (jobId) => {
  const response = await axios.get(`${API_BASE_URL}/research/jobs/${jobId}`);
  return response.data;
};

export const getResearchJobDrafts = async (jobId) => {
  const response = await axios.get(`${API_BASE_URL}/research/jobs/${jobId}/drafts`);
  return response.data.drafts;
};

export const cancelResearchJob = async (jobId) => {
  const response = await axios.post(`${API_BASE_URL}/research/jobs/${jobId}/cancel`);
  return response.data;
};

export const getOllamaModels = async (url) => {
  const response = await axios.get(`${API_BASE_URL}/ollama-models?url=${encodeURIComponent(url)}`);
  return response.data;
};

export const getExternalAIModels = async (serverType) => {
  const response = await axios.get(`${API_BASE_URL}/external-ai/models?server_type=${encodeURIComponent(serverType)}`);
  return response.data;
};

export const getLocalStorageFiles = async () => {
  const response = await axios.get(`${API_BASE_URL}/local-storage/files`);
  return response.data;
};

export const uploadToLocalStorage = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/local-storage/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteLocalStorageFile = async (filename) => {
  const response = await axios.delete(`${API_BASE_URL}/local-storage/files/${filename}`);
  return response.data;
};

export const deleteMultipleLocalStorageFiles = async (filenames) => {
  // Make multiple delete requests concurrently
  const promises = filenames.map(filename => 
    axios.delete(`${API_BASE_URL}/local-storage/files/${filename}`)
  );
  const responses = await Promise.all(promises);
  return responses.map(response => response.data);
};

export const queryLocalStorageFiles = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/local-storage/query`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getLocalStorageJobStatus = async (jobId) => {
  const response = await axios.get(`${API_BASE_URL}/local-storage/status/${jobId}`);
  return response.data;
};

export const getAllLocalStorageJobs = async () => {
  const response = await axios.get(`${API_BASE_URL}/local-storage/jobs`);
  return response.data;
};

export const deleteLocalStorageJob = async (jobId) => {
  const response = await axios.delete(`${API_BASE_URL}/local-storage/jobs/${jobId}`);
  return response.data;
};

export const chatWithAI = async (messages, modelName, serverName, serverType) => {
  const formData = new FormData();
  formData.append("messages", JSON.stringify(messages));
  formData.append("model_name", modelName);
  formData.append("server_name", serverName);
  formData.append("server_type", serverType);
  const response = await axios.post(`${API_BASE_URL}/chat`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

// --- Email Scheduler API Functions ---

export const getEmailConfigs = async () => {
  const response = await axios.get(`${API_BASE_URL}/email-configs`);
  return response.data.configs;
};

export const addEmailConfig = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/email-config`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const updateEmailConfig = async (configId, formData) => {
  const response = await axios.put(`${API_BASE_URL}/email-configs/${configId}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteEmailConfig = async (configId) => {
  const response = await axios.delete(`${API_BASE_URL}/email-configs/${configId}`);
  return response.data;
};

export const getEmailRecipientGroups = async () => {
  const response = await axios.get(`${API_BASE_URL}/email-recipient-groups`);
  return response.data.groups;
};

export const addEmailRecipientGroup = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/email-recipient-groups`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const updateEmailRecipientGroup = async (groupId, formData) => {
  const response = await axios.put(`${API_BASE_URL}/email-recipient-groups/${groupId}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteEmailRecipientGroup = async (groupId) => {
  const response = await axios.delete(`${API_BASE_URL}/email-recipient-groups/${groupId}`);
  return response.data;
};

export const getEmailRecipients = async (groupId) => {
  const response = await axios.get(`${API_BASE_URL}/email-recipients/${groupId}`);
  return response.data.recipients;
};

export const addEmailRecipient = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/email-recipients`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const updateEmailRecipient = async (recipientId, formData) => {
  const response = await axios.put(`${API_BASE_URL}/email-recipients/${recipientId}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteEmailRecipient = async (recipientId) => {
  const response = await axios.delete(`${API_BASE_URL}/email-recipients/${recipientId}`);
  return response.data;
};

export const getScheduledResearchList = async () => {
  const response = await axios.get(`${API_BASE_URL}/scheduled-research`);
  return response.data.scheduled_research;
};

export const addScheduledResearch = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/scheduled-research`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const updateScheduledResearch = async (researchId, formData) => {
  const response = await axios.put(`${API_BASE_URL}/scheduled-research/${researchId}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteScheduledResearch = async (researchId) => {
  const response = await axios.delete(`${API_BASE_URL}/scheduled-research/${researchId}`);
  return response.data;
};

export const testEmailConfig = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/test-email`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

// Test scheduled research immediately
export const testScheduledResearch = async (formData) => {
  const response = await axios.post(`${API_BASE_URL}/test-scheduled-research`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const getEmailDeliveryLogs = async (scheduledResearchId = null) => {
  const url = scheduledResearchId 
    ? `${API_BASE_URL}/email-delivery-logs?scheduled_research_id=${scheduledResearchId}`
    : `${API_BASE_URL}/email-delivery-logs`;
  const response = await axios.get(url);
  return response.data.logs;
};
