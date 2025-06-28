// This file now makes requests to the relative '/api' path.
// In development, the Vite proxy handles this.
// In production, your NGINX proxy will handle this.
// The frontend code is now blissfully unaware of the backend's actual address.

export const parseHl7 = async (message) => {
    try {
        const response = await fetch('/api/parse_hl7', { // <-- THE CHANGE
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.message || `Server error: ${response.status}`);
        }
        return result.data;
    } catch (error) {
        console.error("Failed to parse HL7:", error);
        throw error; // Re-throw to be caught by the component
    }
};

export const sendHl7 = async (host, port, message) => {
    // IMPORTANT NOTE: The `send_hl7` API endpoint in Flask doesn't use the
    // `host` and `port` from the UI to find the Python server. It uses them
    // as *parameters* to know where to send the MLLP message from Python.
    // So the fetch call itself still goes through our proxy.
    const payload = { host, port, message };
    try {
        const response = await fetch('/api/send_hl7', { // <-- THE CHANGE
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.message || `Server error: ${response.status}`);
        }
        return result;
    } catch (error) {
        console.error("Failed to send HL7:", error);
        throw error;
    }
};

export const analyzeHl7 = async (message) => {
    try {
        const response = await fetch('/api/analyze_hl7', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.error || `Server error during analysis: ${response.status}`);
        }
        return result;
    } catch (error) {
        console.error("Failed to analyze HL7:", error);
        throw error;
    }
};