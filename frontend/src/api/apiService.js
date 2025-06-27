import axios from "axios";
// import { API_BASE_URL } from ".";

const API_BASE_URL = "/api";


// const API_BASE_URL = "http://127.0.0.1:8000"; // Your FastAPI server URL

/**
 * Processes a single PDF file.
 * @param {string} prompt The user's prompt.
 * @param {File} file The PDF file to process.
 * @param {string} ollamaModel The Ollama model to use.
 * @returns {Promise<object>} The server's response.
 */
export const processSingleFile = async (prompt, file, ollamaModel) => {
  const formData = new FormData();
  formData.append("prompt", prompt);
  formData.append("file", file);
  formData.append("ollama_model", ollamaModel); // <-- ADDED

  const response = await axios.post(`${API_BASE_URL}/pdfprofessor`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

/**
 * Processes multiple PDF files in the background.
 * @param {string} prompt The user's prompt.
 * @param {File[]} files An array of PDF files.
 * @param {string} ollamaModel The Ollama model to use.
 * @returns {Promise<object>} The server's response.
 */
export const processMultipleFiles = async (prompt, files, ollamaModel) => {
  const formData = new FormData();
  formData.append("user_prompt", prompt);
  formData.append("ollama_model", ollamaModel); // <-- ADDED
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await axios.post(`${API_BASE_URL}/process-pdfs/`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

/**
 * Fetches the status of all background tasks.
 * @returns {Promise<Array>} A list of tasks.
 */
export const getStatus = async () => {
  const response = await axios.get(`${API_BASE_URL}/status`);
  return response.data;
};

/**
 * Fetches a single task by its ID.
 * @param {string} taskId The ID of the task.
 * @returns {Promise<object>} The task object.
 */
export const getTaskById = async (taskId) => {
  const response = await axios.get(`${API_BASE_URL}/status/${taskId}`);
  return response.data;
};


/**
 * Deletes a task by its ID.
 * @param {string} taskId The ID of the task to delete.
 * @returns {Promise<object>} The server's confirmation message.
 */
export const deleteTaskById = async (taskId) => {
  const response = await axios.delete(`${API_BASE_URL}/task/${taskId}`);
  return response.data;
};
