// --- START OF FILE src/components/TerminologyManagement.jsx ---

import React, { useState, useEffect } from 'react';
import { refreshTerminologyApi, getTerminologyStatusApi } from '../api/admin';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';
import TerminologyBrowser from './TerminologyBrowser'; // <-- NEW IMPORT

const ProgressBar = ({ progress }) => (
    <div className="w-full bg-gray-700 rounded-full h-2.5 mt-2">
        <div 
            className="bg-indigo-500 h-2.5 rounded-full transition-all duration-300 ease-linear" 
            style={{ width: `${progress}%` }}
        ></div>
    </div>
);

const TerminologyManagement = () => {
    const [isLoading, setIsLoading] = useState(false);
    const [stats, setStats] = useState(null);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [isBrowserOpen, setIsBrowserOpen] = useState(false); // <-- NEW STATE
    const { socket } = useAuth();

    const fetchStatus = async () => {
        try {
            const statusData = await getTerminologyStatusApi();
            setStats(statusData);
        } catch (error) {
            toast.error(`Could not load terminology stats: ${error.message}`);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, []);

    useEffect(() => {
        if (!socket) return;

        const handleStatusUpdate = (data) => {
            setProgressMessage(data.message);
            if (data.progress) {
                setProgress(data.progress);
            }
            if (data.status === 'success' || data.status === 'error') {
                setIsLoading(false);
                toast[data.status](data.message, { duration: 5000 });
                fetchStatus();
            }
        };

        socket.on('terminology_status', handleStatusUpdate);

        return () => {
            socket.off('terminology_status', handleStatusUpdate);
        };
    }, [socket]);

    const handleRefresh = async () => {
        if (!window.confirm("Are you sure? This will reload all terminology definitions and can take several minutes.")) return;
        
        setIsLoading(true);
        setProgress(0);
        setProgressMessage('Initiating refresh...');
        try {
            await refreshTerminologyApi();
        } catch (error) {
            setIsLoading(false);
            toast.error(`Failed to start refresh: ${error.message}`);
        }
    };

    return (
        <div>
            {isBrowserOpen && <TerminologyBrowser onClose={() => setIsBrowserOpen(false)} />}
            
            <h3 className="text-xl font-semibold mb-3 text-gray-200">Global Terminology Tables</h3>
            <div className="mb-6 p-4 bg-gray-900/50 rounded-lg grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <div className="flex items-center gap-4">
                        <div>
                            <p className="text-sm text-gray-400">Loaded Tables</p>
                            <p className="text-2xl font-bold text-white">{stats ? stats.table_count.toLocaleString() : '...'}</p>
                        </div>
                        {/* --- THE NEW BUTTON --- */}
                        <button 
                            onClick={() => setIsBrowserOpen(true)}
                            className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white text-sm font-bold rounded-lg"
                        >
                            Browse
                        </button>
                    </div>
                </div>
                <div>
                    <p className="text-sm text-gray-400">Total Definitions</p>
                    <p className="text-2xl font-bold text-white">{stats ? stats.definition_count.toLocaleString() : '...'}</p>
                </div>
                <div>
                    <p className="text-sm text-gray-400">Last Updated (UTC)</p>
                    <p className="text-lg font-semibold text-gray-300">{stats ? (stats.last_updated ? new Date(stats.last_updated).toLocaleString() : 'Never') : '...'}</p>
                </div>
            </div>

            <p className="text-gray-400 mb-4 max-w-2xl">
                This will connect to terminology.hl7.org and download the latest V2 code systems.
            </p>
            
            <div className="mt-6">
                <button
                    onClick={handleRefresh}
                    disabled={isLoading}
                    className="flex items-center justify-center px-6 py-3 bg-red-600 text-white font-bold rounded-lg shadow-md hover:bg-red-700 disabled:bg-red-900 disabled:cursor-not-allowed transition-colors"
                >
                    Refresh All V2 Terminology
                </button>
            </div>
            
            {isLoading && (
                <div className="mt-4 p-4 bg-gray-900 rounded-md max-w-2xl">
                    <p className="text-sm font-semibold text-indigo-300">Working...</p>
                    <p className="text-xs text-gray-400 mt-1">{progressMessage}</p>
                    <ProgressBar progress={progress} />
                </div>
            )}
        </div>
    );
};

export default TerminologyManagement;

// --- END OF FILE src/components/TerminologyManagement.jsx ---