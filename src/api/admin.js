// --- START OF FILE src/api/admin.js ---

import { getAuthHeaders, handleResponse } from './apiUtils';

const API_URL = ''; // Uses Vite proxy

/**
 * Fetches all processed HL7 versions from the server.
 * Requires admin privileges.
 * @returns {Promise<Array>} A promise that resolves to an array of version objects.
 */
export const getHl7VersionsApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/versions`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

/**
 * Toggles the 'is_active' status of a specific HL7 version.
 * Requires admin privileges.
 * @param {number} versionId - The ID of the version to toggle.
 * @returns {Promise<Object>} A promise that resolves to the updated version object.
 */
export const toggleVersionStatusApi = async (versionId) => {
    const response = await fetch(`${API_URL}/api/admin/versions/${versionId}/toggle`, {
        method: 'PATCH',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

/**
 * Triggers a refresh of the global V2 terminology tables from HL7's servers.
 * Requires admin privileges.
 * @returns {Promise<Object>} A promise that resolves to the success message from the backend.
 */
export const refreshTerminologyApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/terminology/refresh`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

/**
 * Uploads a new HL7 version definition zip file.
 * Requires admin privileges.
 * @param {File} file - The zip file to upload.
 * @param {string} version - The version string for the new version (e.g., "2.8").
 * @param {string} description - An optional description for the version.
 * @returns {Promise<Object>} A promise that resolves to the success message.
 */
export const uploadVersionApi = async (file, version, description) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('version', version);
    formData.append('description', description);

    // Note: We don't set Content-Type for FormData. The browser does it correctly.
    // We only need the auth header.
    const token = localStorage.getItem('authToken');
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}/api/admin/versions/upload`, {
        method: 'POST',
        headers: headers, // <-- No 'Content-Type': 'application/json'
        body: formData,
    });
    
    // The response could be success or a validation error, handleResponse is perfect
    return handleResponse(response);
};

export const getTerminologyStatusApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/terminology/status`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};
// --- END OF FILE src/api/admin.js ---