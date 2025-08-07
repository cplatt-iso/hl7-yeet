// --- REPLACE src/components/SimulationWorkflowManager.jsx ---
import React, { useState, useEffect, useMemo } from 'react';
import { toast } from 'react-hot-toast';
import { getSimulationTemplatesApi, createSimulationTemplateApi, updateSimulationTemplateApi, deleteSimulationTemplateApi } from '../api/simulator';
import { getGeneratorTemplatesApi } from '../api/simulator';
import { getEndpointsApi } from '../api/endpoints';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { arrayMove, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { PlusIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import WorkflowStepCard from './WorkflowStepCard';
import SimulationStepModal from './SimulationStepModal';
import { validateWorkflow } from '../utils/workflowAnalyzer';

const SimulationWorkflowManager = () => {
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    
    // Dependencies needed for the step editor
    const [generatorTemplates, setGeneratorTemplates] = useState([]);
    const [endpoints, setEndpoints] = useState([]);

    // State for the modal
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingStepIndex, setEditingStepIndex] = useState(null);

    const sensors = useSensors(useSensor(PointerSensor));

    // Validate workflow whenever steps change
    const workflowValidation = useMemo(() => {
        if (!selectedTemplate?.steps?.length) return [];
        return validateWorkflow(selectedTemplate.steps, generatorTemplates);
    }, [selectedTemplate?.steps, generatorTemplates]);

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
        const stepsWithIds = template.steps.map((step, index) => ({ ...step, id: step.id || `temp-${index}` }));
        setSelectedTemplate({ ...template, steps: stepsWithIds });
    };

    const handleCreateNew = () => {
        setSelectedTemplate({ name: 'New Workflow Template', description: '', steps: [] });
    };

    const handleFieldChange = (e) => {
        const { name, value } = e.target;
        setSelectedTemplate(prev => ({ ...prev, [name]: value }));
    };

    const handleAddStep = () => {
        const newStep = {
            id: `new-${Date.now()}`,
            step_order: selectedTemplate.steps.length + 1,
            step_type: '',
            parameters: {}
        };
        setSelectedTemplate(prev => ({ ...prev, steps: [...prev.steps, newStep] }));
        // Open the modal immediately to configure the new step
        setEditingStepIndex(selectedTemplate.steps.length);
        setIsModalOpen(true);
    };

    const handleOpenEditModal = (index) => {
        setEditingStepIndex(index);
        setIsModalOpen(true);
    };

    const handleSaveStep = (updatedStep) => {
        const newSteps = [...selectedTemplate.steps];
        newSteps[editingStepIndex] = updatedStep;
        setSelectedTemplate(prev => ({ ...prev, steps: newSteps }));
    };

    const handleStepDelete = (index) => {
        if (!window.confirm("Are you sure you want to remove this step?")) return;
        const newSteps = selectedTemplate.steps.filter((_, i) => i !== index);
        const reorderedSteps = newSteps.map((step, i) => ({ ...step, step_order: i + 1 }));
        setSelectedTemplate(prev => ({ ...prev, steps: reorderedSteps }));
    };

    const handleDragEnd = (event) => {
        const { active, over } = event;
        if (active.id !== over.id) {
            const oldIndex = selectedTemplate.steps.findIndex(step => step.id === active.id);
            const newIndex = selectedTemplate.steps.findIndex(step => step.id === over.id);
            
            const movedSteps = arrayMove(selectedTemplate.steps, oldIndex, newIndex);
            const reorderedSteps = movedSteps.map((step, index) => ({ ...step, step_order: index + 1 }));

            setSelectedTemplate(prev => ({ ...prev, steps: reorderedSteps }));
        }
    };

    const handleSaveWorkflow = async () => {
        const isCreating = !selectedTemplate.id;
        const toastId = toast.loading(isCreating ? 'Creating workflow...' : 'Updating workflow...');
        try {
            const payload = {
                name: selectedTemplate.name,
                description: selectedTemplate.description,
                // Server doesn't care about our temp frontend ID
                steps: selectedTemplate.steps.map(({ id, ...step }) => step) 
            };

            if (isCreating) {
                await createSimulationTemplateApi(payload);
            } else {
                await updateSimulationTemplateApi(selectedTemplate.id, payload);
            }
            toast.success('Workflow saved!', { id: toastId });
            setSelectedTemplate(null);
            fetchAllData();
        } catch (error) {
            toast.error(`Save failed: ${error.message}`, { id: toastId });
        }
    };
    
    const handleDeleteWorkflow = async () => {
        if (!selectedTemplate.id || !window.confirm("Are you sure? This will permanently delete the workflow.")) return;
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

    const editingStep = useMemo(() =>
        (editingStepIndex !== null && selectedTemplate) ? selectedTemplate.steps[editingStepIndex] : null,
        [editingStepIndex, selectedTemplate]
    );

    // --- THE FIX IS HERE ---
    // `dnd-kit`'s `SortableContext` needs an array of IDs, not the full objects.
    const stepIds = useMemo(
        () => (selectedTemplate ? selectedTemplate.steps.map(s => s.id) : []),
        [selectedTemplate]
    );

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
                             <textarea name="description" value={selectedTemplate.description || ''} onChange={handleFieldChange} className="w-full bg-gray-900 p-2 rounded mt-1" rows="2" />
                        </div>
                        
                        {/* Workflow Validation Warnings */}
                        {workflowValidation.length > 0 && (
                            <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-lg p-4">
                                <div className="flex items-center gap-2 mb-3">
                                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                                    <h4 className="text-yellow-400 font-semibold">Workflow Validation</h4>
                                </div>
                                <div className="space-y-2">
                                    {workflowValidation.map((warning, idx) => (
                                        <div key={idx} className={`text-sm ${warning.type === 'error' ? 'text-red-400' : 'text-yellow-400'}`}>
                                            <span className="font-medium">Step {warning.stepIndex + 1}:</span> {warning.message}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        <h3 className="text-lg font-bold">Steps</h3>
                        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                            {/* --- THIS IS THE FIX --- */}
                            <SortableContext items={stepIds} strategy={verticalListSortingStrategy}>
                                <div className="space-y-3">
                                   {selectedTemplate.steps.map((step, index) => (
                                       <WorkflowStepCard 
                                            key={step.id}
                                            step={step}
                                            index={index}
                                            onEdit={handleOpenEditModal}
                                            onDelete={handleStepDelete}
                                            generatorTemplates={generatorTemplates}
                                            endpoints={endpoints}
                                       />
                                   ))}
                                </div>
                            </SortableContext>
                        </DndContext>
                        <button onClick={handleAddStep} className="flex items-center gap-2 w-full justify-center p-3 border-2 border-dashed border-gray-600 hover:border-indigo-500 hover:text-indigo-400 rounded-lg text-gray-400">
                           <PlusIcon className="h-6 w-6" /> Add Step
                        </button>
                        
                        <div className="flex justify-between items-center pt-4 border-t border-gray-700">
                            <button onClick={handleDeleteWorkflow} disabled={!selectedTemplate.id} className="px-4 py-2 text-sm bg-red-800 hover:bg-red-700 rounded disabled:opacity-50">Delete Workflow</button>
                            <div className="flex gap-4">
                                <button onClick={() => setSelectedTemplate(null)} className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-500 rounded">Cancel</button>
                                <button onClick={handleSaveWorkflow} className="px-6 py-2 font-bold bg-green-600 hover:bg-green-500 rounded">Save Workflow</button>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-96 border-2 border-dashed border-gray-700 rounded-lg">
                        <p className="text-gray-500">Select a workflow to edit or create a new one.</p>
                    </div>
                )}
            </div>

            <SimulationStepModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSave={handleSaveStep}
                step={editingStep}
                generatorTemplates={generatorTemplates}
                endpoints={endpoints}
            />
        </div>
    );
};

export default SimulationWorkflowManager;