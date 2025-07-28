// frontend/src/api/apiService.js

import axios from "axios";

// Make the base URL a relative path. The Nginx proxy will handle it.
const API_BASE_URL = "/api";

// --- Ensure ALL functions below use this relative path ---

export const processSingleFile = async (prompt, file, ollamaModel) => {
  const formData = new FormData();
  formData.append("prompt", prompt);
  formData.append("file", file);
  formData.append("ollama_model", ollamaModel);
  const response = await axios.post(`${API_BASE_URL}/pdfprofessor`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const processMultipleFiles = async (prompt, files, ollamaModel, ollamaServerName) => {
  const formData = new FormData();
  formData.append("user_prompt", prompt);
  formData.append("ollama_model", ollamaModel);
  formData.append("ollama_server_name", ollamaServerName); // Add server name
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

export const researchByDate = async (query, ollamaServerName, ollamaModel) => {
  const formData = new FormData();
  formData.append("query", query);
  if (ollamaServerName) {
    formData.append("ollama_server_name", ollamaServerName);
  }
  if (ollamaModel) {
    formData.append("ollama_model", ollamaModel);
  }
  const response = await axios.post(`${API_BASE_URL}/research`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const investigate = async (query, ollamaServerName, ollamaModel) => {
  const formData = new FormData();
  formData.append("query", query);
  if (ollamaServerName) {
    formData.append("ollama_server_name", ollamaServerName);
  }
  if (ollamaModel) {
    formData.append("ollama_model", ollamaModel);
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

export const addOllamaServer = async (name, url, model) => {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("url", url);
  formData.append("model", model);
  const response = await axios.post(`${API_BASE_URL}/ollama-servers`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const deleteOllamaServer = async (name) => {
  const response = await axios.delete(`${API_BASE_URL}/ollama-servers/${name}`);
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
