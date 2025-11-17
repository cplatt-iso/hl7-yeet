import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { getSimulationRunApi, getSimulationRunMetricsApi } from '../api/simulator';
import { toast } from 'react-hot-toast';
import { io } from 'socket.io-client';
import { InformationCircleIcon } from '@heroicons/react/24/outline';
import { API_BASE_URL } from '../api/config';

const EVENT_FETCH_LIMIT = 2000;
const MAX_EVENT_BUFFER = 4000;
const WORKER_JOBS_FETCH_LIMIT = 200;

const calculatePercentile = (sortedValues, percentile) => {
    if (!sortedValues.length) {
        return null;
    }
    if (sortedValues.length === 1) {
        return sortedValues[0];
    }
    const clamped = Math.min(Math.max(percentile, 0), 100);
    const index = Math.floor((clamped / 100) * (sortedValues.length - 1));
    return sortedValues[index];
};

const computeBarWidthPercentage = (value, maxValue) => {
    if (value === null || value === undefined || !maxValue) {
        return 0;
    }
    const ratio = (Number(value) / maxValue) * 100;
    if (!Number.isFinite(ratio) || ratio <= 0) {
        return 4;
    }
    return Math.min(100, Math.max(4, ratio));
};

const METRIC_TOOLTIPS = {
    patients: 'Unique patient iterations executed for this run. Include repeats defined on the template.',
    queuedJobs: 'Total asynchronous jobs enqueued while the run executed. Retries count as additional jobs.',
    queuedJobDepth: 'RabbitMQ depth observed when jobs were published. Spikes indicate backlog growth.',
    workerSuccess: 'Worker job outcomes collected from the metrics feed. Helps confirm retries vs failures.',
    workerDuration: 'Distribution of worker job runtimes measured by the workers themselves.',
    ordersPerSecond: 'Average number of jobs dispatched per second across the full wall-clock window.',
    queuePublish: 'Time spent publishing jobs to RabbitMQ. Higher latency can signal broker or network contention.',
    dicomSuccess: 'Instances successfully sent compared with attempted instances across all DICOM sends.',
    dicomBytes: 'Total payload volume delivered via successful DICOM sends.',
    dicomThroughput: 'Observed network throughput for DICOM sends, derived from payload size and send duration.',
    dicomSendLatency: 'Aggregated C-STORE send durations from the simulator perspective.',
    runWindow: 'Backend timestamps showing when the run started and when it finished.',
    stepDurations: 'Aggregate timing for each simulation step order. Useful for spotting slow links in the workflow.',
    wallClock: 'Total elapsed wall-clock time calculated from the run start and completion timestamps.',
    slowestStep: 'Step with the highest average duration across the run. Handy for identifying workflow bottlenecks.',
};

const TooltipIcon = ({ message, label }) => {
    if (!message) {
        return null;
    }
    return (
        <span
            className="relative inline-flex cursor-help items-center group focus-within:outline-none"
            tabIndex={0}
            aria-label={label}
        >
            <InformationCircleIcon
                className="h-4 w-4 text-gray-400 group-hover:text-indigo-300 group-focus:text-indigo-300"
                aria-hidden="true"
            />
            <span className="pointer-events-none absolute left-1/2 top-full z-20 hidden w-64 -translate-x-1/2 rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-200 shadow-lg group-hover:block group-focus:block">
                {message}
            </span>
        </span>
    );
};

const MetricCard = ({ title, tooltipKey, primary, children }) => (
    <div className="rounded-md border border-gray-800 bg-gray-950 p-3">
        <div className="flex items-center justify-between text-xs uppercase text-gray-500">
            <span>{title}</span>
            <TooltipIcon message={tooltipKey ? METRIC_TOOLTIPS[tooltipKey] : null} label={`${title} help`} />
        </div>
        <p className="mt-1 text-xl font-semibold text-gray-100">{primary}</p>
        {children}
    </div>
);

const formatThroughput = (mbps) => {
    if (mbps === null || mbps === undefined) {
        return '—';
    }
    const value = Number(mbps);
    if (!Number.isFinite(value)) {
        return '—';
    }
    if (value >= 1000) {
        const gbps = value / 1000;
        return `${value.toFixed(2)} Mbit/s (${gbps.toFixed(2)} Gbit/s)`;
    }
    return `${value.toFixed(2)} Mbit/s`;
};

const formatSeconds = (seconds) => {
    if (seconds === null || seconds === undefined) {
        return '—';
    }
    const value = Number(seconds);
    if (!Number.isFinite(value)) {
        return '—';
    }
    if (value < 1) {
        return `${value.toFixed(2)} s`;
    }
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const secs = value % 60;
    const parts = [];
    if (hours) {
        parts.push(`${hours}h`);
    }
    if (minutes) {
        parts.push(`${minutes}m`);
    }
    if (secs >= 1 || parts.length === 0) {
        const precision = secs >= 10 ? 0 : 1;
        parts.push(`${secs.toFixed(precision)}s`);
    }
    return parts.join(' ');
};

const formatStepTypeLabel = (value) => {
    if (!value || typeof value !== 'string') {
        return 'Unknown';
    }
    return value
        .toLowerCase()
        .split('_')
        .map((segment) => (segment ? segment.charAt(0).toUpperCase() + segment.slice(1) : ''))
        .join(' ');
};

const SimulationRunLog = ({ runId, onBack }) => {
    const [runDetails, setRunDetails] = useState(null);
    const [events, setEvents] = useState([]);
    const [eventsMeta, setEventsMeta] = useState({
        total: 0,
        remaining: 0,
        truncated: false,
        limit: EVENT_FETCH_LIMIT,
        offset: 0,
        order: 'desc',
    });
    const [isLoading, setIsLoading] = useState(true);
    const [metrics, setMetrics] = useState(null);
    const [workerJobs, setWorkerJobs] = useState([]);
    const [workerJobsMeta, setWorkerJobsMeta] = useState({
        total: 0,
        remaining: 0,
        truncated: false,
        limit: WORKER_JOBS_FETCH_LIMIT,
        offset: 0,
        order: 'desc',
        returned: 0,
    });
    const [isLoadingWorkerJobs, setIsLoadingWorkerJobs] = useState(false);
    const [queuedJobs, setQueuedJobs] = useState([]);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const logContainerRef = useRef(null);
    const refreshIntervalRef = useRef(null);
    const socketRef = useRef(null);
    const workerJobsRef = useRef([]);
    const workerJobsOptionsRef = useRef({
        limit: WORKER_JOBS_FETCH_LIMIT,
        offset: 0,
        order: 'desc',
    });
    const workerJobsMetaRef = useRef(workerJobsMeta);

    const numberFormatter = new Intl.NumberFormat();

    const escapeCsvValue = (value) => {
        if (value === null || value === undefined) {
            return '';
        }
        const stringValue = String(value).replace(/"/g, '""');
        return `"${stringValue}"`;
    };

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

    const formatDateTime = (value) => {
        if (!value) {
            return '—';
        }
        return new Date(value).toLocaleString();
    };

    const fetchRunData = useCallback(async (options = {}) => {
        const {
            refreshEvents = true,
            jobsOffset,
            jobsLimit,
            jobsOrder,
        } = options;

        try {
            const metricsOptions = {
                jobsLimit: jobsLimit ?? workerJobsOptionsRef.current.limit ?? WORKER_JOBS_FETCH_LIMIT,
                jobsOffset: jobsOffset ?? workerJobsOptionsRef.current.offset ?? 0,
                jobsOrder: jobsOrder ?? workerJobsOptionsRef.current.order ?? 'desc',
            };

            const runPromise = refreshEvents
                ? getSimulationRunApi(runId, { eventsLimit: EVENT_FETCH_LIMIT, eventsOrder: 'desc' })
                : Promise.resolve(null);

            const [runData, metricsData] = await Promise.all([
                runPromise,
                getSimulationRunMetricsApi(runId, metricsOptions),
            ]);

            if (runData) {
                setRunDetails(runData);
                const serverEvents = runData.events || [];
                setEvents(serverEvents);
                setEventsMeta(prev => ({
                    ...prev,
                    total: runData.events_total ?? serverEvents.length,
                    remaining: runData.events_remaining ?? Math.max((runData.events_total ?? serverEvents.length) - serverEvents.length, 0),
                    truncated: Boolean(runData.events_truncated),
                    limit: runData.events_limit ?? EVENT_FETCH_LIMIT,
                    offset: runData.events_offset ?? 0,
                    order: runData.events_order ?? 'desc',
                }));
            }

            if (metricsData) {
                const latestPage = (metricsOptions.jobsOffset || 0) === 0;
                setMetrics(metricsData);
                const nextWorkerJobs = Array.isArray(metricsData.worker_jobs)
                    ? [...metricsData.worker_jobs].sort((a, b) => {
                        const aTime = new Date(a.created_at || 0).getTime();
                        const bTime = new Date(b.created_at || 0).getTime();
                        return aTime - bTime;
                    })
                    : [];
                setWorkerJobs(nextWorkerJobs);

                setQueuedJobs(prev => {
                    if (!latestPage || !prev.length) {
                        return prev;
                    }
                    const resolvedIds = new Set(
                        nextWorkerJobs.map(job => job.job_id || job.id)
                    );
                    return prev.filter(job => {
                        if (!job.job_id) {
                            return true;
                        }
                        return !resolvedIds.has(job.job_id);
                    });
                });

                const totalWorkerMetrics = metricsData.worker_jobs_total ?? nextWorkerJobs.length;
                const returnedCount = metricsData.worker_jobs_returned ?? nextWorkerJobs.length;
                const responseLimit = metricsData.worker_jobs_limit ?? metricsOptions.jobsLimit;
                const responseOffset = metricsData.worker_jobs_offset ?? metricsOptions.jobsOffset ?? 0;
                const responseOrder = metricsData.worker_jobs_order ?? metricsOptions.jobsOrder;
                const remainingCount = metricsData.worker_jobs_remaining ?? Math.max(totalWorkerMetrics - (responseOffset + returnedCount), 0);
                const truncated = metricsData.worker_jobs_truncated ?? (remainingCount > 0 || responseOffset > 0);

                const meta = {
                    total: totalWorkerMetrics,
                    remaining: remainingCount,
                    truncated: Boolean(truncated),
                    limit: responseLimit,
                    offset: responseOffset,
                    order: responseOrder,
                    returned: returnedCount,
                };

                setWorkerJobsMeta(meta);
                workerJobsMetaRef.current = meta;
                workerJobsOptionsRef.current = {
                    limit: meta.limit ?? WORKER_JOBS_FETCH_LIMIT,
                    offset: meta.offset ?? 0,
                    order: meta.order ?? 'desc',
                };
            }
        } catch (error) {
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

    useEffect(() => {
        workerJobsRef.current = workerJobs;
    }, [workerJobs]);

    useEffect(() => {
        workerJobsMetaRef.current = workerJobsMeta;
    }, [workerJobsMeta]);

    const trimWorkerJobsToLimit = useCallback((jobs) => {
        const { limit = WORKER_JOBS_FETCH_LIMIT } = workerJobsMetaRef.current || {};
        if (!limit || workerJobsOptionsRef.current.offset !== 0) {
            return jobs;
        }
        if (jobs.length > limit) {
            return jobs.slice(jobs.length - limit);
        }
        return jobs;
    }, []);

    const getStatusColor = (status) => {
        if (status === 'SUCCESS') return 'text-green-400';
        if (status === 'FAILURE') return 'text-red-400';
        if (status === 'INFO') return 'text-blue-400';
        return 'text-gray-400';
    };

    useEffect(() => {
        const token = localStorage.getItem('authToken');
        const socketUrl = import.meta.env.VITE_SOCKET_URL || API_BASE_URL;

        const socketInstance = io(socketUrl, {
            auth: token ? { token } : undefined,
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5,
        });

        socketRef.current = socketInstance;

        const handleLogUpdate = (payload) => {
            if (!payload || payload.run_id !== runId || !payload.event) {
                return;
            }
            setEvents(prevEvents => {
                if (prevEvents.some(event => event.id === payload.event.id)) {
                    return prevEvents;
                }
                const eventWithTimestamp = {
                    ...payload.event,
                    timestamp: payload.event.timestamp || new Date().toISOString(),
                };
                const combined = [...prevEvents, eventWithTimestamp];
                let dropped = 0;
                if (combined.length > MAX_EVENT_BUFFER) {
                    dropped = combined.length - MAX_EVENT_BUFFER;
                    combined.splice(0, dropped);
                }
                setEventsMeta(meta => ({
                    ...meta,
                    total: (meta.total || prevEvents.length) + 1,
                    remaining: Math.max((meta.remaining || 0) + dropped, 0),
                    truncated: meta.truncated || dropped > 0,
                }));
                combined.sort((a, b) => {
                    const aTime = new Date(a.timestamp || 0).getTime();
                    const bTime = new Date(b.timestamp || 0).getTime();
                    return aTime - bTime;
                });
                return combined;
            });
        };

        const handleStatusUpdate = (payload) => {
            if (!payload || payload.run_id !== runId) {
                return;
            }
            setRunDetails(prev => (prev ? { ...prev, status: payload.status } : prev));
            if (payload.status === 'COMPLETED' || payload.status === 'WAITING_ON_WORKERS' || payload.status === 'ERROR' || payload.status === 'CANCELLED') {
                fetchRunData();
            }
        };

        const handleAsyncQueued = (payload) => {
            if (!payload || payload.run_id !== runId) {
                return;
            }
            setMetrics(prev => {
                if (!prev) {
                    return prev;
                }
                const nextCount = (prev.queued_job_count || 0) + 1;
                const nextLastDepth = payload.queued_jobs ?? prev.queued_job_last_depth;
                const nextMaxDepth = typeof payload.queued_jobs === 'number'
                    ? Math.max(prev.queued_job_max_depth || 0, payload.queued_jobs)
                    : prev.queued_job_max_depth;
                return {
                    ...prev,
                    queued_job_count: nextCount,
                    queued_job_last_depth: nextLastDepth,
                    queued_job_max_depth: nextMaxDepth,
                };
            });

            setQueuedJobs(prev => {
                const jobId = payload.job_id;
                const existingMetricsIds = new Set(
                    workerJobsRef.current.map(job => job.job_id || job.id)
                );
                if (jobId && existingMetricsIds.has(jobId)) {
                    return prev.filter(job => job.job_id !== jobId);
                }

                const alreadyQueuedIndex = prev.findIndex(job => job.job_id === jobId);
                if (alreadyQueuedIndex >= 0) {
                    const updated = [...prev];
                    updated[alreadyQueuedIndex] = {
                        ...updated[alreadyQueuedIndex],
                        queued_jobs_total: payload.queued_jobs,
                        created_at: new Date().toISOString(),
                    };
                    return updated;
                }

                const placeholder = {
                    rowKey: jobId || `queued-${Date.now()}`,
                    job_id: jobId,
                    queue: payload.queue,
                    success: null,
                    outcome: 'Queued',
                    duration_ms: null,
                    steps_executed: null,
                    remaining_steps: null,
                    patient_iteration: payload.patient_iteration,
                    repeat_iteration: payload.repeat_iteration,
                    error: null,
                    created_at: new Date().toISOString(),
                    isQueuedPlaceholder: true,
                    queued_jobs_total: payload.queued_jobs,
                };
                const next = [...prev, placeholder];
                if (next.length > 250) {
                    next.shift();
                }
                return next;
            });
        };

        const handleAsyncCompleted = (payload) => {
            if (!payload || payload.run_id !== runId) {
                return;
            }

            const isRetrying = Boolean(payload.retrying);
            const attemptNumber = payload.retry_attempt ?? payload.job?.attempt ?? null;
            const maxAttempts = payload.retry_max_attempts ?? payload.job?.max_attempts ?? null;

            if (payload.metrics) {
                setMetrics(prev => ({
                    ...(prev || {}),
                    ...payload.metrics,
                }));
            }

            if (payload.job) {
                const jobData = {
                    ...payload.job,
                    created_at: payload.job.created_at || new Date().toISOString(),
                    attempt: attemptNumber ?? payload.job.attempt ?? null,
                    max_attempts: maxAttempts ?? payload.job.max_attempts ?? null,
                    retrying: isRetrying,
                };

                if (workerJobsOptionsRef.current.offset === 0) {
                    setWorkerJobs(prev => {
                        const existingIndex = prev.findIndex(job => job.id === jobData.id);
                        if (existingIndex >= 0) {
                            const updated = [...prev];
                            updated[existingIndex] = jobData;
                            return trimWorkerJobsToLimit(updated);
                        }
                        const next = [...prev, jobData];
                        next.sort((a, b) => {
                            const aTime = new Date(a.created_at || 0).getTime();
                            const bTime = new Date(b.created_at || 0).getTime();
                            return aTime - bTime;
                        });
                        return trimWorkerJobsToLimit(next);
                    });
                }

                const completedJobKey = jobData.job_id || jobData.id;
                setQueuedJobs(prev => {
                    if (!prev.length) {
                        return prev;
                    }
                    if (!completedJobKey) {
                        return isRetrying ? prev : prev.slice(1);
                    }
                    return prev.reduce((acc, job) => {
                        const jobKey = job.job_id || job.rowKey;
                        if (jobKey !== completedJobKey) {
                            acc.push(job);
                            return acc;
                        }

                        if (isRetrying) {
                            acc.push({
                                ...job,
                                last_error: payload.job?.error || payload.job?.outcome || job.last_error,
                                retry_attempt: attemptNumber ?? job.retry_attempt ?? null,
                                retry_max_attempts: maxAttempts ?? job.retry_max_attempts ?? null,
                                updated_at: new Date().toISOString(),
                            });
                        }

                        return acc;
                    }, []);
                });
            }
        };

        socketInstance.on('connect', () => {
            socketInstance.emit('join_run_room', { run_id: runId });
        });

        socketInstance.on('sim_log_update', handleLogUpdate);
        socketInstance.on('sim_run_status_update', handleStatusUpdate);
        socketInstance.on('simulation_async_job_queued', handleAsyncQueued);
        socketInstance.on('simulation_async_job_completed', handleAsyncCompleted);

        return () => {
            if (socketRef.current) {
                socketRef.current.emit('leave_run_room', { run_id: runId });
                socketRef.current.off('sim_log_update', handleLogUpdate);
                socketRef.current.off('sim_run_status_update', handleStatusUpdate);
                socketRef.current.off('simulation_async_job_queued', handleAsyncQueued);
                socketRef.current.off('simulation_async_job_completed', handleAsyncCompleted);
                socketRef.current.disconnect();
                socketRef.current = null;
            }
        };
    }, [runId, fetchRunData, trimWorkerJobsToLimit]);

    const combinedWorkerJobs = useMemo(() => {
        const metricsJobs = (workerJobs || []).map(job => ({
            ...job,
            rowKey: job.id ?? job.job_id ?? `${job.created_at || ''}-${job.queue || 'queue'}`,
            isQueuedPlaceholder: false,
        }));
        const includeQueued = (workerJobsMeta.offset ?? 0) === 0;
        const seen = new Set(metricsJobs.map(job => job.job_id || job.id || job.rowKey));
        const pending = includeQueued
            ? (queuedJobs || [])
                .filter(job => {
                    if (!job.job_id) {
                        return true;
                    }
                    return !seen.has(job.job_id);
                })
                .map(job => ({
                    ...job,
                    rowKey: job.rowKey || job.job_id || `queued-${job.created_at}`,
                    isQueuedPlaceholder: true,
                }))
            : [];
        const merged = [...metricsJobs, ...pending];
        merged.sort((a, b) => {
            const aTime = new Date(a.created_at || 0).getTime();
            const bTime = new Date(b.created_at || 0).getTime();
            return aTime - bTime;
        });
        return merged;
    }, [workerJobs, queuedJobs, workerJobsMeta.offset]);

    const workerDurationStats = useMemo(() => {
        const durations = (workerJobs || [])
            .map(job => (job.duration_ms !== null && job.duration_ms !== undefined ? Number(job.duration_ms) : null))
            .filter(value => value !== null && Number.isFinite(value))
            .sort((a, b) => a - b);

        if (!durations.length) {
            return null;
        }

        const sum = durations.reduce((acc, value) => acc + value, 0);
        const maxValue = durations[durations.length - 1];

        return {
            count: durations.length,
            avg: sum / durations.length,
            p50: calculatePercentile(durations, 50),
            p90: calculatePercentile(durations, 90),
            p95: calculatePercentile(durations, 95),
            p99: calculatePercentile(durations, 99),
            max: maxValue,
        };
    }, [workerJobs]);

    const queuePublishStats = useMemo(() => {
        if (!metrics) {
            return null;
        }
        const { queue_publish_min_ms, queue_publish_avg_ms, queue_publish_max_ms } = metrics;
        if (
            queue_publish_min_ms === null &&
            queue_publish_avg_ms === null &&
            queue_publish_max_ms === null
        ) {
            return null;
        }
        return {
            min: queue_publish_min_ms,
            avg: queue_publish_avg_ms,
            max: queue_publish_max_ms,
        };
    }, [metrics]);

    const dicomSendStats = useMemo(() => {
        if (!metrics) {
            return null;
        }
        const {
            dicom_send_avg_ms,
            dicom_send_min_ms,
            dicom_send_max_ms,
            dicom_send_count,
        } = metrics;
        if (
            dicom_send_avg_ms === null &&
            dicom_send_min_ms === null &&
            dicom_send_max_ms === null
        ) {
            return null;
        }
        return {
            avg: dicom_send_avg_ms,
            min: dicom_send_min_ms,
            max: dicom_send_max_ms,
            count: dicom_send_count,
        };
    }, [metrics]);

    const dicomThroughputStats = useMemo(() => {
        if (!metrics) {
            return null;
        }
        const {
            dicom_throughput_avg_mbps,
            dicom_throughput_min_mbps,
            dicom_throughput_max_mbps,
            dicom_throughput_count,
        } = metrics;
        if (
            dicom_throughput_avg_mbps === null &&
            dicom_throughput_min_mbps === null &&
            dicom_throughput_max_mbps === null
        ) {
            return null;
        }
        return {
            avg: dicom_throughput_avg_mbps,
            min: dicom_throughput_min_mbps,
            max: dicom_throughput_max_mbps,
            count: dicom_throughput_count,
        };
    }, [metrics]);

    const stepDurations = useMemo(() => {
        if (!metrics || !Array.isArray(metrics.step_durations)) {
            return [];
        }
        return metrics.step_durations;
    }, [metrics]);

    const slowestStep = useMemo(() => {
        if (!stepDurations.length) {
            return null;
        }
        return stepDurations.reduce((acc, step) => {
            const avgValue = step.avg_ms ?? (step.total_ms && step.count ? step.total_ms / step.count : null);
            if (avgValue === null || avgValue === undefined) {
                return acc;
            }
            const numericAvg = Number(avgValue);
            if (!Number.isFinite(numericAvg)) {
                return acc;
            }
            if (!acc) {
                return { ...step, avg_value: numericAvg };
            }
            if (numericAvg > acc.avg_value) {
                return { ...step, avg_value: numericAvg };
            }
            return acc;
        }, null);
    }, [stepDurations]);

    const totalWorkerJobs = workerJobsMeta.total ?? workerJobs.length;
    const currentWorkerCount = workerJobs.length;
    const totalCombinedCount = combinedWorkerJobs.length;
    const includeQueuedPlaceholders = (workerJobsMeta.offset ?? 0) === 0;
    const isAtLatestWorkerPage = includeQueuedPlaceholders;
    const queuedPlaceholderCount = includeQueuedPlaceholders
        ? Math.max(totalCombinedCount - currentWorkerCount, 0)
        : 0;
    const workerJobsLimit = workerJobsMeta.limit || WORKER_JOBS_FETCH_LIMIT;
    const workerJobsPage = workerJobsLimit
        ? Math.floor((workerJobsMeta.offset ?? 0) / workerJobsLimit) + 1
        : 1;
    const workerJobsTotalPages = workerJobsLimit && totalWorkerJobs > 0
        ? Math.max(1, Math.ceil(totalWorkerJobs / workerJobsLimit))
        : 1;
    const hasNewerWorkerJobs = (workerJobsMeta.offset ?? 0) > 0;
    const hasOlderWorkerJobs = workerJobsLimit
        ? (workerJobsMeta.offset ?? 0) + workerJobsLimit < totalWorkerJobs
        : false;

    const workerHeaderLabel = totalWorkerJobs > 0
        ? `${formatNumber(totalWorkerJobs)} total${includeQueuedPlaceholders && queuedPlaceholderCount > 0 ? ` • ${formatNumber(queuedPlaceholderCount)} queued` : ''}`
        : includeQueuedPlaceholders && queuedPlaceholderCount > 0
            ? `${formatNumber(queuedPlaceholderCount)} queued`
            : 'No worker jobs recorded yet';

    const workerJobsSummaryText = totalWorkerJobs > 0
        ? `Showing ${formatNumber(currentWorkerCount)} of ${formatNumber(totalWorkerJobs)} worker jobs • Page ${formatNumber(workerJobsPage)} of ${formatNumber(workerJobsTotalPages)}`
        : 'No worker job metrics recorded yet.';

    const workerJobsHintText = workerJobsMeta.offset > 0
        ? 'Viewing older entries. Auto-refresh paused for paging; use "Latest" to resume realtime updates.'
        : workerJobsMeta.truncated
            ? 'Showing newest worker jobs. Use "Older" to page back through history.'
            : '';

    const workerBarItems = useMemo(() => {
        if (!workerDurationStats) {
            return [];
        }
        return [
            { label: 'Avg', value: workerDurationStats.avg },
            { label: 'P50', value: workerDurationStats.p50 },
            { label: 'P90', value: workerDurationStats.p90 },
            { label: 'P95', value: workerDurationStats.p95 },
            { label: 'P99', value: workerDurationStats.p99 },
            { label: 'Max', value: workerDurationStats.max },
        ];
    }, [workerDurationStats]);

    const workerMaxValue = workerDurationStats?.max || 0;

    const queueBarItems = useMemo(() => {
        if (!queuePublishStats) {
            return [];
        }
        return [
            { label: 'Min', value: queuePublishStats.min },
            { label: 'Avg', value: queuePublishStats.avg },
            { label: 'Max', value: queuePublishStats.max },
        ];
    }, [queuePublishStats]);

    const queueMaxValue = queueBarItems.reduce((max, item) => Math.max(max, item.value || 0), 0);

    const loadWorkerJobsPage = useCallback(async (newOffset) => {
        const safeLimit = workerJobsMetaRef.current?.limit ?? WORKER_JOBS_FETCH_LIMIT;
        const safeOrder = workerJobsOptionsRef.current.order ?? 'desc';
        const clampedOffset = Math.max(newOffset, 0);
        setIsLoadingWorkerJobs(true);
        try {
            if (clampedOffset > 0) {
                setAutoRefresh(false);
            }
            await fetchRunData({
                refreshEvents: false,
                jobsOffset: clampedOffset,
                jobsLimit: safeLimit,
                jobsOrder: safeOrder,
            });
        } finally {
            setIsLoadingWorkerJobs(false);
        }
    }, [fetchRunData, setAutoRefresh]);

    const handleWorkerJobsLatest = useCallback(() => {
        if (isLoadingWorkerJobs) {
            return;
        }
        loadWorkerJobsPage(0);
    }, [isLoadingWorkerJobs, loadWorkerJobsPage]);

    const handleWorkerJobsNewer = useCallback(() => {
        if (isLoadingWorkerJobs) {
            return;
        }
        if (!hasNewerWorkerJobs) {
            return;
        }
        const nextOffset = Math.max((workerJobsMeta.offset ?? 0) - workerJobsLimit, 0);
        loadWorkerJobsPage(nextOffset);
    }, [isLoadingWorkerJobs, hasNewerWorkerJobs, workerJobsMeta.offset, workerJobsLimit, loadWorkerJobsPage]);

    const handleWorkerJobsOlder = useCallback(() => {
        if (isLoadingWorkerJobs) {
            return;
        }
        if (!hasOlderWorkerJobs) {
            return;
        }
        const nextOffset = (workerJobsMeta.offset ?? 0) + workerJobsLimit;
        loadWorkerJobsPage(nextOffset);
    }, [isLoadingWorkerJobs, hasOlderWorkerJobs, workerJobsMeta.offset, workerJobsLimit, loadWorkerJobsPage]);

    const handleDownloadCsv = () => {
        if (!metrics) {
            toast.error('Run metrics are not available yet.');
            return;
        }

        const rows = [];

        rows.push(['metric', 'value']);
        rows.push(['total_patients', metrics.total_patients ?? '']);
        rows.push(['queued_job_count', metrics.queued_job_count ?? '']);
        rows.push(['queued_job_max_depth', metrics.queued_job_max_depth ?? '']);
        rows.push(['queued_job_last_depth', metrics.queued_job_last_depth ?? '']);
        rows.push(['worker_job_count', metrics.worker_job_count ?? '']);
        rows.push(['worker_job_success_count', metrics.worker_job_success_count ?? '']);
        rows.push(['worker_job_duration_avg_ms', metrics.worker_job_duration_avg_ms ?? '']);
        rows.push(['orders_per_second', metrics.orders_per_second ?? '']);
        rows.push(['queue_publish_avg_ms', metrics.queue_publish_avg_ms ?? '']);
        rows.push(['queue_publish_min_ms', metrics.queue_publish_min_ms ?? '']);
        rows.push(['queue_publish_max_ms', metrics.queue_publish_max_ms ?? '']);
        rows.push(['dicom_success_instances', metrics.dicom_success_instances ?? '']);
        rows.push(['dicom_attempted_instances', metrics.dicom_attempted_instances ?? '']);
        rows.push(['dicom_success_bytes', metrics.dicom_success_bytes ?? '']);
        rows.push(['dicom_attempted_bytes', metrics.dicom_attempted_bytes ?? '']);
        rows.push(['dicom_send_avg_ms', metrics.dicom_send_avg_ms ?? '']);
        rows.push(['dicom_send_min_ms', metrics.dicom_send_min_ms ?? '']);
        rows.push(['dicom_send_max_ms', metrics.dicom_send_max_ms ?? '']);
        rows.push(['dicom_send_count', metrics.dicom_send_count ?? '']);
        rows.push(['dicom_throughput_avg_mbps', metrics.dicom_throughput_avg_mbps ?? '']);
        rows.push(['dicom_throughput_min_mbps', metrics.dicom_throughput_min_mbps ?? '']);
        rows.push(['dicom_throughput_max_mbps', metrics.dicom_throughput_max_mbps ?? '']);
        rows.push(['dicom_throughput_count', metrics.dicom_throughput_count ?? '']);
        rows.push(['wall_clock_seconds', metrics.wall_clock_seconds ?? '']);
        rows.push(['started_at', metrics.started_at ?? '']);
        rows.push(['completed_at', metrics.completed_at ?? '']);
        rows.push([]);

        const csvStepDurations = Array.isArray(metrics.step_durations) ? metrics.step_durations : [];
        if (csvStepDurations.length) {
            rows.push(['step_order', 'step_type', 'count', 'avg_ms', 'last_ms', 'min_ms', 'max_ms', 'total_ms']);
            csvStepDurations.forEach((step) => {
                rows.push([
                    step.step_order ?? '',
                    step.step_type ?? '',
                    step.count ?? '',
                    step.avg_ms ?? '',
                    step.last_ms ?? '',
                    step.min_ms ?? '',
                    step.max_ms ?? '',
                    step.total_ms ?? '',
                ]);
            });
            rows.push([]);
        }

        rows.push([
            'job_id',
            'queue',
            'success',
            'outcome',
            'duration_ms',
            'steps_executed',
            'remaining_steps',
            'patient_iteration',
            'error',
            'created_at',
        ]);

        workerJobs.forEach((job) => {
            rows.push([
                job.job_id || job.id || '',
                job.queue || '',
                job.success === undefined ? '' : job.success ? 'true' : 'false',
                job.outcome || '',
                job.duration_ms ?? '',
                job.steps_executed ?? '',
                job.remaining_steps ?? '',
                job.patient_iteration ?? '',
                job.error || '',
                job.created_at || '',
            ]);
        });

        const csvContent = rows
            .map((row) => row.map(escapeCsvValue).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `simulation-run-${runId}-metrics.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        toast.success('Metrics CSV downloaded.');
    };

    return (
        <div className="space-y-6">
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
                        <button
                            onClick={handleDownloadCsv}
                            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-medium"
                        >
                            Download Metrics CSV
                        </button>
                    </div>
                </div>

                {metrics && (
                    <>
                        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                            <MetricCard
                                title="Patients"
                                tooltipKey="patients"
                                primary={formatNumber(metrics?.total_patients ?? runDetails?.patient_count)}
                            >
                                <p className="text-xs text-gray-500">
                                    Template configured {formatNumber(runDetails?.patient_count)}
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="Async Jobs"
                                tooltipKey="queuedJobs"
                                primary={formatNumber(metrics?.queued_job_count)}
                            >
                                <p className="text-xs text-gray-500 flex items-center gap-1">
                                    <TooltipIcon message={METRIC_TOOLTIPS.queuedJobDepth} label="Queue depth help" />
                                    <span>
                                        Max depth {formatNumber(metrics?.queued_job_max_depth)} | Last {formatNumber(metrics?.queued_job_last_depth)}
                                    </span>
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="Worker Jobs"
                                tooltipKey="workerSuccess"
                                primary={`${formatNumber(metrics?.worker_job_success_count)} / ${formatNumber(metrics?.worker_job_count)} success`}
                            >
                                <p className="text-xs text-gray-500 flex items-center gap-1">
                                    <TooltipIcon message={METRIC_TOOLTIPS.workerDuration} label="Worker duration help" />
                                    <span>Avg duration {formatFloat(metrics?.worker_job_duration_avg_ms)} ms</span>
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="Dispatch Rate"
                                tooltipKey="ordersPerSecond"
                                primary={`${formatFloat(metrics?.orders_per_second)} jobs/s`}
                            >
                                <p className="text-xs text-gray-500 flex items-center gap-1">
                                    <TooltipIcon message={METRIC_TOOLTIPS.queuePublish} label="Queue publish help" />
                                    <span>Publish avg {formatFloat(metrics?.queue_publish_avg_ms)} ms</span>
                                </p>
                            </MetricCard>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                            <MetricCard
                                title="DICOM Success"
                                tooltipKey="dicomSuccess"
                                primary={`${formatNumber(metrics?.dicom_success_instances)} / ${formatNumber(metrics?.dicom_attempted_instances)}`}
                            >
                                <p className="text-xs text-gray-500 flex items-center gap-1">
                                    <TooltipIcon message={METRIC_TOOLTIPS.dicomBytes} label="DICOM volume help" />
                                    <span>Success bytes {formatNumber(metrics?.dicom_success_bytes)}</span>
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="DICOM Volume"
                                tooltipKey="dicomBytes"
                                primary={`${formatNumber(metrics?.dicom_attempted_bytes)} attempted bytes`}
                            >
                                <p className="text-xs text-gray-500">
                                    Success {formatNumber(metrics?.dicom_success_bytes)} bytes delivered
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="DICOM Throughput"
                                tooltipKey="dicomThroughput"
                                primary={dicomThroughputStats ? formatThroughput(dicomThroughputStats.avg) : '—'}
                            >
                                <p className="text-xs text-gray-500">
                                    Peak {dicomThroughputStats ? formatThroughput(dicomThroughputStats.max) : '—'}
                                </p>
                                <p className="text-xs text-gray-500">
                                    Samples {formatNumber(dicomThroughputStats?.count)}
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="C-STORE Duration"
                                tooltipKey="dicomSendLatency"
                                primary={dicomSendStats && dicomSendStats.avg !== null && dicomSendStats.avg !== undefined ? `${formatFloat(dicomSendStats.avg)} ms` : '—'}
                            >
                                <p className="text-xs text-gray-500">
                                    Min {dicomSendStats && dicomSendStats.min !== null && dicomSendStats.min !== undefined ? `${formatFloat(dicomSendStats.min)} ms` : '—'} | Max {dicomSendStats && dicomSendStats.max !== null && dicomSendStats.max !== undefined ? `${formatFloat(dicomSendStats.max)} ms` : '—'}
                                </p>
                                <p className="text-xs text-gray-500">
                                    Samples {formatNumber(dicomSendStats?.count)}
                                </p>
                            </MetricCard>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                            <MetricCard
                                title="Run Window"
                                tooltipKey="runWindow"
                                primary={formatDateTime(metrics?.started_at)}
                            >
                                <p className="text-xs text-gray-500">Completed {formatDateTime(metrics?.completed_at)}</p>
                            </MetricCard>
                            <MetricCard
                                title="Wall Clock"
                                tooltipKey="wallClock"
                                primary={formatSeconds(metrics?.wall_clock_seconds)}
                            >
                                <p className="text-xs text-gray-500">
                                    Includes async wait time and worker execution windows.
                                </p>
                            </MetricCard>
                            <MetricCard
                                title="Slowest Step"
                                tooltipKey="slowestStep"
                                primary={
                                    slowestStep && (slowestStep.avg_value ?? slowestStep.avg_ms) !== null && (slowestStep.avg_value ?? slowestStep.avg_ms) !== undefined
                                        ? `${formatFloat(slowestStep.avg_value ?? slowestStep.avg_ms)} ms`
                                        : '—'
                                }
                            >
                                {slowestStep ? (
                                    <>
                                        <p className="text-xs text-gray-500">
                                            Step #{formatNumber(slowestStep.step_order)} · {formatStepTypeLabel(slowestStep.step_type)}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            Max {slowestStep.max_ms !== null && slowestStep.max_ms !== undefined ? `${formatFloat(slowestStep.max_ms)} ms` : '—'} across {formatNumber(slowestStep.count)} runs
                                        </p>
                                    </>
                                ) : (
                                    <p className="text-xs text-gray-500">No step timing captured yet.</p>
                                )}
                            </MetricCard>
                        </div>

                        {stepDurations.length > 0 && (
                            <div className="mt-6">
                                <div className="mb-2 flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-300">
                                        <span>Step Durations</span>
                                        <TooltipIcon message={METRIC_TOOLTIPS.stepDurations} label="Step durations help" />
                                    </div>
                                    <span className="text-xs text-gray-500">
                                        {formatNumber(stepDurations.length)} steps reported
                                    </span>
                                </div>
                                <div className="overflow-x-auto rounded-md border border-gray-800 bg-gray-950">
                                    <table className="min-w-full text-xs text-gray-300">
                                        <thead className="bg-gray-900 text-[11px] uppercase text-gray-500">
                                            <tr>
                                                <th className="px-3 py-2 text-left">Step</th>
                                                <th className="px-3 py-2 text-left">Type</th>
                                                <th className="px-3 py-2 text-left">Count</th>
                                                <th className="px-3 py-2 text-left">Avg (ms)</th>
                                                <th className="px-3 py-2 text-left">Last (ms)</th>
                                                <th className="px-3 py-2 text-left">Min (ms)</th>
                                                <th className="px-3 py-2 text-left">Max (ms)</th>
                                                <th className="px-3 py-2 text-left">Total (ms)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {stepDurations.map((step) => {
                                                const isSlowest = slowestStep && slowestStep.step_order === step.step_order;
                                                return (
                                                    <tr
                                                        key={step.step_order}
                                                        className={isSlowest ? 'bg-gray-900' : 'bg-gray-950'}
                                                    >
                                                        <td className="px-3 py-2 align-top">{formatNumber(step.step_order)}</td>
                                                        <td className="px-3 py-2 align-top">{formatStepTypeLabel(step.step_type)}</td>
                                                        <td className="px-3 py-2 align-top">{formatNumber(step.count)}</td>
                                                        <td className="px-3 py-2 align-top">{step.avg_ms !== null && step.avg_ms !== undefined ? formatFloat(step.avg_ms) : '—'}</td>
                                                        <td className="px-3 py-2 align-top">{step.last_ms !== null && step.last_ms !== undefined ? formatFloat(step.last_ms) : '—'}</td>
                                                        <td className="px-3 py-2 align-top">{step.min_ms !== null && step.min_ms !== undefined ? formatFloat(step.min_ms) : '—'}</td>
                                                        <td className="px-3 py-2 align-top">{step.max_ms !== null && step.max_ms !== undefined ? formatFloat(step.max_ms) : '—'}</td>
                                                        <td className="px-3 py-2 align-top">{step.total_ms !== null && step.total_ms !== undefined ? formatFloat(step.total_ms) : '—'}</td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {(workerDurationStats || queuePublishStats) && (
                            <div className="mt-4 grid gap-4 md:grid-cols-2">
                                {workerDurationStats && (
                                    <div className="rounded-md border border-gray-800 bg-gray-950 p-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-1 text-xs uppercase text-gray-500">
                                                <span>Worker Duration Percentiles</span>
                                                <TooltipIcon message={METRIC_TOOLTIPS.workerDuration} label="Worker duration help" />
                                            </div>
                                            <span className="text-[11px] text-gray-500">{formatNumber(workerDurationStats.count)} samples</span>
                                        </div>
                                        <div className="space-y-3">
                                            {workerBarItems.map(item => (
                                                <div key={item.label}>
                                                    <div className="flex justify-between text-[11px] text-gray-400 mb-1">
                                                        <span>{item.label}</span>
                                                        <span>{item.value !== null && item.value !== undefined ? `${formatFloat(item.value)} ms` : '—'}</span>
                                                    </div>
                                                    <div className="h-2 bg-gray-800 rounded">
                                                        <div
                                                            className="h-2 rounded bg-indigo-500"
                                                            style={{ width: `${computeBarWidthPercentage(item.value, workerMaxValue || 1)}%` }}
                                                        ></div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <p className="mt-3 text-[10px] text-gray-500">Max duration sets the scale. Percentiles computed from worker job metrics.</p>
                                    </div>
                                )}
                                {queuePublishStats && (
                                    <div className="rounded-md border border-gray-800 bg-gray-950 p-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-1 text-xs uppercase text-gray-500">
                                                <span>Queue Publish Timing</span>
                                                <TooltipIcon message={METRIC_TOOLTIPS.queuePublish} label="Queue publish help" />
                                            </div>
                                            <span className="text-[11px] text-gray-500">Min / Avg / Max</span>
                                        </div>
                                        <div className="space-y-3">
                                            {queueBarItems.map(item => (
                                                <div key={item.label}>
                                                    <div className="flex justify-between text-[11px] text-gray-400 mb-1">
                                                        <span>{item.label}</span>
                                                        <span>{item.value !== null && item.value !== undefined ? `${formatFloat(item.value)} ms` : '—'}</span>
                                                    </div>
                                                    <div className="h-2 bg-gray-800 rounded">
                                                        <div
                                                            className="h-2 rounded bg-teal-500"
                                                            style={{ width: `${computeBarWidthPercentage(item.value, queueMaxValue || workerMaxValue || 1)}%` }}
                                                        ></div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <p className="mt-3 text-[10px] text-gray-500">Scaled against the largest observed publish time.</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                )}

                {eventsMeta.truncated && (
                    <div className="mt-4 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                        Showing last {formatNumber(events.length)} of {formatNumber(eventsMeta.total)} log events. {eventsMeta.remaining > 0 ? `${formatNumber(eventsMeta.remaining)} older entries are hidden to keep the dashboard responsive.` : 'Older entries were trimmed to keep the dashboard responsive.'}
                    </div>
                )}

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
                    {formatNumber(events.length)} events • Last updated: {new Date().toLocaleTimeString()}
                    {autoRefresh && <span className="ml-2">• Auto-refreshing every 2s</span>}
                </div>
            </div>

            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-semibold text-gray-100">Worker Jobs</h4>
                    <span className="text-xs text-gray-500">{workerHeaderLabel}</span>
                </div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
                    <span>{workerJobsSummaryText}</span>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleWorkerJobsLatest}
                            disabled={isLoadingWorkerJobs || isAtLatestWorkerPage}
                            className={`px-2 py-1 rounded border border-gray-700 transition ${
                                isLoadingWorkerJobs || isAtLatestWorkerPage
                                    ? 'text-gray-500 cursor-not-allowed opacity-60'
                                    : 'text-gray-300 hover:bg-gray-800'
                            }`}
                        >
                            Latest
                        </button>
                        <button
                            onClick={handleWorkerJobsNewer}
                            disabled={isLoadingWorkerJobs || !hasNewerWorkerJobs}
                            className={`px-2 py-1 rounded border border-gray-700 transition ${
                                isLoadingWorkerJobs || !hasNewerWorkerJobs
                                    ? 'text-gray-500 cursor-not-allowed opacity-60'
                                    : 'text-gray-300 hover:bg-gray-800'
                            }`}
                        >
                            Newer
                        </button>
                        <button
                            onClick={handleWorkerJobsOlder}
                            disabled={isLoadingWorkerJobs || !hasOlderWorkerJobs}
                            className={`px-2 py-1 rounded border border-gray-700 transition ${
                                isLoadingWorkerJobs || !hasOlderWorkerJobs
                                    ? 'text-gray-500 cursor-not-allowed opacity-60'
                                    : 'text-gray-300 hover:bg-gray-800'
                            }`}
                        >
                            Older
                        </button>
                    </div>
                </div>
                {workerJobsHintText && (
                    <div className="mb-3 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                        {workerJobsHintText}
                    </div>
                )}
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-800 text-sm">
                        <thead className="bg-gray-950 text-xs uppercase text-gray-400">
                            <tr>
                                <th className="px-3 py-2 text-left">Job ID</th>
                                <th className="px-3 py-2 text-left">Queue</th>
                                <th className="px-3 py-2 text-left">Success</th>
                                <th className="px-3 py-2 text-left">Outcome</th>
                                <th className="px-3 py-2 text-left">Duration (ms)</th>
                                <th className="px-3 py-2 text-left">Steps</th>
                                <th className="px-3 py-2 text-left">Remaining</th>
                                <th className="px-3 py-2 text-left">Patient Iter</th>
                                <th className="px-3 py-2 text-left">Error</th>
                                <th className="px-3 py-2 text-left">Created</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800 bg-gray-900">
                            {isLoadingWorkerJobs ? (
                                <tr>
                                    <td colSpan="10" className="px-3 py-4 text-center text-gray-500">
                                        Loading worker jobs…
                                    </td>
                                </tr>
                            ) : combinedWorkerJobs.length === 0 ? (
                                <tr>
                                    <td colSpan="10" className="px-3 py-4 text-center text-gray-500">
                                        No worker job metrics yet.
                                    </td>
                                </tr>
                            ) : (
                                combinedWorkerJobs.map((job) => {
                                    const isPlaceholder = job.isQueuedPlaceholder;
                                    const rowKey = job.rowKey || job.job_id || job.id || `${job.queue || 'queue'}-${job.created_at}`;
                                    const successDisplay = isPlaceholder
                                        ? 'Queued'
                                        : job.success === undefined || job.success === null
                                            ? '—'
                                            : job.success ? 'Yes' : 'No';
                                    const successClass = isPlaceholder
                                        ? 'text-amber-300'
                                        : job.success
                                            ? 'text-green-300'
                                            : job.success === false
                                                ? 'text-red-300'
                                                : 'text-gray-200';
                                    const attemptValue = job.attempt ?? job.retry_attempt ?? null;
                                    const attemptMax = job.max_attempts ?? job.retry_max_attempts ?? null;
                                    const attemptSuffix = (() => {
                                        if (attemptValue && attemptValue > 1 && attemptMax) {
                                            return ` (attempt ${attemptValue}/${attemptMax})`;
                                        }
                                        if (attemptValue && attemptValue > 1) {
                                            return ` (attempt ${attemptValue})`;
                                        }
                                        return '';
                                    })();
                                    const outcomeDisplay = (() => {
                                        if (isPlaceholder) {
                                            const depthLabel = job.queued_jobs_total !== null && job.queued_jobs_total !== undefined
                                                ? ` (depth ${job.queued_jobs_total})`
                                                : '';
                                            return `Queued${depthLabel}${attemptSuffix}`;
                                        }
                                        const baseOutcome = job.outcome || '—';
                                        return `${baseOutcome}${attemptSuffix}`;
                                    })();
                                    const durationDisplay = !isPlaceholder && job.duration_ms !== null && job.duration_ms !== undefined
                                        ? formatFloat(job.duration_ms)
                                        : '—';
                                    const createdDisplay = formatDateTime(job.created_at);
                                    return (
                                    <tr
                                            key={rowKey}
                                            className={`hover:bg-gray-800/60 ${
                                                isPlaceholder
                                                    ? 'bg-amber-900/10'
                                                    : job.success === false
                                                        ? 'bg-red-900/20'
                                                        : ''
                                            }`}
                                        >
                                            <td className="px-3 py-2 text-gray-200">{job.job_id || job.id || '—'}</td>
                                            <td className="px-3 py-2 text-gray-200">{job.queue || '—'}</td>
                                            <td className={`px-3 py-2 ${successClass}`}>{successDisplay}</td>
                                            <td className="px-3 py-2 text-gray-200">{outcomeDisplay}</td>
                                            <td className="px-3 py-2 text-gray-200">{durationDisplay}</td>
                                            <td className="px-3 py-2 text-gray-200">{isPlaceholder ? '—' : (job.steps_executed ?? '—')}</td>
                                            <td className="px-3 py-2 text-gray-200">{isPlaceholder ? '—' : (job.remaining_steps ?? '—')}</td>
                                            <td className="px-3 py-2 text-gray-200">{job.patient_iteration ?? '—'}</td>
                                            <td className="px-3 py-2 text-gray-200">{isPlaceholder ? (job.last_error || '—') : job.error || '—'}</td>
                                            <td className="px-3 py-2 text-gray-300">{createdDisplay}</td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default SimulationRunLog;
