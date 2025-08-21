// --- START OF FILE src/api/listener.js ---

import { getAuthHeaders, handleResponse } from './apiUtils';
import { API_BASE_URL } from './config.js';

const API_URL = API_BASE_URL; // Uses the centralized API configuration


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