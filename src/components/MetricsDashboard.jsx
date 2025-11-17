// --- START OF FILE src/components/MetricsDashboard.jsx ---
import React, { useEffect, useState, useMemo } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import {
    fetchRunMetrics,
    fetchWorkerMetrics,
    downloadRunMetricsCsv,
    downloadWorkerMetricsCsv,
} from '../api/metrics';
import { useAuth } from '../context/AuthContext';
import YeetLoader from './YeetLoader';
import Sparkline from './Sparkline';

const initialRunSummary = {
    run_count: 0,
    total_patients: 0,
    total_worker_jobs: 0,
    total_worker_success: 0,
    total_dicom_instances: 0,
    total_dicom_bytes: 0,
    average_orders_per_second: null,
};

const initialWorkerSummary = {
    job_count: 0,
    success_count: 0,
    failure_count: 0,
    average_duration_ms: null,
};

const numberFormatter = new Intl.NumberFormat();

const formatNumber = (value) => {
    if (value === null || value === undefined) {
        return '—';
    }
    return numberFormatter.format(value);
};

const formatFloat = (value, fractionDigits = 2) => {
    if (value === null || value === undefined) {
        return '—';
    }
    return Number(value).toFixed(fractionDigits);
};

const formatBytes = (bytes) => {
    if (!bytes) {
        return '—';
    }
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }
    return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
};

const formatDateTime = (value) => {
    if (!value) {
        return '—';
    }
    return new Date(value).toLocaleString();
};

const SummaryCard = ({ label, value, hint }) => (
    <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
        <p className="text-sm text-gray-400">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-gray-100">{value}</p>
        {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
    </div>
);

const MetricsDashboard = () => {
    const { isAuthenticated } = useAuth();

    const [runData, setRunData] = useState([]);
    const [runSummary, setRunSummary] = useState(initialRunSummary);
    const [runLoading, setRunLoading] = useState(false);
    const [runFilters, setRunFilters] = useState({
        limit: '50',
        template_id: '',
        status: '',
        start_at: '',
        end_at: '',
    });
    const [runQuery, setRunQuery] = useState(runFilters);

    const [workerData, setWorkerData] = useState([]);
    const [workerSummary, setWorkerSummary] = useState(initialWorkerSummary);
    const [workerLoading, setWorkerLoading] = useState(false);
    const [workerFilters, setWorkerFilters] = useState({
        limit: '200',
        run_id: '',
        queue: '',
        success: '',
    });
    const [workerQuery, setWorkerQuery] = useState(workerFilters);
    const [selectedRunId, setSelectedRunId] = useState(null);

    const normalizeRunQuery = (filters) => {
        const toIso = (value) => (value ? new Date(value).toISOString() : undefined);
        return {
            limit: filters.limit || undefined,
            template_id: filters.template_id || undefined,
            status: filters.status || undefined,
            start_at: toIso(filters.start_at),
            end_at: toIso(filters.end_at),
        };
    };

    const normalizeWorkerQuery = (filters) => ({
        limit: filters.limit || undefined,
        run_id: filters.run_id || undefined,
        queue: filters.queue || undefined,
        success: filters.success || undefined,
    });

    const loadRunMetrics = async (query) => {
        setRunLoading(true);
        try {
            const data = await fetchRunMetrics(query);
            setRunData(data?.runs || []);
            setRunSummary({ ...initialRunSummary, ...(data?.summary || {}) });
        } catch (error) {
            toast.error(error.message || 'Failed to load run metrics');
        } finally {
            setRunLoading(false);
        }
    };

    const loadWorkerMetrics = async (query) => {
        setWorkerLoading(true);
        try {
            const data = await fetchWorkerMetrics(query);
            setWorkerData(data?.metrics || []);
            setWorkerSummary({ ...initialWorkerSummary, ...(data?.summary || {}) });
        } catch (error) {
            toast.error(error.message || 'Failed to load worker metrics');
        } finally {
            setWorkerLoading(false);
        }
    };

    const workerDurationTrend = useMemo(() => {
        if (!Array.isArray(runData) || runData.length === 0) {
            return [];
        }
        return [...runData]
            .filter((run) => run.worker_job_duration_avg_ms !== null && run.worker_job_duration_avg_ms !== undefined)
            .sort((a, b) => {
                const aTime = new Date(a.completed_at || a.started_at || 0).getTime();
                const bTime = new Date(b.completed_at || b.started_at || 0).getTime();
                return aTime - bTime;
            })
            .map((run) => Number(run.worker_job_duration_avg_ms));
    }, [runData]);

    const workerDurationLatest = workerDurationTrend.length
        ? workerDurationTrend[workerDurationTrend.length - 1]
        : null;

    useEffect(() => {
        if (!isAuthenticated) {
            return;
        }
        loadRunMetrics(normalizeRunQuery(runQuery));
    }, [isAuthenticated, runQuery]);

    useEffect(() => {
        if (!isAuthenticated) {
            return;
        }
        loadWorkerMetrics(normalizeWorkerQuery(workerQuery));
    }, [isAuthenticated, workerQuery]);

    if (!isAuthenticated) {
        return <Navigate to="/login" />;
    }

    const handleApplyRunFilters = (event) => {
        event.preventDefault();
        setRunQuery(runFilters);
    };

    const handleResetRunFilters = () => {
        const defaults = { limit: '50', template_id: '', status: '', start_at: '', end_at: '' };
        setRunFilters(defaults);
        setRunQuery(defaults);
    };

    const handleApplyWorkerFilters = (event) => {
        event.preventDefault();
        setWorkerQuery(workerFilters);
    };

    const handleResetWorkerFilters = () => {
        const defaults = { limit: '200', run_id: '', queue: '', success: '' };
        setWorkerFilters(defaults);
        setWorkerQuery(defaults);
        setSelectedRunId(null);
    };

    const handleRunRowClick = (runId) => {
        setSelectedRunId(runId);
        setWorkerFilters((prev) => ({ ...prev, run_id: String(runId) }));
        setWorkerQuery((prev) => ({ ...prev, run_id: String(runId) }));
    };

    const handleDownloadRuns = async () => {
        try {
            await downloadRunMetricsCsv(normalizeRunQuery(runQuery));
        } catch (error) {
            toast.error(error.message || 'Failed to download run metrics');
        }
    };

    const handleDownloadWorkers = async () => {
        try {
            await downloadWorkerMetricsCsv(normalizeWorkerQuery(workerQuery));
        } catch (error) {
            toast.error(error.message || 'Failed to download worker metrics');
        }
    };

    const ordersPerSecondHint = runSummary.average_orders_per_second
        ? 'Average across selected runs.'
        : 'Average calculated across runs with wall clock measurements.';

    return (
        <div className="space-y-8">
            <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-100">Simulation Metrics</h1>
                    <p className="text-sm text-gray-400">Review run throughput, queue timings, and worker outcomes.</p>
                </div>
                <div className="flex gap-3">
                    <Link to="/" className="rounded-md border border-gray-700 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800">
                        Back to Dashboard
                    </Link>
                    <button
                        onClick={() => loadRunMetrics(normalizeRunQuery(runQuery))}
                        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
                    >
                        Refresh
                    </button>
                </div>
            </header>

            <section className="space-y-4">
                <h2 className="text-2xl font-semibold text-gray-100">Run Overview</h2>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <SummaryCard label="Runs" value={formatNumber(runSummary.run_count)} />
                    <SummaryCard label="Total Patients" value={formatNumber(runSummary.total_patients)} />
                    <SummaryCard label="Worker Jobs" value={formatNumber(runSummary.total_worker_jobs)} hint={formatNumber(runSummary.total_worker_success) + ' successful'} />
                    <SummaryCard label="Orders / Second" value={formatFloat(runSummary.average_orders_per_second, 2)} hint={ordersPerSecondHint} />
                    <SummaryCard label="DICOM Instances" value={formatNumber(runSummary.total_dicom_instances)} hint={`${formatBytes(runSummary.total_dicom_bytes)} transferred`} />
                </div>

                {workerDurationTrend.length > 1 && (
                    <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 shadow-sm">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Worker Duration Trend</p>
                                <p className="mt-1 text-2xl font-semibold text-gray-100">{formatFloat(workerDurationLatest, 2)} ms</p>
                                <p className="mt-1 text-xs text-gray-500">Average worker runtime across the last {workerDurationTrend.length} completed runs.</p>
                            </div>
                            <Sparkline data={workerDurationTrend} className="sm:ml-4" />
                        </div>
                    </div>
                )}

                <form onSubmit={handleApplyRunFilters} className="grid gap-4 rounded-lg border border-gray-700 bg-gray-800 p-4 md:grid-cols-6">
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Limit</label>
                        <input
                            type="number"
                            min="1"
                            max="1000"
                            value={runFilters.limit}
                            onChange={(event) => setRunFilters((prev) => ({ ...prev, limit: event.target.value }))}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Template ID</label>
                        <input
                            type="number"
                            min="1"
                            value={runFilters.template_id}
                            onChange={(event) => setRunFilters((prev) => ({ ...prev, template_id: event.target.value }))}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Status</label>
                        <input
                            type="text"
                            value={runFilters.status}
                            onChange={(event) => setRunFilters((prev) => ({ ...prev, status: event.target.value }))}
                            placeholder="COMPLETED"
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Start After</label>
                        <input
                            type="datetime-local"
                            value={runFilters.start_at}
                            onChange={(event) => setRunFilters((prev) => ({ ...prev, start_at: event.target.value }))}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Completed Before</label>
                        <input
                            type="datetime-local"
                            value={runFilters.end_at}
                            onChange={(event) => setRunFilters((prev) => ({ ...prev, end_at: event.target.value }))}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-2 flex items-end gap-2">
                        <button type="submit" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">Apply</button>
                        <button type="button" onClick={handleResetRunFilters} className="rounded-md border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800">Reset</button>
                        <button type="button" onClick={handleDownloadRuns} className="rounded-md border border-indigo-500 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-500 hover:text-white">Download CSV</button>
                    </div>
                </form>

                <div className="overflow-x-auto rounded-lg border border-gray-700">
                    <table className="min-w-full divide-y divide-gray-700">
                        <thead className="bg-gray-800">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Run ID</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Template</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Status</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Patients</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Queue Avg (ms)</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Worker Avg (ms)</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Orders / s</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Started</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Completed</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800 bg-gray-900">
                            {runLoading ? (
                                <tr>
                                    <td colSpan="9" className="px-4 py-8">
                                        <div className="flex items-center justify-center">
                                            <YeetLoader />
                                        </div>
                                    </td>
                                </tr>
                            ) : runData.length === 0 ? (
                                <tr>
                                    <td colSpan="9" className="px-4 py-8 text-center text-sm text-gray-400">
                                        No runs found for the selected filters.
                                    </td>
                                </tr>
                            ) : (
                                runData.map((run) => (
                                    <tr
                                        key={run.run_id}
                                        className={`cursor-pointer hover:bg-gray-800 ${selectedRunId === run.run_id ? 'bg-gray-800' : ''}`}
                                        onClick={() => handleRunRowClick(run.run_id)}
                                    >
                                        <td className="px-4 py-2 text-sm text-gray-100">{run.run_id}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{run.template_name || '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{run.status || '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{formatNumber(run.total_patients)}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{formatFloat(run.queue_publish_avg_ms)}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{formatFloat(run.worker_job_duration_avg_ms)}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{formatFloat(run.orders_per_second)}</td>
                                        <td className="px-4 py-2 text-sm text-gray-300">{formatDateTime(run.started_at)}</td>
                                        <td className="px-4 py-2 text-sm text-gray-300">{formatDateTime(run.completed_at)}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            <section className="space-y-4">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <h2 className="text-2xl font-semibold text-gray-100">Worker Jobs</h2>
                    {selectedRunId && (
                        <p className="text-sm text-indigo-300">Filtering by run {selectedRunId}</p>
                    )}
                </div>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <SummaryCard label="Jobs" value={formatNumber(workerSummary.job_count)} />
                    <SummaryCard label="Success" value={formatNumber(workerSummary.success_count)} />
                    <SummaryCard label="Failures" value={formatNumber(workerSummary.failure_count)} />
                    <SummaryCard label="Average Duration (ms)" value={formatFloat(workerSummary.average_duration_ms)} />
                </div>

                <form onSubmit={handleApplyWorkerFilters} className="grid gap-4 rounded-lg border border-gray-700 bg-gray-800 p-4 md:grid-cols-5">
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Limit</label>
                        <input
                            type="number"
                            min="1"
                            max="2000"
                            value={workerFilters.limit}
                            onChange={(event) => setWorkerFilters((prev) => ({ ...prev, limit: event.target.value }))}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Run ID</label>
                        <input
                            type="number"
                            min="1"
                            value={workerFilters.run_id}
                                onChange={(event) => {
                                    const { value } = event.target;
                                    setWorkerFilters((prev) => ({ ...prev, run_id: value }));
                                    setSelectedRunId(value ? Number(value) : null);
                                }}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Queue</label>
                        <input
                            type="text"
                            value={workerFilters.queue}
                            onChange={(event) => setWorkerFilters((prev) => ({ ...prev, queue: event.target.value }))}
                            placeholder="default"
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <label className="text-xs uppercase tracking-wide text-gray-400">Success</label>
                        <select
                            value={workerFilters.success}
                            onChange={(event) => setWorkerFilters((prev) => ({ ...prev, success: event.target.value }))}
                            className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-sm text-gray-100"
                        >
                            <option value="">Any</option>
                            <option value="true">Success</option>
                            <option value="false">Failure</option>
                        </select>
                    </div>
                    <div className="md:col-span-2 flex items-end gap-2">
                        <button type="submit" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">Apply</button>
                        <button type="button" onClick={handleResetWorkerFilters} className="rounded-md border border-gray-600 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-800">Reset</button>
                        <button type="button" onClick={handleDownloadWorkers} className="rounded-md border border-indigo-500 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-500 hover:text-white">Download CSV</button>
                    </div>
                </form>

                <div className="overflow-x-auto rounded-lg border border-gray-700">
                    <table className="min-w-full divide-y divide-gray-700">
                        <thead className="bg-gray-800">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">ID</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Run</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Queue</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Success</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Outcome</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Duration (ms)</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Steps</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Remaining</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Patient Iteration</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Error</th>
                                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">Created</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800 bg-gray-900">
                            {workerLoading ? (
                                <tr>
                                    <td colSpan="11" className="px-4 py-8">
                                        <div className="flex items-center justify-center">
                                            <YeetLoader />
                                        </div>
                                    </td>
                                </tr>
                            ) : workerData.length === 0 ? (
                                <tr>
                                    <td colSpan="11" className="px-4 py-8 text-center text-sm text-gray-400">
                                        No worker metrics found for the selected filters.
                                    </td>
                                </tr>
                            ) : (
                                workerData.map((job) => (
                                    <tr key={job.id} className="hover:bg-gray-800">
                                        <td className="px-4 py-2 text-sm text-gray-100">{job.id}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.run_id}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.queue || '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.success ? 'Yes' : 'No'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.outcome || '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{formatFloat(job.duration_ms)}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.steps_executed ?? '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.remaining_steps ?? '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.patient_iteration ?? '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-200">{job.error || '—'}</td>
                                        <td className="px-4 py-2 text-sm text-gray-300">{formatDateTime(job.created_at)}</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
};

export default MetricsDashboard;
// --- END OF FILE src/components/MetricsDashboard.jsx ---
