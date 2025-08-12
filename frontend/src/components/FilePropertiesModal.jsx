import React from 'react';

export default function FilePropertiesModal({ item, onClose }) {
    if (!item) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
            <div className="bg-gray-800 text-white rounded-lg shadow-lg p-6 w-full max-w-md max-h-full overflow-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">Properties: {item.name}</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">&times;</button>
                </div>
                <div className="mb-4">
                    <p><strong>Type:</strong> {item.is_dir ? 'Directory' : 'File'}</p>
                    <p><strong>Size:</strong> {item.is_file ? `${(item.size / 1024).toFixed(2)} KB` : 'N/A'}</p>
                    <p><strong>Modified:</strong> {new Date(item.mtime * 1000).toLocaleString()}</p>
                    <p><strong>Created:</strong> {new Date(item.ctime * 1000).toLocaleString()}</p>
                    <p><strong>Permissions (octal):</strong> {item.mode}</p>
                    <p><strong>Owner User ID:</strong> {item.uid}</p>
                    <p><strong>Owner Group ID:</strong> {item.gid}</p>
                </div>
                <div className="flex justify-end mt-4">
                    <button onClick={onClose} className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
