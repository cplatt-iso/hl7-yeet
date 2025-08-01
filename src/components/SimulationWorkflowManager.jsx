// --- CREATE NEW FILE: src/components/SimulationWorkflowManager.jsx ---
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { getSimulationTemplatesApi, createSimulationTemplateApi, updateSimulationTemplateApi, deleteSimulationTemplateApi } from '../api/simulator';
import { getGeneratorTemplatesApi } from '../api/simulator';
import { getEndpointsApi } from '../api/endpoints';
import SimulationStepEditor from './SimulationStepEditor';
import { PlusIcon } from '@heroicons/react/24/outline';

const SimulationWorkflowManager = () => {
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    // Dependencies needed for the step editor dropdowns
    const [generatorTemplates, setGeneratorTemplates] = useState([]);
    const [endpoints, setEndpoints] = useState([]);

    const fetchAllData = async () => {
        setIsLoading(true);
        try {
            const [simTemplates, genTemplates, endpointsData] = await Promise.all([
                getSimulationTemplatesApi(),
                getGeneratorTemplatesApi(),
                getEndpointsApi(),
            ]);
            setTemplates(simTemplates);
            setGeneratorTemplates(genTemplates);
            setEndpoints(endpointsData);
        } catch (error) {
            toast.error(`Failed to load workflow data: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchAllData();
    }, []);

    const handleSelectTemplate = (template) => {
        // Make a deep copy to avoid editing the original state directly
        setSelectedTemplate(JSON.parse(JSON.stringify(template)));
    };

    const handleCreateNew = () => {
        setSelectedTemplate({ name: 'New Workflow Template', description: '', steps: [] });
    };

    const handleFieldChange = (e) => {
        const { name, value } = e.target;
        setSelectedTemplate(prev => ({ ...prev, [name]: value }));
    };

    const handleStepUpdate = (index, updatedStep) => {
        const newSteps = [...selectedTemplate.steps];
        newSteps[index] = updatedStep;
        setSelectedTemplate(prev => ({ ...prev, steps: newSteps }));
    };

    const handleAddStep = () => {
        const newStep = { step_order: selectedTemplate.steps.length + 1, step_type: '', parameters: {} };
        setSelectedTemplate(prev => ({ ...prev, steps: [...prev.steps, newStep] }));
    };

    const handleStepDelete = (index) => {
        const newSteps = selectedTemplate.steps.filter((_, i) => i !== index);
        // Re-order the steps
        const reorderedSteps = newSteps.map((step, i) => ({ ...step, step_order: i + 1 }));
        setSelectedTemplate(prev => ({ ...prev, steps: reorderedSteps }));
    };

    const handleStepMove = (index, direction) => {
        const newSteps = [...selectedTemplate.steps];
        const targetIndex = direction === 'up' ? index - 1 : index + 1;
        if (targetIndex < 0 || targetIndex >= newSteps.length) return;
        
        // Swap
        [newSteps[index], newSteps[targetIndex]] = [newSteps[targetIndex], newSteps[index]];
        
        // Update step_order
        const reorderedSteps = newSteps.map((step, i) => ({ ...step, step_order: i + 1 }));
        setSelectedTemplate(prev => ({ ...prev, steps: reorderedSteps }));
    };

    const handleSave = async () => {
        const isCreating = !selectedTemplate.id;
        const toastId = toast.loading(isCreating ? 'Creating workflow...' : 'Updating workflow...');
        try {
            const payload = {
                name: selectedTemplate.name,
                description: selectedTemplate.description,
                steps: selectedTemplate.steps.map(({id, ...step}) => step) // Remove temp ID for create/update
            };

            if (isCreating) {
                await createSimulationTemplateApi(payload);
            } else {
                await updateSimulationTemplateApi(selectedTemplate.id, payload);
            }
            toast.success('Workflow saved!', { id: toastId });
            setSelectedTemplate(null); // Close editor
            fetchAllData(); // Refresh list
        } catch (error) {
            toast.error(`Save failed: ${error.message}`, { id: toastId });
        }
    };
    
    const handleDelete = async () => {
        if (!selectedTemplate.id || !window.confirm("Are you sure? This will permanently delete the workflow template.")) return;
         const toastId = toast.loading('Deleting workflow...');
        try {
            await deleteSimulationTemplateApi(selectedTemplate.id);
            toast.success('Workflow deleted.', { id: toastId });
            setSelectedTemplate(null);
            fetchAllData();
        } catch(error) {
             toast.error(`Delete failed: ${error.message}`, { id: toastId });
        }
    }

    return (
        <div className="flex gap-8">
            <div className="w-1/4">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold">Workflows</h3>
                    <button onClick={handleCreateNew} className="px-3 py-1 bg-indigo-600 text-sm rounded hover:bg-indigo-700">New</button>
                </div>
                <div className="space-y-2">
                    {isLoading ? <p>Loading...</p> : templates.map(t => (
                        <div key={t.id} onClick={() => handleSelectTemplate(t)} className={`p-3 rounded cursor-pointer ${selectedTemplate?.id === t.id ? 'bg-indigo-600 text-white' : 'bg-gray-700 hover:bg-gray-600'}`}>
                            <p className="font-semibold">{t.name}</p>
                            <p className="text-xs">{t.steps.length} steps</p>
                        </div>
                    ))}
                </div>
            </div>
            <div className="w-3/4">
                {selectedTemplate ? (
                    <div className="space-y-6">
                        <div>
                             <label className="text-sm text-gray-400">Workflow Name</label>
                             <input type="text" name="name" value={selectedTemplate.name} onChange={handleFieldChange} className="w-full bg-gray-900 p-2 rounded text-xl font-bold" />
                        </div>
                        <div>
                             <label className="text-sm text-gray-400">Description</label>
                             <textarea name="description" value={selectedTemplate.description} onChange={handleFieldChange} className="w-full bg-gray-900 p-2 rounded mt-1" rows="2" />
                        </div>
                        
                        <h3 className="text-lg font-bold">Steps</h3>
                        <div className="space-y-4">
                           {selectedTemplate.steps.map((step, index) => (
                               <SimulationStepEditor 
                                    key={index} // Using index is OK here as we don't have stable IDs until saved
                                    step={step}
                                    index={index}
                                    onUpdate={handleStepUpdate}
                                    onDelete={handleStepDelete}
                                    onMove={handleStepMove}
                                    isFirst={index === 0}
                                    isLast={index === selectedTemplate.steps.length - 1}
                                    generatorTemplates={generatorTemplates}
                                    endpoints={endpoints}
                               />
                           ))}
                        </div>
                        <button onClick={handleAddStep} className="flex items-center gap-2 w-full justify-center p-3 border-2 border-dashed border-gray-600 hover:border-indigo-500 hover:text-indigo-400 rounded-lg text-gray-400">
                           <PlusIcon className="h-6 w-6" /> Add Step
                        </button>
                        
                        <div className="flex justify-between items-center pt-4 border-t border-gray-700">
                            <button onClick={handleDelete} disabled={!selectedTemplate.id} className="px-4 py-2 text-sm bg-red-800 hover:bg-red-700 rounded disabled:opacity-50">Delete Workflow</button>
                            <div className="flex gap-4">
                                <button onClick={() => setSelectedTemplate(null)} className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-500 rounded">Cancel</button>
                                <button onClick={handleSave} className="px-6 py-2 font-bold bg-green-600 hover:bg-green-500 rounded">Save Workflow</button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-96 border-2 border-dashed border-gray-700 rounded-lg">
                        <p className="text-gray-500">Select a workflow to edit or create a new one.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SimulationWorkflowManager;
// --- END OF FILE: src/components/SimulationWorkflowManager.jsx ---