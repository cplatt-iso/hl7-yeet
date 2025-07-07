import React from 'react';

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


// --- THIS IS THE CORRECTED FUNCTION SIGNATURE ---
const SettingsPanel = ({ showTooltips, setShowTooltips, selectedModel, setSelectedModel }) => {

    const availableModels = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-2.5-flash',
        'gemini-2.5-pro',
    ];

    return (
        <div className="flex flex-col space-y-4 p-4 bg-gray-800 rounded-md border border-gray-700 h-fit">
            <h3 className="text-lg font-bold text-gray-300 border-b border-gray-600 pb-2 mb-2">Settings</h3>
            
            <Toggle 
                label="Show Tooltips on Hover"
                enabled={showTooltips}
                onChange={setShowTooltips}
            />

            <div>
                <label htmlFor="model-select" className="block text-sm font-medium text-gray-300 mb-1">
                    AI Analysis Model
                </label>
                <select
                    id="model-select"
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm p-2 text-white focus:ring-indigo-500 focus:border-indigo-500"
                >
                    {availableModels.map(model => (
                        <option key={model} value={model}>
                            {model}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
};

export default SettingsPanel;