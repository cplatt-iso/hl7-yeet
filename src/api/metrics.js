// --- START OF FILE src/api/metrics.js ---
import { API_BASE_URL } from './config';
import { getAuthHeaders, handleResponse } from './apiUtils';

const buildQueryString = (params) => {
    const query = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') {
            return;
        }
        query.append(key, value);
    });
    const qs = query.toString();
    return qs ? `?${qs}` : '';
};

export const fetchRunMetrics = async (params = {}) => {
    const response = await fetch(
        `${API_BASE_URL}/metrics/runs${buildQueryString(params)}`,
        {
            headers: getAuthHeaders(),
        }
    );
    return handleResponse(response);
};

export const fetchWorkerMetrics = async (params = {}) => {
    const response = await fetch(
        `${API_BASE_URL}/metrics/workers${buildQueryString(params)}`,
        {
            headers: getAuthHeaders(),
        }
    );
    return handleResponse(response);
};

const downloadCsv = async (url, filename) => {
    const response = await fetch(url, {
        headers: getAuthHeaders(),
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Download failed with status ${response.status}`);
    }
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
};

export const downloadRunMetricsCsv = async (params = {}) => {
    const url = `${API_BASE_URL}/metrics/runs${buildQueryString({ ...params, format: 'csv' })}`;
    await downloadCsv(url, 'run-metrics.csv');
};

export const downloadWorkerMetricsCsv = async (params = {}) => {
    const url = `${API_BASE_URL}/metrics/workers${buildQueryString({ ...params, format: 'csv' })}`;
    await downloadCsv(url, 'worker-metrics.csv');
};
// --- END OF FILE src/api/metrics.js ---
