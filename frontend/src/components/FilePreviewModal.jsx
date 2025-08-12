import React, { useState, useEffect } from 'react';
import { FaDownload, FaTrash } from 'react-icons/fa';

export default function FilePreviewModal({ file, onClose, onDelete }) {
    const [content, setContent] = useState(null);
    const [fileType, setFileType] = useState(null);

    useEffect(() => {
        if (file) {
            const fetchContent = async () => {
                const response = await fetch(`http://localhost:8000/local-storage/preview/${file.name}`);
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                
                if (blob.type.startsWith('image/')) {
                    setFileType('image');
                    setContent(url);
                } else if (blob.type.startsWith('text/') || blob.type === 'application/json') {
                    setFileType('text');
                    const text = await blob.text();
                    setContent(text);
                } else {
                    setFileType('other');
                    setContent(null);
                }
            };
            fetchContent();
        }
    }, [file]);

    if (!file) return null;

    const renderContent = () => {
        if (fileType === 'image') {
            return <img src={content} alt={file.name} className="max-w-full max-h-96" />;
        } else if (fileType === 'text') {
            return <pre className="bg-gray-900 p-4 rounded-lg text-white whitespace-pre-wrap">{content}</pre>;
        } else {
            return <p>No preview available for this file type.</p>;
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
            <div className="bg-gray-800 text-white rounded-lg shadow-lg p-6 w-full max-w-4xl max-h-full overflow-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold">{file.name}</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">&times;</button>
                </div>
                <div className="mb-4">
                    {renderContent()}
                </div>
                <div className="flex justify-end gap-4 mt-4">
                    <a href={`http://localhost:8000/local-storage/files/${file.name}`} download className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded flex items-center">
                        <FaDownload className="mr-2" /> Download
                    </a>
                    <button onClick={() => onDelete(file.name)} className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded flex items-center">
                        <FaTrash className="mr-2" /> Delete
                    </button>
                </div>
            </div>
        </div>
    );
}
