// --- START OF FILE src/components/ConnectionInputs.jsx ---
import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import SendButton from './SendButton';
import { getEndpointsApi } from '../api/endpoints'; // <-- NEW: Use the correct API
import { ChevronDownIcon } from '@heroicons/react/20/solid';

const ConnectionInputs = ({ host, setHost, port, setPort, isSending, handleSend, handlePing }) => {
    const { isAuthenticated, isAdmin } = useAuth();
    const [savedEndpoints, setSavedEndpoints] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);

    useEffect(() => {
        // Fetch endpoints if the user is logged in
        if (isAuthenticated) {
            getEndpointsApi()
                .then(data => {
                    // We only care about MLLP endpoints for this input
                    const mllpEndpoints = data.filter(ep => ep.endpoint_type === 'MLLP');
                    setSavedEndpoints(mllpEndpoints);
                })
                .catch(err => console.error("Failed to fetch endpoints:", err));
        }
    }, [isAuthenticated]);

    const handleSelectEndpoint = (endpoint) => {
        setHost(endpoint.hostname);
        setPort(endpoint.port);
        setShowDropdown(false);
    }

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
                {/* THIS BUTTON IS NOW A DROPDOWN SELECTOR */}
                <div className="relative">
                    <button
                        onClick={() => setShowDropdown(prev => !prev)}
                        className="w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-md flex items-center justify-center"
                        title="Select a saved endpoint"
                    >
                         <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" /></svg>
                        Saved
                        <ChevronDownIcon className="h-5 w-5 ml-1" />
                    </button>
                    {showDropdown && (
                         <div className="absolute bottom-full mb-2 w-full bg-gray-700 rounded-md shadow-lg z-10 border border-gray-600">
                             {savedEndpoints.length > 0 ? (
                                savedEndpoints.map(ep => (
                                    <div key={ep.id} onClick={() => handleSelectEndpoint(ep)} className="p-2 hover:bg-indigo-600 cursor-pointer">
                                       <p className="font-semibold">{ep.name}</p>
                                       <p className="text-xs text-gray-300 font-mono">{ep.hostname}:{ep.port}</p>
                                    </div>
                                ))
                             ) : (
                                <div className="p-2 text-sm text-gray-400">
                                    No saved MLLP endpoints. {isAdmin ? "Add some in the Admin panel." : "Ask an admin to add some."}
                                </div>
                             )}
                         </div>
                    )}
                </div>

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