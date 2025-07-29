// --- START OF FILE src/api/destinations.js ---
import { getAuthHeaders, handleResponse } from './apiUtils';

const API_URL = ''; // Uses Vite proxy

/**
 * Fetches all saved destinations for the logged-in user.
 * @returns {Promise<Array>} A promise that resolves to an array of destinations.
 */
export const getDestinations = async () => {
    const response = await fetch(`${API_URL}/api/destinations`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

/**
 * Adds a new destination for the logged-in user.
 * @param {string} name - The name for the new destination.
 * @param {string} host - The hostname or IP address.
 * @param {number} port - The port number.
 * @returns {Promise<Object>} A promise that resolves to the newly created destination object.
 */
export const addDestination = async (name, host, port) => {
    const response = await fetch(`${API_URL}/api/destinations`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name, hostname: host, port })
    });
    return handleResponse(response);
};

/**
 * Deletes a destination by its ID.
 * @param {number} id - The ID of the destination to delete.
 * @returns {Promise<Object>} A promise that resolves to the success message.
 */
export const deleteDestination = async (id) => {
    const response = await fetch(`${API_URL}/api/destinations/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};
// --- END OF FILE src/api/destinations.js ---
