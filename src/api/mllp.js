// This is just a promise-based wrapper around the same fetch calls we had before.
// It keeps the components cleaner.

export const parseHl7 = async (message) => {
    try {
        const response = await fetch('http://localhost:5001/parse_hl7', {
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
    const payload = { host, port, message };
    try {
        const response = await fetch('http://localhost:5001/send_hl7', {
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