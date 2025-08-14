import { useState, useEffect, useCallback, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { useOutletContext, useNavigate } from 'react-router-dom';
import { getLocalStorageFiles, uploadToLocalStorage, deleteLocalStorageFile, queryLocalStorageFiles } from '../../api/apiService';
import { FaTrash, FaDownload, FaEye, FaFile } from 'react-icons/fa';

export default function LocalStoragePage() {
    const [files, setFiles] = useState([]);
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [filesToUpload, setFilesToUpload] = useState([]);
    const [prompt, setPrompt] = useState('');
    const [searchTerm, setSearchTerm] = useState('');
    const [sortOrder, setSortOrder] = useState('name-asc'); // 'name-asc', 'name-desc', 'date-asc', 'date-desc'
    const [fileTypeFilter, setFileTypeFilter] = useState(''); // 'pdf', 'txt', 'doc', etc.
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
        
        // Show success message and close modal after a delay
        alert('Your files uploaded successfully!');
        setIsUploadModalOpen(false);
    };

    const removeFileToUpload = (fileName) => {
        setFilesToUpload(filesToUpload.filter((file) => file.name !== fileName));
    };

    const handleDelete = async (filename) => {
        if (window.confirm(`Are you sure you want to delete ${filename}?`)) {
            await deleteLocalStorageFile(filename);
            fetchFiles();
            // Remove the file from selectedFiles if it was selected
            setSelectedFiles(prev => prev.filter(f => f !== filename));
        }
    };

    const handleDeleteSelected = async () => {
        if (selectedFiles.length === 0) return;
        
        if (window.confirm(`Are you sure you want to delete ${selectedFiles.length} selected files?`)) {
            try {
                // Delete all selected files
                await Promise.all(selectedFiles.map(filename => deleteLocalStorageFile(filename)));
                fetchFiles();
                setSelectedFiles([]); // Clear selection
            } catch (error) {
                console.error("Error deleting files:", error);
                alert("Failed to delete some files. Please try again.");
            }
        }
    };

    const handleDownloadSelected = async () => {
        if (selectedFiles.length === 0) return;
        
        // Download each selected file
        selectedFiles.forEach(filename => {
            const link = document.createElement('a');
            link.href = `/api/local-storage/files/${filename}`;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    };

    const handleQuery = async () => {
        if (!prompt || selectedFiles.length === 0 || !selectedOllamaServer || !selectedModel) {
            alert('Please select files, enter a prompt, and select a server and model.');
            return;
        }
        console.log({ prompt, selectedFiles, selectedOllamaServer, selectedModel });
        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('filenames', JSON.stringify(selectedFiles));
        formData.append('model_name', selectedModel);
        formData.append('server_name', selectedOllamaServer.name);
        formData.append('server_type', selectedOllamaServer.type);

        const response = await queryLocalStorageFiles(formData);
        navigate(`/local-storage/result/${response.job_id}`);
    };

    const filteredFiles = useMemo(() => {
        let currentFiles = [...files];

        // Apply search filter
        if (searchTerm) {
            currentFiles = currentFiles.filter(file =>
                file.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        // Apply file type filter
        if (fileTypeFilter) {
            currentFiles = currentFiles.filter(file =>
                file.toLowerCase().endsWith(`.${fileTypeFilter.toLowerCase()}`)
            );
        }

        // Apply sorting
        currentFiles.sort((a, b) => {
            if (sortOrder === 'name-asc') {
                return a.localeCompare(b);
            } else if (sortOrder === 'name-desc') {
                return b.localeCompare(a);
            } else if (sortOrder === 'date-asc') {
                // Assuming files are returned in some chronological order or we need metadata
                // For now, just use filename as a proxy for date if no actual date metadata is available
                return a.localeCompare(b); // Placeholder, ideally needs actual date
            } else if (sortOrder === 'date-desc') {
                return b.localeCompare(a); // Placeholder, ideally needs actual date
            }
            return 0;
        });

        return currentFiles;
    }, [files, searchTerm, sortOrder, fileTypeFilter]);

    // State for upload modal
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

    return (
        <div className="w-full h-full flex flex-col p-5 bg-gray-900 text-white">
            <div className="flex justify-between items-center mb-5">
                <h1 className="text-2xl font-bold">LocalStorage</h1>
                <button
                    className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg flex items-center gap-2"
                    onClick={() => setIsUploadModalOpen(true)}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                    Upload Files
                </button>
            </div>

            {/* Search, Sort, Filter */}
            <div className="mb-4 flex flex-wrap items-center gap-4">
                <input
                    type="text"
                    placeholder="Search files..."
                    className="flex-1 p-2 rounded bg-gray-800 text-white border border-gray-700"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
                <select
                    className="p-2 rounded bg-gray-800 text-white border border-gray-700"
                    value={sortOrder}
                    onChange={(e) => setSortOrder(e.target.value)}
                >
                    <option value="name-asc">Name (A-Z)</option>
                    <option value="name-desc">Name (Z-A)</option>
                    <option value="date-asc">Date (Oldest)</option>
                    <option value="date-desc">Date (Newest)</option>
                </select>
                <select
                    className="p-2 rounded bg-gray-800 text-white border border-gray-700"
                    value={fileTypeFilter}
                    onChange={(e) => setFileTypeFilter(e.target.value)}
                >
                    <option value="">All Types</option>
                    <option value="pdf">PDF</option>
                    <option value="txt">Text</option>
                    <option value="doc">DOC</option>
                    {/* Add more file types as needed */}
                </select>
            </div>

            {/* Group Actions */}
            {selectedFiles.length > 0 && (
              <div className="mb-4 flex gap-2">
                <button
                  className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg flex items-center gap-2"
                  onClick={handleDeleteSelected}
                >
                  <FaTrash /> Delete Selected ({selectedFiles.length})
                </button>
                <button
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg flex items-center gap-2"
                  onClick={handleDownloadSelected}
                >
                  <FaDownload /> Download Selected ({selectedFiles.length})
                </button>
              </div>
            )}

            {/* File Display Area */}
            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 overflow-y-auto p-2">
                {filteredFiles.map(file => (
                    <div key={file} className="relative group bg-gray-800 p-3 rounded-lg flex flex-col items-center justify-between text-center shadow-lg hover:shadow-xl transition-all duration-200 h-min">
                        <input
                            type="checkbox"
                            className="absolute top-2 left-2 z-10 form-checkbox h-5 w-5 text-green-500 rounded"
                            onChange={() => handleFileSelect(file)}
                            checked={selectedFiles.includes(file)}
                        />
                        <div className="w-12 h-12 mb-2 text-green-400">
                            <FaFile className="w-full h-full" />
                        </div>
                        <p className="text-sm font-medium text-white break-all mt-2">{file}</p>
                        <div className="absolute top-2 right-2 flex flex-col gap-1">
                            <FaEye
                                className="cursor-pointer text-gray-400 hover:text-blue-400"
                                onClick={() => window.open(`/api/local-storage/files/${file}`, '_blank')}
                                title="View File"
                            />
                            <a href={`/api/local-storage/files/${file}`} download className="text-gray-400 hover:text-green-400" title="Download File">
                                <FaDownload />
                            </a>
                            <FaTrash
                                className="cursor-pointer text-gray-400 hover:text-red-400"
                                onClick={() => handleDelete(file)}
                                title="Delete File"
                            />
                        </div>
                    </div>
                ))}
            </div>

            {/* Query Area */}
            <div className="mt-5 flex flex-col md:flex-row items-center gap-4">
                <textarea
                    className="w-full p-3 rounded bg-gray-800 text-white border border-gray-700 focus:border-green-500 focus:ring focus:ring-green-500 focus:ring-opacity-50 resize-y"
                    rows="3"
                    placeholder="Enter your prompt here to query selected files..."
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                />
                <button
                    className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 whitespace-nowrap"
                    onClick={handleQuery}
                >
                    Run Query
                </button>
            </div>

            {/* File Upload Area - Hidden when modal is used */}
            {false && (
                <div className="mt-5 p-4 border-2 border-dashed border-green-500 rounded-lg text-center transition-colors duration-200">
                    <div
                        {...getRootProps()}
                        className={`p-10 cursor-pointer ${isDragActive ? "bg-green-900/50" : "bg-gray-800 hover:bg-gray-700"}`}
                    >
                        <input {...getInputProps()} />
                        {isDragActive ? (
                            <p className="text-green-400">Drop the files here ...</p>
                        ) : (
                            <p className="text-gray-400">Drag & drop files here, or click to select</p>
                        )}
                    </div>

                    {filesToUpload.length > 0 && (
                        <aside className="mt-4 p-4 bg-gray-700 rounded-lg shadow-inner">
                            <h4 className="text-lg font-semibold text-white mb-3">Files to Upload:</h4>
                            <ul className="list-none space-y-2 text-gray-300">
                                {filesToUpload.map((file) => (
                                    <li key={file.path} className="flex justify-between items-center bg-gray-800 p-2 rounded">
                                        <span>{file.path} - {(file.size / 1024).toFixed(2)} KB</span>
                                        <button
                                            type="button"
                                            onClick={() => removeFileToUpload(file.name)}
                                            className="ml-4 text-red-400 hover:text-red-500 focus:outline-none text-sm"
                                        >
                                            Remove
                                        </button>
                                    </li>
                                ))}
                            </ul>
                            <button
                                className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-5 rounded-lg shadow-md transition-all duration-200"
                                onClick={handleUpload}
                            >
                                Upload Selected Files
                            </button>
                        </aside>
                    )}
                </div>
            )}
            
            {/* Upload Modal */}
            {isUploadModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                        <div className="p-6">
                            <div className="flex justify-between items-center mb-4">
                                <h2 className="text-xl font-bold text-white">Upload Files</h2>
                                <button 
                                    onClick={() => setIsUploadModalOpen(false)}
                                    className="text-gray-400 hover:text-white"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                            
                            {/* File Upload Area */}
                            <div className="mt-4 p-6 border-2 border-dashed border-green-500 rounded-lg text-center transition-colors duration-200">
                                <div
                                    {...getRootProps()}
                                    className={`p-8 cursor-pointer ${isDragActive ? "bg-green-900/50" : "bg-gray-700 hover:bg-gray-600"}`}
                                >
                                    <input {...getInputProps()} />
                                    {isDragActive ? (
                                        <p className="text-green-400 text-lg">Drop the files here ...</p>
                                    ) : (
                                        <div>
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-green-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                            </svg>
                                            <p className="text-gray-300 text-lg">Drag & drop files here, or click to select</p>
                                            <p className="text-gray-400 text-sm mt-2">Supports all file types</p>
                                        </div>
                                    )}
                                </div>

                                {filesToUpload.length > 0 && (
                                    <div className="mt-6">
                                        <h3 className="text-lg font-semibold text-white mb-3">Selected Files:</h3>
                                        <ul className="list-none space-y-2 text-gray-300">
                                            {filesToUpload.map((file) => (
                                                <li key={file.path} className="flex justify-between items-center bg-gray-700 p-3 rounded">
                                                    <div>
                                                        <span className="font-medium">{file.path}</span>
                                                        <span className="text-gray-400 text-sm block"> {(file.size / 1024).toFixed(2)} KB</span>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={() => removeFileToUpload(file.name)}
                                                        className="ml-4 text-red-400 hover:text-red-500 focus:outline-none"
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                                                        </svg>
                                                    </button>
                                                </li>
                                            ))}
                                        </ul>
                                        <button
                                            className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-5 rounded-lg shadow-md transition-all duration-200 w-full"
                                            onClick={handleUpload}
                                        >
                                            Upload Selected Files
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}