import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { processMultipleFiles } from "../../api/apiService";
import { useOutletContext } from "react-router-dom";

const UploadPage = () => {
    const [files, setFiles] = useState([]);
    const [prompt, setPrompt] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState(null);
    const [error, setError] = useState("");

    const { selectedModel, selectedOllamaServer } = useOutletContext();

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
            const timestampedFiles = files.map(file => {
                const newName = `${Date.now()}-${file.name}`;
                return new File([file], newName, { type: file.type });
            });

            const result = await processMultipleFiles(prompt, timestampedFiles, selectedModel, selectedOllamaServer.name);

            setResponse(result);
            setFiles([]);
            setPrompt("");
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
        <div className="page-content p-5">
            <h1 className="text-2xl font-bold mb-4">Upload and Process PDFs</h1>
            <p className="text-gray-300 mb-6">
                Drag 'n' drop PDF files here, or click to select files. The system will
                automatically choose the correct API endpoint based on the number of
                files.
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div
                    {...getRootProps()}
                    className={`border-2 border-dashed border-green-500 rounded-lg p-10 text-center cursor-pointer transition-colors duration-200 ${isDragActive ? "bg-green-900/50" : "bg-gray-800 hover:bg-gray-700"}`}
                >
                    <input {...getInputProps()} />
                    {isDragActive ? (
                        <p className="text-green-400">Drop the files here ...</p>
                    ) : (
                        <p className="text-gray-400">Drag & drop PDFs here, or click to select</p>
                    )}
                </div>

                {files.length > 0 && (
                    <aside className="mt-4 p-4 bg-gray-800 rounded-lg shadow">
                        <h4 className="text-lg font-semibold text-white mb-2">Selected Files:</h4>
                        <ul className="list-disc list-inside text-gray-300">
                            {files.map((file) => (
                                <li key={file.path} className="flex justify-between items-center py-1">
                                    <span>{file.path} - {(file.size / 1024).toFixed(2)} KB</span>
                                    <button
                                        type="button"
                                        onClick={() => removeFile(file.name)}
                                        className="ml-4 text-red-400 hover:text-red-600 focus:outline-none"
                                    >
                                        Remove
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </aside>
                )}

                <div className="prompt-area">
                    <label htmlFor="prompt" className="block text-lg font-medium text-white mb-2">Your Prompt</label>
                    <textarea
                        id="prompt"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="e.g., 'Summarize the key findings in these documents...'"
                        rows="4"
                        className="w-full p-3 border border-green-600 rounded-md text-white bg-green-500/20 focus:ring-green-500 focus:border-green-500 outline-none"
                    />
                </div>

                <button
                    type="submit"
                    className="w-full px-4 py-2 border border-green-500 text-green-500 rounded-md hover:bg-green-500 hover:text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isLoading || files.length === 0 || !prompt}
                >
                    {isLoading ? "Processing..." : `Process ${files.length} File(s)`}
                </button>
            </form>

            {error && <div className="error-message text-red-500 mt-4">{error}</div>}

            {response && (
                <div className="response-area mt-4 p-4 bg-gray-800 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-white mb-2">Server Response</h3>
                    <pre className="whitespace-pre-wrap text-gray-300 text-sm">{JSON.stringify(response, null, 2)}</pre>
                </div>
            )}
        </div>
    );
};

export default UploadPage;