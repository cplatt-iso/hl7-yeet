// --- CREATE NEW FILE: src/api/endpoints.js ---
import { getAuthHeaders, handleResponse } from './apiUtils';

const API_URL = ''; // Uses Vite proxy

/**
 * Fetches all saved endpoints. (Admin or User)
 * @returns {Promise<Array>} A promise that resolves to an array of endpoints.
 */
export const getEndpointsApi = async () => {
    const response = await fetch(`${API_URL}/api/endpoints`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

/**
 * Creates a new endpoint. (Admin only)
 * @param {object} endpointData - The full endpoint object.
 * @returns {Promise<Object>} A promise that resolves to the newly created endpoint object.
 */
export const createEndpointApi = async (endpointData) => {
    const response = await fetch(`${API_URL}/api/endpoints`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(endpointData)
    });
    return handleResponse(response);
};

/**
 * Updates an existing endpoint. (Admin only)
 * @param {number} id - The ID of the endpoint to update.
 * @param {object} endpointData - The fields to update.
 * @returns {Promise<Object>} A promise that resolves to the updated endpoint object.
 */
export const updateEndpointApi = async (id, endpointData) => {
    const response = await fetch(`${API_URL}/api/endpoints/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(endpointData)
    });
    return handleResponse(response);
};

/**
 * Deletes an endpoint by its ID. (Admin only)
 * @param {number} id - The ID of the endpoint to delete.
 * @returns {Promise<void>} A promise that resolves on success.
 */
export const deleteEndpointApi = async (id) => {
    const response = await fetch(`${API_URL}/api/endpoints/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    // This expects a 204 No Content, which our handleResponse can deal with.
    return handleResponse(response);
};
// --- END OF FILE src/api/endpoints.js ---