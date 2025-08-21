// --- START OF FILE src/api/mllp.js ---
import { getAuthHeaders, handleResponse } from './apiUtils';
import { API_BASE_URL } from './config.js';

const API_URL = API_BASE_URL; // Uses the centralized API configuration

export const pingMllpApi = async (host, port) => {
    const portAsInt = parseInt(port, 10);
    if (isNaN(portAsInt)) {
        throw new Error('Invalid port number provided for ping.');
    }
    const payload = { host, port: portAsInt };
    const response = await fetch(`${API_URL}/api/ping_mllp`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
    });
    // We want the raw response data, even for errors, so handleResponse is perfect.
    return handleResponse(response);
};

export const getTableDefinitionsApi = async (tableId) => {
    // The `version` parameter was useless since the table definitions are global.
    // Removing it to keep things clean and match the backend route.
    const response = await fetch(`${API_URL}/api/tables/${tableId}`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

// Public, no auth needed
export const getSupportedVersions = async () => {
    const response = await fetch(`${API_URL}/api/get_supported_versions`);
    return handleResponse(response);
};

// Public, no auth needed
export const parseHl7 = async (message, version) => {
    const response = await fetch(`${API_URL}/api/parse_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, version }),
    });
    const result = await handleResponse(response);
    return result.data;
};

// --- PROTECTED ENDPOINTS NOW USE getAuthHeaders() ---

export const sendHl7 = async (host, port, message) => {
    const payload = { host, port, message };
    const response = await fetch(`${API_URL}/api/send_hl7`, {
        method: 'POST',
        headers: getAuthHeaders(), // <-- The magic
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
};

export const analyzeHl7 = async (message, modelName, hl7Version) => {
    const response = await fetch(`${API_URL}/api/analyze_hl7`, {
        method: 'POST',
        headers: getAuthHeaders(), // <-- The magic
        body: JSON.stringify({ 
            message, 
            model: modelName, 
            version: hl7Version
        }), 
    });
    return handleResponse(response);
};

// These two could be public or private, but let's lock them down for consistency
export const getUsageByModel = async () => {
    const response = await fetch(`${API_URL}/api/get_usage_by_model`, { headers: getAuthHeaders() });
    return handleResponse(response);
};

export const getTotalUsage = async () => {
    const response = await fetch(`${API_URL}/api/get_total_token_usage`, { headers: getAuthHeaders() });
    const data = await handleResponse(response);
    return data.total_usage;
};

// And we need to modify the listener API calls as well

export const startListenerApi = async (port) => {
    const response = await fetch(`${API_URL}/api/listener/start`, {
        method: 'POST',
        headers: getAuthHeaders(), // <-- The magic
        body: JSON.stringify({ port }),
    });
    return handleResponse(response);
};

export const stopListenerApi = async () => {
    const response = await fetch(`${API_URL}/api/listener/stop`, {
        method: 'POST',
        headers: getAuthHeaders(), // <-- The magic
    });
    return handleResponse(response);
};