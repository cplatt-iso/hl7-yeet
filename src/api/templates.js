// --- START OF FILE src/api/templates.js ---

import { getAuthHeaders, handleResponse } from './apiUtils'; // We'll create this helper file next

export const getTemplatesApi = async () => {
    const response = await fetch('/api/templates', {
        headers: getAuthHeaders()
    });
    return handleResponse(response);
};

export const saveTemplateApi = async (name, content) => {
    const response = await fetch('/api/templates', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name, content })
    });
    return handleResponse(response);
};

export const deleteTemplateApi = async (templateId) => {
    const response = await fetch(`/api/templates/${templateId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    // DELETE might not return a body, so we handle that.
    if (response.status === 200) return { message: 'Success' }; 
    return handleResponse(response);
};