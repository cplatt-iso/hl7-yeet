// --- START OF FILE src/api/mllp.js ---

const API_URL = ''; // Uses the Vite proxy

// --- NEW: A helper to get the auth token from localStorage ---
// This is the simplest way to do it without prop drilling or context here.
// When an API call is made, it grabs the latest token directly.
const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');
    const headers = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

const handleResponse = async (response) => {
    if (response.status === 401) {
        // This means the token is invalid or expired.
        // A more advanced implementation could trigger a logout here.
        throw new Error('Unauthorized. Your session may have expired.');
    }
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(errorData.error || errorData.message || `Server responded with ${response.status}`);
    }
    // Handle cases where the response might be empty (e.g., a 204 No Content)
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
        return response.json();
    }
    return;
};

export const getTableDefinitionsApi = async (tableId, version = '2.5.1') => {
    const response = await fetch(`/api/tables/${tableId}?version=${version}`, {
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