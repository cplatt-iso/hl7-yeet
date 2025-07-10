// --- START OF FILE src/components/ConnectionInputs.jsx ---

import React from 'react';
import { useAuth } from '../context/AuthContext';
import SendButton from './SendButton';

const ConnectionInputs = ({ host, setHost, port, setPort, isSending, handleSend }) => {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
                <label htmlFor="host" className="block text-sm font-medium text-gray-400">Host</label>
                <input
                    type="text"
                    id="host"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2"
                />
            </div>
            <div>
                <label htmlFor="port" className="block text-sm font-medium text-gray-400">Port</label>
                <input
                    type="text"
                    id="port"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2"
                />
            </div>
            <div className="md:self-end">
                {/* We use the SendButton component here */}
                <SendButton
                    isSending={isSending}
                    onClick={handleSend}
                    disabled={!isAuthenticated}
                />
            </div>
        </div>
    );
};

export default ConnectionInputs;