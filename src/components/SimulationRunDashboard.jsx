// --- REPLACE src/components/SimulationRunDashboard.jsx ---
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { getSimulationTemplatesApi, runSimulationApi, getSimulationRunsApi } from '../api/simulator';
import SimulationRunLog from './SimulationRunLog';

const SimulationRunDashboard = () => {
    const [templates, setTemplates] = useState([]);
    const [runs, setRuns] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedTemplateId, setSelectedTemplateId] = useState('');
    const [patientCount, setPatientCount] = useState(1);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [viewingRunId, setViewingRunId] = useState(null);

    const fetchDashboardData = () => {
        setIsLoading(true);
        Promise.all([
            getSimulationTemplatesApi(),
            getSimulationRunsApi()
        ]).then(([templatesData, runsData]) => {
            setTemplates(templatesData);
            setRuns(runsData);
        }).catch(err => {
            toast.error(`Failed to load dashboard data: ${err.message}`);
        }).finally(() => {
            setIsLoading(false);
        });
    };

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedTemplateId) {
            toast.error("Please select a workflow template.");
            return;
        }
        setIsSubmitting(true);
        const toastId = toast.loading('Initiating simulation...');
        try {
            const result = await runSimulationApi(selectedTemplateId, patientCount);
            toast.success(`Run #${result.run_id} started!`, { id: toastId });
            setViewingRunId(result.run_id);
            fetchDashboardData(); // Refresh history
        } catch (error) {
            toast.error(`Failed to start: ${error.message}`, { id: toastId });
        } finally {
            setIsSubmitting(false);
        }
    };

    if (viewingRunId) {
        return <SimulationRunLog runId={viewingRunId} onBack={() => setViewingRunId(null)} />;
    }

    return (
        <div>
            {/* ... (form is the same) ... */}
            <h3 className="text-xl font-bold mb-4 text-gray-200">Run a Simulation</h3>
            <form onSubmit={handleSubmit} className="p-4 bg-gray-900 rounded-lg grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-gray-400">Workflow Template</label>
                    <select value={selectedTemplateId} onChange={(e) => setSelectedTemplateId(e.target.value)} className="bg-gray-800 p-2 rounded border border-gray-700 h-10">
                        <option value="">-- Select a Workflow --</option>
                        {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                </div>
                <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-gray-400">Patient Count</label>
                    <input type="number" value={patientCount} onChange={(e) => setPatientCount(parseInt(e.target.value, 10))} min="1" className="bg-gray-800 p-2 rounded border border-gray-700 h-10"/>
                </div>
                <button type="submit" disabled={isSubmitting || !selectedTemplateId} className="p-2 h-10 bg-green-600 hover:bg-green-700 rounded font-bold disabled:bg-gray-600">
                    {isSubmitting ? 'Starting...' : 'Run Simulation'}
                </button>
            </form>

            <h3 className="text-xl font-bold mt-8 mb-4 text-gray-200">Run History</h3>
            <div className="bg-gray-900 rounded-lg overflow-hidden">
                <table className="w-full text-left text-sm">
                     <thead className="bg-gray-950 text-xs text-gray-400 uppercase">
                         <tr>
                            <th className="p-3">Run ID</th>
                            <th className="p-3">Template ID</th>
                            <th className="p-3">Status</th>
                            <th className="p-3">Started At (UTC)</th>
                            <th className="p-3">Actions</th>
                         </tr>
                     </thead>
                     <tbody>
                        {isLoading ? (
                             <tr><td colSpan="5" className="p-4 text-center">Loading...</td></tr>
                        ) : runs.length === 0 ? (
                            <tr><td colSpan="5" className="p-4 text-center text-gray-500">No simulation runs found.</td></tr>
                        ) : (
                            runs.map(run => (
                                <tr key={run.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                                    <td className="p-3 font-mono">{run.id}</td>
                                    <td className="p-3">{run.template_id}</td>
                                    <td className="p-3 font-semibold">{run.status}</td>
                                    <td className="p-3">{run.started_at ? new Date(run.started_at).toLocaleString('en-GB', { timeZone: 'UTC' }) : 'N/A'}</td>
                                    <td className="p-3">
                                        <button onClick={() => setViewingRunId(run.id)} className="text-indigo-400 hover:underline">View Log</button>
                                    </td>
                                </tr>
                            ))
                        )}
                     </tbody>
                </table>
            </div>
        </div>
    );
};

export default SimulationRunDashboard;