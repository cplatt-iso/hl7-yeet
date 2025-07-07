// By setting the base URL to an empty string, all fetch requests
// will be relative to the current domain.
// In dev, Vite's proxy will catch '/api'.
// In prod, NGINX's proxy will catch '/api'.
const API_URL = ''; // THIS IS THE KEY

// A helper to handle errors consistently, because we're professionals.
const handleResponse = async (response) => {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(errorData.error || errorData.message || `Server responded with ${response.status}`);
    }
    return response.json();
};

export const parseHl7 = async (message) => {
    const response = await fetch(`${API_URL}/api/parse_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
    });
    const result = await handleResponse(response);
    return result.data; // The parser endpoint has a 'data' key
};

export const sendHl7 = async (host, port, message) => {
    const payload = { host, port, message };
    const response = await fetch(`${API_URL}/api/send_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    return handleResponse(response);
};

export const analyzeHl7 = async (message, modelName) => {
    const response = await fetch(`${API_URL}/api/analyze_hl7`, { // <-- CORRECTED
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, model: modelName }), 
    });
    return handleResponse(response);
};

export const getUsageByModel = async () => {
    const response = await fetch(`${API_URL}/api/get_usage_by_model`); // <-- CORRECTED
    return handleResponse(response);
};

export const getTotalUsage = async () => {
    const response = await fetch(`${API_URL}/api/get_total_token_usage`); // <-- CORRECTED (and simplified)
    const data = await handleResponse(response);
    return data.total_usage;
};