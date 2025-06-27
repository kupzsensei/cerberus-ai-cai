import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { processMultipleFiles } from "../../api/apiService";

import '../../PdfProfessor.css'
import { useOutletContext } from "react-router-dom";

const UploadPage = () => {
    const [files, setFiles] = useState([]);
    const [prompt, setPrompt] = useState("");
    
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState(null);
    const [error, setError] = useState("");

    const outletContext = useOutletContext()
    const ollamaModel = outletContext // <-- ADDED: State for model

    // console.log('pdfprofessor context',outletContext )

    const onDrop = useCallback((acceptedFiles) => {
        setFiles((prevFiles) => [...prevFiles, ...acceptedFiles]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { "application/pdf": [".pdf"] },
    });

    const removeFile = (fileName) => {
        setFiles(files.filter((file) => file.name !== fileName));
    };



    const handleSubmit = async (e) => {
        e.preventDefault();
        if (files.length === 0 || !prompt) {
            setError("Please add at least one PDF file and a prompt.");
            return;
        }

        setIsLoading(true);
        setResponse(null);
        setError("");

        try {
            // ALWAYS use the background processing endpoint for consistency and to avoid timeouts.
            const result = await processMultipleFiles(prompt, files, ollamaModel); // <-- UPDATED

            // The response is now just a confirmation message.
            // The actual result must be viewed on the Status page.
            setResponse(result);
            setFiles([]); // Clear files on success
            setPrompt(""); // Clear prompt on success
        } catch (err) {
            const errorMessage =
                err.response?.data?.detail ||
                err.message ||
                "An unknown error occurred.";
            setError(
                typeof errorMessage === "string"
                    ? errorMessage
                    : JSON.stringify(errorMessage)
            );
        } finally {
            setIsLoading(false);
        }
    };
    return (
        <div className="page-content text-green-500 border-b p-5">
            <h1 className="font-bold">Upload and Process PDFs</h1>
            <p>
                Drag 'n' drop PDF files here, or click to select files. The system will
                automatically choose the correct API endpoint based on the number of
                files.
            </p>

            <form onSubmit={handleSubmit}>
                <div
                    {...getRootProps()}
                    className={`dropzone ${isDragActive ? "active" : ""}`}
                >
                    <input {...getInputProps()} />
                    {isDragActive ? (
                        <p>Drop the files here ...</p>
                    ) : (
                        <p>Drag & drop PDFs here, or click to select</p>
                    )}
                </div>

                {files.length > 0 && (
                    <aside className="file-list">
                        <h4>Selected Files:</h4>
                        <ul>
                            {files.map((file) => (
                                <li key={file.path}>
                                    {file.path} - {(file.size / 1024).toFixed(2)} KB
                                    <button type="button" onClick={() => removeFile(file.name)}>
                                        Remove
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </aside>
                )}
                {/* ADDED: Model Selection Dropdown
                <div className="prompt-area">
                    <label htmlFor="ollama-model">Ollama Model</label>
                    <select
                        id="ollama-model"
                        value={ollamaModel}
                        onChange={(e) => setOllamaModel(e.target.value)}
                    >
                        <option value="gemma3">Gemma3</option>
                        <option value="llama2">Llama2</option>
                        <option value="mistral">Mistral</option>
                        <option value="codellama">CodeLlama</option>
                    </select>
                </div> */}

                <div className="prompt-area">
                    <label htmlFor="prompt">Your Prompt</label>
                    <textarea
                        id="prompt"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="e.g., 'Summarize the key findings in these documents...'"
                        rows="4"
                    />
                </div>

                <button
                    type="submit"
                    className="mt-5"
                    disabled={isLoading || files.length === 0 || !prompt}
                >
                    {isLoading ? "Processing..." : `Process ${files.length} File(s)`}
                </button>
            </form>

            {error && <div className="error-message">{error}</div>}

            {response && (
                <div className="response-area">
                    <h3>Server Response</h3>
                    <pre>{JSON.stringify(response, null, 2)}</pre>
                </div>
            )}
        </div>
    );
};

export default UploadPage;