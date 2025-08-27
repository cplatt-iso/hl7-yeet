import React, { useState, useEffect, useRef, useCallback } from 'react';
import { getSimulationRunApi } from '../api/simulator';
import { toast } from 'react-hot-toast';

const SimulationRunLog = ({ runId, onBack }) => {
    const [runDetails, setRunDetails] = useState(null);
    const [events, setEvents] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const logContainerRef = useRef(null);
    const refreshIntervalRef = useRef(null);

    const fetchRunData = useCallback(async () => {
        try {
            const data = await getSimulationRunApi(runId);
            setRunDetails(data);
            setEvents(data.events || []);
        } catch(error) {
            console.error('Failed to load run details:', error);
            toast.error(`Failed to load run details: ${error.message}`);
        }
    }, [runId]);

    useEffect(() => {
        const initialLoad = async () => {
            setIsLoading(true);
            await fetchRunData();
            setIsLoading(false);
        };
        initialLoad();
    }, [fetchRunData]);

    // Auto-refresh polling
    useEffect(() => {
        if (autoRefresh) {
            refreshIntervalRef.current = setInterval(() => {
                fetchRunData();
            }, 2000);
        } else {
            if (refreshIntervalRef.current) {
                clearInterval(refreshIntervalRef.current);
                refreshIntervalRef.current = null;
            }
        }

        return () => {
            if (refreshIntervalRef.current) {
                clearInterval(refreshIntervalRef.current);
            }
        };
    }, [autoRefresh, fetchRunData]);

    // Auto-scroll to bottom when new events arrive
    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [events]);

    const getStatusColor = (status) => {
        if (status === 'SUCCESS') return 'text-green-400';
        if (status === 'FAILURE') return 'text-red-400';
        if (status === 'INFO') return 'text-blue-400';
        return 'text-gray-400';
    };

    return (
        <div>
            <button onClick={onBack} className="mb-4 text-sm text-indigo-400 hover:text-indigo-300">
                ← Back to Dashboard
            </button>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h3 className="text-xl font-bold">Log for Run #{runDetails?.id}</h3>
                        <p className="text-sm text-gray-400">
                            Status: <span className="font-semibold">{runDetails?.status}</span>
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => fetchRunData()}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium"
                        >
                            Refresh Now
                        </button>
                        <button 
                            onClick={() => setAutoRefresh(!autoRefresh)}
                            className={`px-3 py-1 rounded text-xs font-medium ${
                                autoRefresh 
                                    ? 'bg-green-600 hover:bg-green-700 text-white' 
                                    : 'bg-gray-600 hover:bg-gray-700 text-white'
                            }`}
                        >
                            {autoRefresh ? '🟢 Auto-refresh ON' : '🔴 Auto-refresh OFF'}
                        </button>
                    </div>
                </div>
                <div 
                    ref={logContainerRef} 
                    className="mt-4 h-[60vh] bg-black rounded p-2 font-mono text-xs overflow-y-auto"
                >
                    {isLoading ? (
                        <p className="text-gray-500">Loading run details...</p>
                    ) : events.length > 0 ? (
                        events.map(event => (
                            <div key={event.id} className="flex gap-2 items-start mb-1">
                                <span className="text-gray-500 flex-shrink-0">
                                    {new Date(event.timestamp).toLocaleTimeString()}
                                </span>
                                <span className={`${getStatusColor(event.status)} font-bold w-16 text-right flex-shrink-0`}>
                                    {event.status}
                                </span>
                                <span className="text-gray-600">
                                    (Iter:{event.iteration}, Step:{event.step_order})
                                </span>
                                <span className="text-gray-300 whitespace-pre-wrap break-words">
                                    {event.details}
                                </span>
                            </div>
                        ))
                    ) : (
                        <p className="text-gray-500">
                            No log events yet. {runDetails?.status === 'RUNNING' ? 'Simulation is starting...' : ''}
                        </p>
                    )}
                </div>
                <div className="mt-2 text-xs text-gray-500">
                    {events.length} events • Last updated: {new Date().toLocaleTimeString()}
                    {autoRefresh && <span className="ml-2">• Auto-refreshing every 2s</span>}
                </div>
            </div>
        </div>
    );
};

export default SimulationRunLog;
