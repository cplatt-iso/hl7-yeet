const API_URL = ''; // Uses the proxy

export const startListenerApi = async (port) => {
    const response = await fetch(`${API_URL}/api/listener/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port }),
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to start listener');
    }
    return response.json();
};

export const stopListenerApi = async () => {
    const response = await fetch(`${API_URL}/api/listener/stop`, {
        method: 'POST',
    });
     if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || 'Failed to stop listener');
    }
    return response.json();
};