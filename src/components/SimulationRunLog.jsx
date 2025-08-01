// --- REPLACE src/components/SimulationRunLog.jsx ---
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { getSimulationRunApi } from '../api/simulator';
import { toast } from 'react-hot-toast';

const SimulationRunLog = ({ runId, onBack }) => {
    const { socket } = useAuth();
    const [runDetails, setRunDetails] = useState(null);
    const [events, setEvents] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const logContainerRef = useRef(null);

    useEffect(() => {
        const fetchInitialData = async () => {
            setIsLoading(true);
            try {
                const data = await getSimulationRunApi(runId);
                setRunDetails(data);
                setEvents(data.events);
            } catch(error) {
                toast.error(`Failed to load run details: ${error.message}`);
            } finally {
                setIsLoading(false);
            }
        };
        fetchInitialData();
    }, [runId]);

    useEffect(() => {
        if (socket) {
            socket.emit('join_run_room', { run_id: runId });
            const handleLogUpdate = (data) => {
                if (data.run_id === runId) {
                    setEvents(prev => [...prev, data.event]);
                }
            };
            socket.on('sim_log_update', handleLogUpdate);
            return () => {
                socket.emit('leave_run_room', { run_id: runId });
                socket.off('sim_log_update', handleLogUpdate);
            };
        }
    }, [socket, runId]);

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
            <button onClick={onBack} className="mb-4 text-sm text-indigo-400 hover:text-indigo-300">← Back to Dashboard</button>
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <h3 className="text-xl font-bold">Log for Run #{runDetails?.id}</h3>
                <p className="text-sm text-gray-400">Status: <span className="font-semibold">{runDetails?.status}</span></p>
                <div ref={logContainerRef} className="mt-4 h-[60vh] bg-black rounded p-2 font-mono text-xs overflow-y-auto">
                    {isLoading ? <p>Loading log history...</p> : events.map(event => (
                        <div key={event.id} className="flex gap-2 items-start">
                            <span className="text-gray-500 flex-shrink-0">{new Date(event.timestamp).toLocaleTimeString()}</span>
                            <span className={`${getStatusColor(event.status)} font-bold w-16 text-right flex-shrink-0`}>{event.status}</span>
                            <span className="text-gray-600">(Iter:{event.iteration}, Step:{event.step_order})</span>
                            <span className="text-gray-300 whitespace-pre-wrap break-words">{event.details}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default SimulationRunLog;