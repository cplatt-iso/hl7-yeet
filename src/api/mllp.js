// By setting the base URL to an empty string, all fetch requests
// will be relative to the current domain.
const API_URL = ''; // This can be set via environment variables if needed

// A helper to handle errors consistently, because we're professionals.
const handleResponse = async (response) => {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: response.statusText }));
        throw new Error(errorData.error || errorData.message || `Server responded with ${response.status}`);
    }
    return response.json();
};

// --- NEW function to get the list of supported HL7 versions ---
export const getSupportedVersions = async () => {
    // This assumes your proxy is set up for /api
    const response = await fetch(`${API_URL}/api/get_supported_versions`);
    return handleResponse(response);
};

// --- UPDATED to send the HL7 version ---
export const parseHl7 = async (message, version) => {
    const response = await fetch(`${API_URL}/api/parse_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, version }), // Pass the version
    });
    const result = await handleResponse(response);
    return result.data;
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

// --- UPDATED to send both model and HL7 version ---
export const analyzeHl7 = async (message, modelName, hl7Version) => {
    const response = await fetch(`${API_URL}/api/analyze_hl7`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            message, 
            model: modelName, 
            version: hl7Version  // Pass the version
        }), 
    });
    return handleResponse(response);
};

export const getUsageByModel = async () => {
    const response = await fetch(`${API_URL}/api/get_usage_by_model`);
    return handleResponse(response);
};

export const getTotalUsage = async () => {
    const response = await fetch(`${API_URL}/api/get_total_token_usage`);
    const data = await handleResponse(response);
    return data.total_usage;
};