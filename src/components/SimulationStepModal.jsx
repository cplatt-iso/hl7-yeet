// --- CREATE NEW FILE: src/components/SimulationStepModal.jsx ---
import React, { useState, useEffect } from 'react';
import SimulationStepEditor from './SimulationStepEditor';

const SimulationStepModal = ({
    isOpen,
    onClose,
    onSave,
    step: initialStep,
    generatorTemplates,
    endpoints
}) => {
    const [step, setStep] = useState(initialStep);

    useEffect(() => {
        setStep(initialStep);
    }, [initialStep]);

    if (!isOpen || !step) return null;

    const handleSave = () => {
        onSave(step);
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-2xl border border-gray-700" onClick={e => e.stopPropagation()}>
                <h2 className="text-2xl font-bold mb-6 text-white">Edit Step {step.step_order}</h2>
                
                <SimulationStepEditor
                    step={step}
                    index={step.step_order - 1} // Editor doesn't use index for logic, but for display
                    onUpdate={(_, updatedStep) => setStep(updatedStep)}
                    generatorTemplates={generatorTemplates}
                    endpoints={endpoints}
                />

                <div className="flex justify-end gap-4 mt-8">
                    <button onClick={onClose} className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-white">
                        Cancel
                    </button>
                    <button onClick={handleSave} className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 rounded text-white font-bold">
                        Save Changes
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SimulationStepModal;