// --- START OF FILE src/api/templates.js ---

import { getAuthHeaders, handleResponse } from './apiUtils'; // We'll create this helper file next
import { API_BASE_URL } from './config.js';

const API_URL = API_BASE_URL; // Uses the centralized API configuration

export const getTemplatesApi = async () => {
    const response = await fetch(`${API_URL}/api/templates`, {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

export const saveTemplateApi = async (name, content) => {
    const response = await fetch(`${API_URL}/api/templates`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name, content })
    });
    return handleResponse(response);
};

export const deleteTemplateApi = async (templateId) => {
    const response = await fetch(`${API_URL}/api/templates/${templateId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    // DELETE might not return a body, so we handle that.
    if (response.status === 200) return { message: 'Success' }; 
    return handleResponse(response);
};