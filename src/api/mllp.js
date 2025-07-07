// By setting the base URL to an empty string, all fetch requests
// will be relative to the current domain.
// In dev, Vite's proxy will catch '/api'.
// In prod, NGINX's proxy will catch '/api'.
const API_URL = ''; // THIS IS THE KEY

export const parseHl7 = async (message) => {
    // We now add `/api` to EVERY request.
    const response = await fetch(`${API_URL}/api/parse_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.message || `Server error: ${response.status}`);
    }
    return result.data;
};

export const sendHl7 = async (host, port, message) => {
    const payload = { host, port, message };
    const response = await fetch(`${API_URL}/api/send_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.message || `Server error: ${response.status}`);
    }
    return result;
};

export const analyzeHl7 = async (message, modelName) => {
    const response = await fetch('http://localhost:5001/analyze_hl7', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        // Pass both the message and the selected model
        body: JSON.stringify({ message, model: modelName }), 
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(errorData.error || errorData.message || 'Failed to analyze message');
    }
    return response.json();
};

export const getUsageByModel = async () => {
    const response = await fetch('http://localhost:5001/get_usage_by_model');
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(errorData.error || errorData.message || 'Failed to fetch model usage');
    }
    return response.json();
};

export const getTotalUsage = async () => {
    const response = await fetch(`${API_URL}/api/get_total_token_usage`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to fetch total usage' }));
        throw new Error(errorData.message || 'An unknown error occurred.');
    }
    const data = await response.json();
    return data.total_usage;
};