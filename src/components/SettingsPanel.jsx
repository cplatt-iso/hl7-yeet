import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../api/config';

const Toggle = ({ label, enabled, onChange }) => (
    <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <button
            type="button"
            className={`${enabled ? 'bg-indigo-600' : 'bg-gray-600'
                } relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-800`}
            role="switch"
            aria-checked={enabled}
            onClick={() => onChange(!enabled)}
        >
            <span
                aria-hidden="true"
                className={`${enabled ? 'translate-x-5' : 'translate-x-0'
                    } pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`}
            />
        </button>
    </div>
);

const SettingsPanel = ({ 
    showTooltips, 
    setShowTooltips, 
    selectedModel, 
    setSelectedModel,
    supportedHl7Versions,
    selectedHl7Version,
    setSelectedHl7Version
}) => {
    const [availableModels, setAvailableModels] = useState([]);
    const [loadingModels, setLoadingModels] = useState(true);

    // Fetch available models from the API
    useEffect(() => {
        const fetchModels = async () => {
            try {
                const token = localStorage.getItem('authToken');
                if (!token) {
                    console.warn('No auth token available, skipping model fetch');
                    setLoadingModels(false);
                    return;
                }
                
                const response = await axios.get(`${API_BASE_URL}/api/available_models`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                
                if (response.data.models && response.data.models.length > 0) {
                    console.log(`✓ Fetched ${response.data.models.length} models from API`);
                    setAvailableModels(response.data.models);
                    
                    // If current selected model is not in the list, select the first available
                    if (!response.data.models.includes(selectedModel)) {
                        setSelectedModel(response.data.models[0]);
                    }
                } else {
                    console.warn('API returned empty models array');
                }
            } catch (error) {
                console.error('Error fetching available models:', error);
                console.error('Error details:', error.response?.status, error.response?.data);
                // Fallback to a default set if API fails
                const fallbackModels = [
                    'models/gemini-2.5-flash',
                    'models/gemini-1.5-flash',
                ];
                setAvailableModels(fallbackModels);
                if (!fallbackModels.includes(selectedModel)) {
                    setSelectedModel(fallbackModels[0]);
                }
            } finally {
                setLoadingModels(false);
            }
        };

        fetchModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Empty dependency array - fetch once on mount, setSelectedModel is stable

    return (
        <div className="flex flex-col space-y-4 p-4 bg-gray-800 rounded-md border border-gray-700 h-fit">
            <h3 className="text-lg font-bold text-gray-300 border-b border-gray-600 pb-2 mb-2">Settings</h3>
            
            <Toggle 
                label="Show Tooltips on Hover"
                enabled={showTooltips}
                onChange={setShowTooltips}
            />

            {/* --- NEW: HL7 Version Selector --- */}
            <div>
                <label htmlFor="hl7-version-select" className="block text-sm font-medium text-gray-300 mb-1">
                    HL7 Definition Version
                </label>
                <select
                    id="hl7-version-select"
                    value={selectedHl7Version}
                    onChange={(e) => setSelectedHl7Version(e.target.value)}
                    disabled={!supportedHl7Versions || supportedHl7Versions.length === 0}
                    className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm p-2 text-white focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50"
                >
                    {supportedHl7Versions && supportedHl7Versions.length > 0 ? (
                        supportedHl7Versions.map(version => (
                            <option key={version.id} value={version.version}>
                                {version.version}
                            </option>
                        ))
                    ) : (
                        <option>Loading...</option>
                    )}
                </select>
            </div>

            {/* --- Existing AI Model Selector --- */}
            <div>
                <label htmlFor="model-select" className="block text-sm font-medium text-gray-300 mb-1">
                    AI Analysis Model {loadingModels && <span className="text-xs text-gray-400">(Loading...)</span>}
                </label>
                <select
                    id="model-select"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={loadingModels || availableModels.length === 0}
                    className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm p-2 text-white focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50"
                >
                    {availableModels.length > 0 ? (
                        availableModels.map(model => (
                            <option key={model} value={model}>
                                {model.replace('models/', '')}
                            </option>
                        ))
                    ) : (
                        <option>No models available</option>
                    )}
                </select>
            </div>
        </div>
    );
};

export default SettingsPanel;