// --- REPLACE src/components/ListenerOutput.jsx ---

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { getMessagesApi, clearMessagesApi } from '../api/listener';
import { toast } from 'react-hot-toast';
import MessageDetailModal from './MessageDetailModal'; // We will create this next

const useDebounce = (value, delay) => {
    const [debouncedValue, setDebouncedValue] = useState(value);
    useEffect(() => {
        const handler = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(handler);
    }, [value, delay]);
    return debouncedValue;
};

const ListenerOutput = ({ onLoadIntoParser }) => {
    const [data, setData] = useState({ items: [], total: 0, page: 1, pages: 1 });
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [searchTerm, setSearchTerm] = useState('');
    const debouncedSearchTerm = useDebounce(searchTerm, 500);
    const [selectedMessageId, setSelectedMessageId] = useState(null);
    const { socket } = useAuth();

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const result = await getMessagesApi({ page, perPage: 25, search: debouncedSearchTerm });
            setData(result);
        } catch (error) {
            toast.error(`Failed to load messages: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }, [page, debouncedSearchTerm]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        if (socket) {
            const handleNewMessage = () => {
                // If on the first page and not searching, refresh to show the new message
                if (page === 1 && !debouncedSearchTerm) {
                    fetchData();
                } else {
                    toast.success("New message received. Refresh or go to page 1 to see it.");
                }
            };
            socket.on('new_message_received', handleNewMessage);
            return () => socket.off('new_message_received', handleNewMessage);
        }
    }, [socket, page, debouncedSearchTerm, fetchData]);

    const handleClear = async () => {
        if (!window.confirm("Are you sure you want to delete all received messages?")) return;
        try {
            await clearMessagesApi();
            toast.success("Message log cleared.");
            fetchData();
        } catch (error) {
            toast.error(`Failed to clear messages: ${error.message}`);
        }
    };
    
    return (
        <div className="mt-8">
            {selectedMessageId && (
                <MessageDetailModal
                    messageId={selectedMessageId}
                    onClose={() => setSelectedMessageId(null)}
                    onLoadIntoParser={onLoadIntoParser}
                />
            )}
            <div className="flex justify-between items-center mb-4 gap-4">
                <input
                    type="text"
                    placeholder="Search by Type, Sender, Control ID, or content..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full p-2 bg-gray-900 border border-gray-600 rounded-md text-white"
                />
                <button onClick={handleClear} className="px-4 py-2 text-xs font-semibold text-white bg-red-700 rounded-md hover:bg-red-800 transition-colors flex-shrink-0">
                    Clear Log
                </button>
            </div>
            
            <div className="bg-gray-800 rounded-lg overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-gray-900">
                        <tr>
                            <th className="p-3 text-sm font-semibold text-gray-300">Timestamp (UTC)</th>
                            <th className="p-3 text-sm font-semibold text-gray-300">Message Type</th>
                            <th className="p-3 text-sm font-semibold text-gray-300">Sending App</th>
                            <th className="p-3 text-sm font-semibold text-gray-300">Control ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="4" className="p-6 text-center text-gray-500">Loading...</td></tr>
                        ) : data.items.length === 0 ? (
                             <tr><td colSpan="4" className="p-6 text-center text-gray-500">No messages found.</td></tr>
                        ) : (
                            data.items.map(msg => (
                                <tr key={msg.id} onClick={() => setSelectedMessageId(msg.id)} className="border-b border-gray-700/50 hover:bg-gray-700/40 cursor-pointer">
                                    <td className="p-3 font-mono text-sm">{new Date(msg.timestamp).toLocaleString('en-GB', { timeZone: 'UTC' })}</td>
                                    <td className="p-3 font-mono text-sm text-indigo-300">{msg.message_type}</td>
                                    <td className="p-3 font-mono text-sm text-yellow-300">{msg.sending_app}</td>
                                    <td className="p-3 font-mono text-sm text-gray-400">{msg.control_id}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="flex justify-between items-center mt-4">
                <span className="text-sm text-gray-400">Page {data.page} of {data.pages}. Total: {data.total} messages.</span>
                <div className="flex gap-2">
                    <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={data.page <= 1} className="px-4 py-2 text-sm bg-gray-600 rounded disabled:opacity-50">Prev</button>
                    <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={data.page >= data.pages} className="px-4 py-2 text-sm bg-gray-600 rounded disabled:opacity-50">Next</button>
                </div>
            </div>
        </div>
    );
};

export default ListenerOutput;