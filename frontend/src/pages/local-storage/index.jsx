import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useOutletContext, useNavigate } from 'react-router-dom';
import { getLocalStorageFiles, uploadToLocalStorage, deleteLocalStorageFile, queryLocalStorageFiles } from '../../api/apiService';
import { FaTrash, FaDownload, FaEye, FaFile } from 'react-icons/fa';

export default function LocalStoragePage() {
    const [files, setFiles] = useState([]);
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [filesToUpload, setFilesToUpload] = useState([]);
    const [prompt, setPrompt] = useState('');
    const { selectedOllamaServer, selectedModel } = useOutletContext();
    const navigate = useNavigate();

    const onDrop = useCallback((acceptedFiles) => {
        setFilesToUpload((prevFiles) => [...prevFiles, ...acceptedFiles]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
    });

    useEffect(() => {
        fetchFiles();
    }, []);

    const fetchFiles = async () => {
        const fetchedFiles = await getLocalStorageFiles();
        setFiles(fetchedFiles);
    };

    const handleFileSelect = (filename) => {
        setSelectedFiles(prev => 
            prev.includes(filename) ? prev.filter(f => f !== filename) : [...prev, filename]
        );
    };

    const handleUpload = async () => {
        if (filesToUpload.length === 0) {
            alert('Please select files to upload.');
            return;
        }
        const formData = new FormData();
        filesToUpload.forEach(file => {
            formData.append('files', file);
        });
        await uploadToLocalStorage(formData);
        fetchFiles();
        setFilesToUpload([]);
    };

    const removeFileToUpload = (fileName) => {
        setFilesToUpload(filesToUpload.filter((file) => file.name !== fileName));
    };

    const handleDelete = async (filename) => {
        if (window.confirm(`Are you sure you want to delete ${filename}?`)) {
            await deleteLocalStorageFile(filename);
            fetchFiles();
        }
    };

    const handleQuery = async () => {
        if (!prompt || selectedFiles.length === 0 || !selectedOllamaServer || !selectedModel) {
            alert('Please select files, enter a prompt, and select a server and model.');
            return;
        }
        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('filenames', JSON.stringify(selectedFiles));
        formData.append('ollama_model', selectedModel);
        formData.append('ollama_server_name', selectedOllamaServer.name);
        formData.append('server_type', selectedOllamaServer.type);

        const response = await queryLocalStorageFiles(formData);
        navigate(`/local-storage/result/${response.job_id}`);
    };

    return (
        <div className="w-full h-full flex flex-col p-5 bg-gray-900 text-white">
            <h1 className="text-2xl font-bold mb-5">LocalStorage</h1>
            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {files.map(file => (
                    <div key={file} className="relative group bg-gray-800 p-4 rounded-lg flex flex-col items-center justify-center">
                        <input type="checkbox" className="absolute top-2 left-2 z-10" onChange={() => handleFileSelect(file)} checked={selectedFiles.includes(file)} />
                        <div className="w-16 h-16 mb-2">
                            <FaFile className="w-full h-full" />
                        </div>
                        <p className="text-sm text-center break-all">{file}</p>
                        <div className="absolute bottom-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <FaEye className="cursor-pointer" onClick={() => window.open(`http://localhost:8000/local-storage/files/${file}`)} />
                            <a href={`http://localhost:8000/local-storage/files/${file}`} download><FaDownload /></a>
                            <FaTrash className="cursor-pointer" onClick={() => handleDelete(file)} />
                        </div>
                    </div>
                ))}
            </div>
            <div className="mt-5 flex items-center gap-4">
                <textarea 
                    className="w-full p-2 rounded bg-gray-800 text-white" 
                    rows="3" 
                    placeholder="Enter your prompt here..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                />
                <button 
                    className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
                    onClick={handleQuery}
                >
                    Run Query
                </button>
            </div>
            <div className="mt-5">
                <div
                    {...getRootProps()}
                    className={`border-2 border-dashed border-green-500 rounded-lg p-10 text-center cursor-pointer transition-colors duration-200 ${isDragActive ? "bg-green-900/50" : "bg-gray-800 hover:bg-gray-700"}`}
                >
                    <input {...getInputProps()} />
                    {isDragActive ? (
                        <p className="text-green-400">Drop the files here ...</p>
                    ) : (
                        <p className="text-gray-400">Drag & drop files here, or click to select</p>
                    )}
                </div>

                {filesToUpload.length > 0 && (
                    <aside className="mt-4 p-4 bg-gray-800 rounded-lg shadow">
                        <h4 className="text-lg font-semibold text-white mb-2">Files to Upload:</h4>
                        <ul className="list-disc list-inside text-gray-300">
                            {filesToUpload.map((file) => (
                                <li key={file.path} className="flex justify-between items-center py-1">
                                    <span>{file.path} - {(file.size / 1024).toFixed(2)} KB</span>
                                    <button
                                        type="button"
                                        onClick={() => removeFileToUpload(file.name)}
                                        className="ml-4 text-red-400 hover:text-red-600 focus:outline-none"
                                    >
                                        Remove
                                    </button>
                                </li>
                            ))}
                        </ul>
                        <button 
                            className="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                            onClick={handleUpload}
                        >
                            Upload
                        </button>
                    </aside>
                )}
            </div>
        </div>
    );
}