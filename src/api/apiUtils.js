// --- START OF FILE src/api/apiUtils.js ---
export const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');
    const headers = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

export const handleResponse = async (response) => {
    if (response.status === 401) {
        // A proper implementation might trigger a full logout here
        throw new Error('Unauthorized. Your session may have expired.');
    }
    // Handle successful but no-content responses (like DELETE)
    if (response.status === 204 || response.status === 200 && response.headers.get("content-length") === "0") {
        return; 
    }
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || data.msg || `Server responded with ${response.status}`);
    }
    return data;
};