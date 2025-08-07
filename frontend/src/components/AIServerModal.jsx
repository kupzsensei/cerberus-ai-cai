import React, { useState, useEffect } from 'react';
import { getOllamaServers, addOllamaServer, deleteOllamaServer, getExternalAIServers, addExternalAIServer, deleteExternalAIServer } from '../api/apiService';

const AIServerModal = ({ isOpen, onClose, onServerSelected }) => {
    const [ollamaServers, setOllamaServers] = useState([]);
    const [externalServers, setExternalServers] = useState([]);
    const [newServerName, setNewServerName] = useState('');
    const [newServerUrl, setNewServerUrl] = useState(''); // For Ollama
    const [newServerType, setNewServerType] = useState('ollama'); // 'ollama' or 'gemini'
    const [newServerApiKey, setNewServerApiKey] = useState(''); // For Gemini
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    useEffect(() => {
        if (isOpen) {
            fetchServers();
        }
    }, [isOpen]);

    const fetchServers = async () => {
        try {
            const ollamaData = await getOllamaServers();
            setOllamaServers(ollamaData);
            const externalData = await getExternalAIServers();
            setExternalServers(externalData);
        } catch (err) {
            setError('Failed to fetch servers.');
        }
    };

    const handleAddServer = async (e) => {
        e.preventDefault();
        setError('');
        setMessage('');

        if (!newServerName) {
            setError('Server name is required.');
            return;
        }

        try {
            if (newServerType === 'ollama') {
                if (!newServerUrl) {
                    setError('Ollama server URL is required.');
                    return;
                }
                const formData = new FormData();
                formData.append('name', newServerName);
                formData.append('url', newServerUrl);
                await addOllamaServer(formData);
            } else if (newServerType === 'gemini') {
                if (!newServerApiKey) {
                    setError('Gemini API Key is required.');
                    return;
                }
                const formData = new FormData();
                formData.append('name', newServerName);
                formData.append('type', newServerType);
                formData.append('api_key', newServerApiKey);
                await addExternalAIServer(formData);
            }
            setMessage(`Server ${newServerName} added successfully.`);
            setNewServerName('');
            setNewServerUrl('');
            setNewServerApiKey('');
            fetchServers();
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to add server.');
        }
    };

    const handleDeleteServer = async (name, type) => {
        setError('');
        setMessage('');
        if (window.confirm(`Are you sure you want to delete server ${name}?`)) {
            try {
                if (type === 'ollama') {
                    await deleteOllamaServer(name);
                } else if (type === 'gemini') {
                    await deleteExternalAIServer(name);
                }
                setMessage(`Server ${name} deleted successfully.`);
                fetchServers();
            } catch (err) {
                setError(err.response?.data?.detail || 'Failed to delete server.');
            }
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg shadow-lg w-11/12 md:w-1/2 lg:w-1/3 border border-green-500 text-green-500">
                <h2 className="text-xl font-bold mb-4">Manage AI Servers</h2>
                {error && <div className="text-red-500 mb-2">{error}</div>}
                {message && <div className="text-green-500 mb-2">{message}</div>}

                <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-2">Current Servers</h3>
                    {(ollamaServers.length === 0 && externalServers.length === 0) ? (
                        <p className="text-gray-400">No AI servers configured.</p>
                    ) : (
                        <ul className="space-y-2">
                            {ollamaServers.map(server => (
                                <li key={server.name} className="flex justify-between items-center bg-gray-700 p-3 rounded-md">
                                    <span>{server.name} (Ollama: {server.url})</span>
                                    <button 
                                        onClick={() => handleDeleteServer(server.name, 'ollama')} 
                                        className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded-md text-sm"
                                    >
                                        Delete
                                    </button>
                                </li>
                            ))}
                            {externalServers.map(server => (
                                <li key={server.name} className="flex justify-between items-center bg-gray-700 p-3 rounded-md">
                                    <span>{server.name} ({server.type})</span>
                                    <button 
                                        onClick={() => handleDeleteServer(server.name, server.type)} 
                                        className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded-md text-sm"
                                    >
                                        Delete
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <div>
                    <h3 className="text-lg font-semibold mb-2">Add New Server</h3>
                    <form onSubmit={handleAddServer} className="space-y-3">
                        <input
                            type="text"
                            placeholder="Server Name"
                            value={newServerName}
                            onChange={(e) => setNewServerName(e.target.value)}
                            className="w-full p-2 rounded-md bg-gray-700 border border-green-600 text-white placeholder-gray-400"
                        />
                        <select
                            value={newServerType}
                            onChange={(e) => setNewServerType(e.target.value)}
                            className="w-full p-2 rounded-md bg-gray-700 border border-green-600 text-white"
                        >
                            <option value="ollama">Ollama</option>
                            <option value="gemini">Gemini</option>
                        </select>
                        {newServerType === 'ollama' && (
                            <input
                                type="text"
                                placeholder="Server URL (e.g., http://localhost:11434)"
                                value={newServerUrl}
                                onChange={(e) => setNewServerUrl(e.target.value)}
                                className="w-full p-2 rounded-md bg-gray-700 border border-green-600 text-white placeholder-gray-400"
                            />
                        )}
                        {newServerType === 'gemini' && (
                            <input
                                type="text"
                                placeholder="Gemini API Key"
                                value={newServerApiKey}
                                onChange={(e) => setNewServerApiKey(e.target.value)}
                                className="w-full p-2 rounded-md bg-gray-700 border border-green-600 text-white placeholder-gray-400"
                            />
                        )}
                        <button 
                            type="submit" 
                            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-md"
                        >
                            Add Server
                        </button>
                    </form>
                </div>

                <button 
                    onClick={onClose} 
                    className="mt-6 w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-md"
                >
                    Close
                </button>
            </div>
        </div>
    );
};

export default AIServerModal;