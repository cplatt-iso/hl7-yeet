// --- START OF FILE src/api/listener.js ---

const API_URL = ''; // Uses the Vite proxy

// We need the same helper function that mllp.js has.
// In a larger app, we'd put this in a shared utility file.
// For now, duplicating it is fine. It's two fucking lines.
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

// Same error handler for consistency
const handleResponse = async (response) => {
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || err.msg || 'Failed to perform listener action');
    }
    return response.json();
};


export const startListenerApi = async (port) => {
    const response = await fetch(`${API_URL}/api/listener/start`, {
        method: 'POST',
        headers: getAuthHeaders(), // <-- THE MISSING GODDAMN PIECE
        body: JSON.stringify({ port }),
    });
    return handleResponse(response);
};

export const stopListenerApi = async () => {
    const response = await fetch(`${API_URL}/api/listener/stop`, {
        method: 'POST',
        headers: getAuthHeaders(), // <-- AND ITS BROTHER
    });
    return handleResponse(response);
};

export const getMessagesApi = async ({ page, perPage, search }) => {
    const params = new URLSearchParams({ page, per_page: perPage });
    if (search) {
        params.append('search', search);
    }
    const response = await fetch(`${API_URL}/api/listener/messages?${params.toString()}`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const getMessageDetailApi = async (messageId) => {
    const response = await fetch(`${API_URL}/api/listener/messages/${messageId}`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const clearMessagesApi = async () => {
    const response = await fetch(`${API_URL}/api/listener/messages`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};