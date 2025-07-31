// --- START OF FILE src/api/admin.js ---

import { getAuthHeaders, handleResponse } from './apiUtils';

const API_URL = ''; // Uses Vite proxy

// ... (getHl7VersionsApi, toggleVersionStatusApi, etc. are unchanged) ...

/**
 * Fetches all processed HL7 versions from the server.
 */
export const getHl7VersionsApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/versions`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

/**
 * Toggles the 'is_active' status of a specific HL7 version.
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
 */
export const uploadVersionApi = async (file, version, description) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('version', version);
    formData.append('description', description);

    const token = localStorage.getItem('authToken');
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}/api/admin/versions/upload`, {
        method: 'POST',
        headers: headers,
        body: formData,
    });
    
    return handleResponse(response);
};

export const getTerminologyStatusApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/terminology/status`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};


// --- NEW BROWSER API FUNCTIONS ---

/**
 * Fetches a list of all unique table IDs.
 * @returns {Promise<string[]>}
 */
export const getTablesListApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/terminology/tables`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

/**
 * Fetches the definitions for a single table.
 * @param {string} tableId 
 * @returns {Promise<Array>}
 */
export const getTableDetailsApi = async (tableId) => {
    const response = await fetch(`${API_URL}/api/admin/terminology/tables/${tableId}`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

/**
 * Creates a new definition entry.
 * @param {{table_id: string, value: string, description: string}} data
 * @returns {Promise<Object>}
 */
export const createDefinitionApi = async (data) => {
    const response = await fetch(`${API_URL}/api/admin/terminology/definitions`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });
    return handleResponse(response);
};

/**
 * Updates an existing definition.
 * @param {number} defId
 * @param {{value?: string, description?: string}} data
 * @returns {Promise<Object>}
 */
export const updateDefinitionApi = async (defId, data) => {
    const response = await fetch(`${API_URL}/api/admin/terminology/definitions/${defId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });
    return handleResponse(response);
};

/**
 * Deletes a definition.
 * @param {number} defId
 * @returns {Promise<void>}
 */
export const deleteDefinitionApi = async (defId) => {
    const response = await fetch(`${API_URL}/api/admin/terminology/definitions/${defId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

/**
 * Fetches all users from the server. (Admin only)
 * @returns {Promise<Array>} A promise that resolves to an array of user objects.
 */
export const getUsersApi = async () => {
    const response = await fetch(`${API_URL}/api/admin/users`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

/**
 * Updates a user's details, e.g., their admin status. (Admin only)
 * @param {number} userId - The ID of the user to update.
 * @param {{ is_admin: boolean }} data - The update data.
 * @returns {Promise<Object>} A promise that resolves to the updated user object.
 */
export const updateUserApi = async (userId, data) => {
    const response = await fetch(`${API_URL}/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });
    return handleResponse(response);
};

/**
 * Deletes a user. (Admin only)
 * @param {number} userId - The ID of the user to delete.
 * @returns {Promise<Object>} A promise that resolves to the success message.
 */
export const deleteUserApi = async (userId) => {
    const response = await fetch(`${API_URL}/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};
// --- END OF FILE src/api/admin.js ---