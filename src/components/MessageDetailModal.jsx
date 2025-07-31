// --- CREATE NEW FILE: src/components/MessageDetailModal.jsx ---

import React, { useState, useEffect } from 'react';
import { getMessageDetailApi } from '../api/listener';
import { toast } from 'react-hot-toast';

const MessageDetailModal = ({ messageId, onClose, onLoadIntoParser }) => {
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(true);
    const [isCopied, setIsCopied] = useState(false);

    useEffect(() => {
        if (messageId) {
            setLoading(true);
            getMessageDetailApi(messageId)
                .then(data => setMessage(data.raw_message))
                .catch(err => toast.error(`Failed to load message detail: ${err.message}`))
                .finally(() => setLoading(false));
        }
    }, [messageId]);

    const handleCopy = async () => {
        if (isCopied || !message) return;
        await navigator.clipboard.writeText(message);
        setIsCopied(true);
        toast.success("Message copied to clipboard!");
        setTimeout(() => setIsCopied(false), 2000);
    };

    const handleLoad = () => {
        onLoadIntoParser(message);
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h2 className="text-xl font-bold text-white">Message Detail (ID: {messageId})</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">×</button>
                </div>
                <div className="flex-grow overflow-y-auto p-4">
                    {loading ? (
                        <p className="text-gray-400">Loading message...</p>
                    ) : (
                        <pre className="text-sm font-mono bg-gray-900 p-3 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
                            {message.replace(/\r/g, '\n')}
                        </pre>
                    )}
                </div>
                <div className="p-4 border-t border-gray-700 flex justify-end gap-4">
                    <button onClick={handleLoad} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-white font-bold">Load into Parser</button>
                    <button onClick={handleCopy} className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-white">{isCopied ? "Copied!" : "Copy Raw"}</button>
                    <button onClick={onClose} className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-white">Close</button>
                </div>
            </div>
        </div>
    );
};

export default MessageDetailModal;