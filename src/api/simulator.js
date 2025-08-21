// --- CREATE NEW FILE: src/api/simulator.js ---
import { getAuthHeaders, handleResponse } from './apiUtils';
import { API_BASE_URL } from './config.js';

const API_URL = API_BASE_URL; // Uses the centralized API configuration

// --- Generator Template (HL7 Message Templates) ---

export const getGeneratorTemplatesApi = async () => {
    const response = await fetch(`${API_URL}/api/simulator/generators`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const createGeneratorTemplateApi = async (templateData) => {
    const response = await fetch(`${API_URL}/api/simulator/generators`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(templateData),
    });
    return handleResponse(response);
};

export const updateGeneratorTemplateApi = async (id, templateData) => {
    const response = await fetch(`${API_URL}/api/simulator/generators/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(templateData),
    });
    return handleResponse(response);
};

export const deleteGeneratorTemplateApi = async (id) => {
    const response = await fetch(`${API_URL}/api/simulator/generators/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};


// --- Simulation Template (Workflow Templates) ---

export const getSimulationTemplatesApi = async () => {
    const response = await fetch(`${API_URL}/api/simulator/templates`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const createSimulationTemplateApi = async (templateData) => {
    const response = await fetch(`${API_URL}/api/simulator/templates`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(templateData),
    });
    return handleResponse(response);
};

export const updateSimulationTemplateApi = async (id, templateData) => {
    const response = await fetch(`${API_URL}/api/simulator/templates/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(templateData),
    });
    return handleResponse(response);
};

export const deleteSimulationTemplateApi = async (id) => {
    const response = await fetch(`${API_URL}/api/simulator/templates/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};


// --- Simulation Run ---

export const runSimulationApi = async (templateId, patientCount = 1) => {
    const response = await fetch(`${API_URL}/api/simulator/run`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ template_id: templateId, patient_count: patientCount }),
    });
    return handleResponse(response);
};

export const getSimulationRunsApi = async () => {
    const response = await fetch(`${API_URL}/api/simulator/runs`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const getSimulationRunApi = async (runId) => {
    const response = await fetch(`${API_URL}/api/simulator/runs/${runId}`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const deleteSimulationRunApi = async (runId) => {
    const response = await fetch(`${API_URL}/api/simulator/runs/${runId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const deleteAllSimulationRunsApi = async () => {
    const response = await fetch(`${API_URL}/api/simulator/runs`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

// --- END OF FILE: src/api/simulator.js ---