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

export const getSimulationRunApi = async (runId, options = {}) => {
    const { eventsLimit, eventsOffset, eventsOrder } = options;
    const params = new URLSearchParams();

    if (eventsLimit !== undefined && eventsLimit !== null) {
        params.set('events_limit', eventsLimit);
    }
    if (eventsOffset !== undefined && eventsOffset !== null) {
        params.set('events_offset', eventsOffset);
    }
    if (eventsOrder) {
        params.set('events_order', eventsOrder);
    }

    const query = params.toString();
    const url = query
        ? `${API_URL}/api/simulator/runs/${runId}?${query}`
        : `${API_URL}/api/simulator/runs/${runId}`;

    const response = await fetch(url, {
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

export const getSimulationRunMetricsApi = async (runId, options = {}) => {
    const { jobsLimit, jobsOffset, jobsOrder } = options;
    const params = new URLSearchParams();

    if (jobsLimit !== undefined && jobsLimit !== null) {
        params.set('jobs_limit', jobsLimit);
    }
    if (jobsOffset !== undefined && jobsOffset !== null) {
        params.set('jobs_offset', jobsOffset);
    }
    if (jobsOrder) {
        params.set('jobs_order', jobsOrder);
    }

    const query = params.toString();
    const url = query
        ? `${API_URL}/api/simulator/runs/${runId}/metrics?${query}`
        : `${API_URL}/api/simulator/runs/${runId}/metrics`;

    const response = await fetch(url, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};


// --- Exam Factory Integration ---

const buildQueryString = (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            params.set(key, value);
        }
    });
    const query = params.toString();
    return query ? `?${query}` : '';
};

export const getExamCatalogApi = async (filters = {}) => {
    const query = buildQueryString(filters);
    const response = await fetch(`${API_URL}/api/simulator/exams${query}`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const getExamSpecApi = async (examId) => {
    const response = await fetch(`${API_URL}/api/simulator/exams/${encodeURIComponent(examId)}`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const getExamModalitiesApi = async () => {
    const response = await fetch(`${API_URL}/api/simulator/exams/modalities`, {
        headers: getAuthHeaders(),
    });
    return handleResponse(response);
};

export const selectExamSpecApi = async (filters = {}) => {
    const response = await fetch(`${API_URL}/api/simulator/exams/select`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(filters || {}),
    });
    return handleResponse(response);
};

// --- END OF FILE: src/api/simulator.js ---