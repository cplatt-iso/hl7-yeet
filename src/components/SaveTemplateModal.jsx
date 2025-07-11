// --- START OF FILE src/components/SaveTemplateModal.jsx ---

import React, { useState } from 'react';

const SaveTemplateModal = ({ isOpen, onClose, onSave, error }) => {
    const [templateName, setTemplateName] = useState('');

    if (!isOpen) return null;

    const handleSave = () => {
        if (templateName.trim()) {
            onSave(templateName);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
            <div className="bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-md">
                <h2 className="text-xl font-bold mb-4">Save Message as Template</h2>
                {error && <p className="text-red-400 bg-red-900/50 p-2 rounded-md mb-4">{error}</p>}
                <div>
                    <label htmlFor="template-name" className="block text-sm font-medium text-gray-400 mb-1">
                        Template Name
                    </label>
                    <input
                        type="text"
                        id="template-name"
                        value={templateName}
                        onChange={(e) => setTemplateName(e.target.value)}
                        className="w-full px-4 py-2 text-white bg-gray-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        autoFocus
                    />
                </div>
                <div className="flex justify-end gap-4 mt-6">
                    <button onClick={onClose} className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded-md">
                        Cancel
                    </button>
                    <button onClick={handleSave} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md">
                        Save
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SaveTemplateModal;