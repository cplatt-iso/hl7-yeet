// --- START OF FILE src/components/WorkerAutoscalerPanel.jsx ---

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import { InformationCircleIcon } from '@heroicons/react/24/outline';
import {
    getWorkerAutoscalerStatusApi,
    updateWorkerAutoscalerConfigApi,
    manualWorkerScaleApi,
    clearManualWorkerScaleApi,
} from '../api/admin';

const numberFields = [
    'min_replicas',
    'max_replicas',
    'scale_up_threshold',
    'scale_up_step',
    'scale_down_threshold',
    'scale_down_step',
    'scale_down_cooldown_seconds',
    'poll_interval_seconds',
    'management_port',
];

// --- Inline tooltip copy for each configurable field ---
const FIELD_HELP_TEXT = {
    enabled: 'When disabled the autoscaler stops polling the queue. Workers stay at their current replica count until you scale manually.',
    min_replicas: 'Smallest number of worker pods to keep running even when the queue is empty.',
    max_replicas: 'Upper bound on worker replicas. Set high enough to absorb bursts but below your cluster capacity.',
    scale_up_threshold: 'Average messages per worker that triggers a scale-up. Lower values react faster but may oscillate.',
    scale_up_step: 'How many replicas to add whenever the threshold is exceeded.',
    scale_down_threshold: 'Average messages per worker below this value triggers scale-down. Keep lower than the scale-up threshold.',
    scale_down_step: 'How many replicas to remove when we scale down.',
    scale_down_cooldown_seconds: 'Minimum wait after a scale-down before another reduction is allowed. Prevents rapid churn.',
    poll_interval_seconds: 'How often the autoscaler checks RabbitMQ. Short intervals react faster but add API load.',
    management_port: 'RabbitMQ management port exposed by your ingress or service.',
    queue_name: 'Name of the RabbitMQ queue that workers consume. Must match your worker configuration.',
};

const LabelWithTooltip = ({ label, helpKey, children }) => (
    <label className="flex flex-col text-sm text-gray-300">
        <span className="mb-1 flex items-center gap-1">
            {label}
            {helpKey && FIELD_HELP_TEXT[helpKey] && (
                <span className="relative group inline-flex focus:outline-none" tabIndex={0} aria-label={`${label} help`}>
                    <InformationCircleIcon
                        className="h-4 w-4 text-gray-400 group-hover:text-indigo-300 group-focus:text-indigo-300"
                        aria-hidden="true"
                    />
                    <span className="pointer-events-none absolute left-1/2 top-full z-20 hidden w-64 -translate-x-1/2 rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-200 shadow-lg group-hover:block group-focus:block">
                        {FIELD_HELP_TEXT[helpKey]}
                    </span>
                </span>
            )}
        </span>
        {children}
    </label>
);

const WorkerAutoscalerPanel = () => {
    const [config, setConfig] = useState(null);
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [manualReplicas, setManualReplicas] = useState('');

    const hydrate = useCallback(async () => {
        setLoading(true);
        try {
            const data = await getWorkerAutoscalerStatusApi();
            setConfig(data.config);
            setStatus(data.status);
        } catch (error) {
            toast.error(`Failed to load autoscaler status: ${error.message}`);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        hydrate();
        const timer = setInterval(hydrate, 15000);
        return () => clearInterval(timer);
    }, [hydrate]);

    const handleConfigChange = (event) => {
        if (!config) {
            return;
        }
        const { name, value, type, checked } = event.target;
        let nextValue = value;
        if (type === 'checkbox') {
            nextValue = checked;
        } else if (numberFields.includes(name)) {
            nextValue = value === '' ? '' : Number(value);
        }
        setConfig((prev) => ({ ...prev, [name]: nextValue }));
    };

    const handleSaveConfig = async (event) => {
        event.preventDefault();
        if (!config) {
            return;
        }
        const payload = { ...config };
        numberFields.forEach((field) => {
            if (payload[field] === '' || payload[field] === null || payload[field] === undefined) {
                return;
            }
            payload[field] = Number(payload[field]);
        });
        setSaving(true);
        try {
            const data = await updateWorkerAutoscalerConfigApi(payload);
            setConfig(data.config);
            setStatus(data.status);
            toast.success('Autoscaler configuration updated');
        } catch (error) {
            toast.error(`Failed to update configuration: ${error.message}`);
        } finally {
            setSaving(false);
        }
    };

    const handleManualScale = async (event) => {
        event.preventDefault();
        if (!manualReplicas) {
            toast.error('Enter desired replica count');
            return;
        }
        const replicas = Number(manualReplicas);
        if (!Number.isInteger(replicas) || replicas <= 0) {
            toast.error('Replicas must be a positive integer');
            return;
        }
        const toastId = toast.loading(`Scaling workers to ${replicas}...`);
        try {
            const data = await manualWorkerScaleApi(replicas);
            setConfig(data.config);
            setStatus(data.status);
            toast.success('Manual scale applied', { id: toastId });
        } catch (error) {
            toast.error(`Manual scale failed: ${error.message}`, { id: toastId });
        }
    };

    const handleClearOverride = async () => {
        const toastId = toast.loading('Clearing manual override...');
        try {
            const data = await clearManualWorkerScaleApi();
            setConfig(data.config);
            setStatus(data.status);
            toast.success('Manual override cleared', { id: toastId });
        } catch (error) {
            toast.error(`Failed to clear override: ${error.message}`, { id: toastId });
        }
    };

    const renderStatusCell = (label, value) => (
        <div className="flex flex-col">
            <span className="text-sm text-gray-400">{label}</span>
            <span className="text-base text-gray-100 font-semibold">{value ?? '—'}</span>
        </div>
    );

    return (
        <div className="bg-gray-900 rounded-lg p-6 shadow-md border border-gray-800">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-white">Worker Autoscaler</h3>
                <button
                    onClick={hydrate}
                    className="px-3 py-1 rounded bg-gray-700 text-gray-200 hover:bg-gray-600 disabled:opacity-50"
                    disabled={loading}
                >
                    {loading ? 'Refreshing...' : 'Refresh'}
                </button>
            </div>

            {status && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    {renderStatusCell('Current Replicas', status.current_replicas)}
                    {renderStatusCell('Target Replicas', status.manual_override_active ? status.manual_override_replicas : status.target_replicas)}
                    {renderStatusCell('Queue Depth', status.queue_depth)}
                    {renderStatusCell('Kubernetes Connected', status.kubernetes_connected ? 'Yes' : 'No')}
                    {renderStatusCell('Last Queue Check', status.last_queue_check_at ? new Date(status.last_queue_check_at).toLocaleString() : '—')}
                    {renderStatusCell('Last Scale Event', status.last_scale_at ? `${status.last_scale_action || ''} @ ${new Date(status.last_scale_at).toLocaleString()}` : '—')}
                    {status.last_error && renderStatusCell('Last Error', status.last_error)}
                    {status.manual_override_active && renderStatusCell('Manual Override', `${status.manual_override_replicas} replicas`)}
                </div>
            )}

            {config ? (
                <form onSubmit={handleSaveConfig} className="space-y-6">
                    <fieldset className="border border-gray-800 rounded-lg p-4">
                        <legend className="px-2 text-sm font-semibold text-gray-300">Configuration</legend>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <LabelWithTooltip label="Enabled" helpKey="enabled">
                                <input
                                    type="checkbox"
                                    name="enabled"
                                    checked={Boolean(config.enabled)}
                                    onChange={handleConfigChange}
                                    className="h-4 w-4"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Min Replicas" helpKey="min_replicas">
                                <input
                                    type="number"
                                    name="min_replicas"
                                    value={config.min_replicas ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="1"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Max Replicas" helpKey="max_replicas">
                                <input
                                    type="number"
                                    name="max_replicas"
                                    value={config.max_replicas ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="1"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Scale-Up Threshold (msgs/worker)" helpKey="scale_up_threshold">
                                <input
                                    type="number"
                                    name="scale_up_threshold"
                                    value={config.scale_up_threshold ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="1"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Scale-Up Step" helpKey="scale_up_step">
                                <input
                                    type="number"
                                    name="scale_up_step"
                                    value={config.scale_up_step ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="1"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Scale-Down Threshold" helpKey="scale_down_threshold">
                                <input
                                    type="number"
                                    name="scale_down_threshold"
                                    value={config.scale_down_threshold ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="0"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Scale-Down Step" helpKey="scale_down_step">
                                <input
                                    type="number"
                                    name="scale_down_step"
                                    value={config.scale_down_step ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="1"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Scale-Down Cooldown (sec)" helpKey="scale_down_cooldown_seconds">
                                <input
                                    type="number"
                                    name="scale_down_cooldown_seconds"
                                    value={config.scale_down_cooldown_seconds ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="0"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Poll Interval (sec)" helpKey="poll_interval_seconds">
                                <input
                                    type="number"
                                    name="poll_interval_seconds"
                                    value={config.poll_interval_seconds ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="5"
                                />
                            </LabelWithTooltip>
                            <LabelWithTooltip label="Management Port" helpKey="management_port">
                                <input
                                    type="number"
                                    name="management_port"
                                    value={config.management_port ?? ''}
                                    onChange={handleConfigChange}
                                    className="bg-gray-800 border border-gray-700 rounded p-2"
                                    min="1"
                                />
                            </LabelWithTooltip>
                            <div className="md:col-span-2">
                                <LabelWithTooltip label="Queue Name" helpKey="queue_name">
                                    <input
                                        type="text"
                                        name="queue_name"
                                        value={config.queue_name ?? ''}
                                        onChange={handleConfigChange}
                                        className="bg-gray-800 border border-gray-700 rounded p-2"
                                    />
                                </LabelWithTooltip>
                            </div>
                        </div>
                        <div className="mt-4">
                            <button
                                type="submit"
                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded text-white disabled:opacity-50"
                                disabled={saving}
                            >
                                {saving ? 'Saving...' : 'Save Configuration'}
                            </button>
                        </div>
                    </fieldset>
                </form>
            ) : (
                <p className="text-gray-400">No configuration available.</p>
            )}

            <div className="mt-8 border border-gray-800 rounded-lg p-4">
                <h4 className="text-lg font-semibold text-white mb-3">Manual Scaling</h4>
                <form onSubmit={handleManualScale} className="flex flex-col md:flex-row md:items-center gap-3">
                    <label className="flex flex-col text-sm text-gray-300">
                        <span className="mb-1">Desired Replicas</span>
                        <input
                            type="number"
                            min="1"
                            value={manualReplicas}
                            onChange={(event) => setManualReplicas(event.target.value)}
                            className="bg-gray-800 border border-gray-700 rounded p-2"
                            placeholder="e.g. 3"
                        />
                    </label>
                    <div className="flex gap-3">
                        <button
                            type="submit"
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded text-white"
                        >
                            Apply Manual Scale
                        </button>
                        <button
                            type="button"
                            onClick={handleClearOverride}
                            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-gray-100"
                        >
                            Clear Manual Override
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default WorkerAutoscalerPanel;

// --- END OF FILE src/components/WorkerAutoscalerPanel.jsx ---
