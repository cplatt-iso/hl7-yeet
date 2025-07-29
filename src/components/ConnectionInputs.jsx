// --- START OF FILE src/components/ConnectionInputs.jsx ---
import React from 'react';
import { useAuth } from '../context/AuthContext';
import SendButton from './SendButton';

// Add handlePing prop
const ConnectionInputs = ({ host, setHost, port, setPort, isSending, handleSend, onManageDestinations, handlePing }) => {
    const { isAuthenticated } = useAuth();

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="md:col-span-2 grid grid-cols-2 gap-4">
                <div>
                    <label htmlFor="host" className="block text-sm font-medium text-gray-400">Hostname</label>
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
            </div>
            <div className="grid grid-cols-3 gap-2 md:col-span-2">
                <button
                    onClick={onManageDestinations}
                    className="w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-md flex items-center justify-center"
                    title="Manage Saved Destinations"
                >
                     <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" /></svg>
                    Saved
                </button>
                <button
                    onClick={handlePing}
                    disabled={isSending || !host || !port}
                    className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-2 px-4 rounded-md flex items-center justify-center transition-colors disabled:bg-gray-600 disabled:cursor-not-allowed"
                    title="Test Connection"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    Test
                </button>
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
// --- END OF FILE src/components/ConnectionInputs.jsx ---