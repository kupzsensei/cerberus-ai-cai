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
