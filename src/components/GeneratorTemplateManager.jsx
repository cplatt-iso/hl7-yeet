// --- CREATE NEW FILE: src/components/GeneratorTemplateManager.jsx ---
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { getGeneratorTemplatesApi, createGeneratorTemplateApi, updateGeneratorTemplateApi, deleteGeneratorTemplateApi } from '../api/simulator';
import { PlusIcon, TrashIcon, PencilSquareIcon, CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

const GeneratorTemplateManager = () => {
    const { isAdmin } = useAuth();
    const [templates, setTemplates] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(null); // Holds ID of template being edited
    const [editData, setEditData] = useState({});
    const [showCreateForm, setShowCreateForm] = useState(false);

    const initialFormState = { name: '', message_type: '', content: '' };
    const [newTemplate, setNewTemplate] = useState(initialFormState);

    const fetchTemplates = async () => {
        setIsLoading(true);
        try {
            const data = await getGeneratorTemplatesApi();
            setTemplates(data);
        } catch (error) {
            toast.error(`Failed to fetch generator templates: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchTemplates();
    }, []);

    const handleCreateChange = (e) => {
        const { name, value } = e.target;
        setNewTemplate(prev => ({ ...prev, [name]: value }));
    };

    const handleEditChange = (e) => {
        const { name, value } = e.target;
        setEditData(prev => ({ ...prev, [name]: value }));
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        const toastId = toast.loading('Creating template...');
        try {
            const created = await createGeneratorTemplateApi(newTemplate);
            setTemplates(prev => [...prev, created]);
            setNewTemplate(initialFormState);
            setShowCreateForm(false);
            toast.success(`Template "${created.name}" created.`, { id: toastId });
        } catch (error) {
            toast.error(`Failed to create template: ${error.message}`, { id: toastId });
        }
    };

    const handleUpdate = async () => {
        const toastId = toast.loading('Updating template...');
        try {
            // We need to send the full object for update, as per our backend route
            const fullUpdateData = {
                name: editData.name,
                message_type: editData.message_type,
                content: editData.content,
            };
            const updated = await updateGeneratorTemplateApi(isEditing, fullUpdateData);
            setTemplates(prev => prev.map(t => (t.id === isEditing ? updated : t)));
            setIsEditing(null);
            toast.success(`Template "${updated.name}" updated.`, { id: toastId });
        } catch (error) {
            toast.error(`Failed to update template: ${error.message}`, { id: toastId });
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to delete this generator template? This could break simulations that use it.")) return;
        const toastId = toast.loading('Deleting template...');
        try {
            await deleteGeneratorTemplateApi(id);
            setTemplates(prev => prev.filter(t => t.id !== id));
            toast.success('Template deleted.', { id: toastId });
        } catch (error) {
            toast.error(`Failed to delete template: ${error.message}`, { id: toastId });
        }
    };

    const startEditing = (template) => {
        setIsEditing(template.id);
        setEditData(template);
    };

    const cancelEditing = () => {
        setIsEditing(null);
        setEditData({});
    };

    if (!isAdmin) {
        return <p className="text-yellow-400">This feature is available to administrators only.</p>;
    }
    
    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-200">HL7 Generator Templates</h3>
                <button 
                    onClick={() => setShowCreateForm(prev => !prev)}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md text-sm font-semibold"
                >
                    <PlusIcon className="h-5 w-5" /> {showCreateForm ? 'Cancel' : 'New Template'}
                </button>
            </div>
            
            {showCreateForm && (
                 <form onSubmit={handleCreate} className="p-4 mb-6 bg-gray-900 rounded-lg flex flex-col gap-4">
                     <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                         <input name="name" value={newTemplate.name} onChange={handleCreateChange} placeholder="Template Name (e.g., 'ADT-A08 Update')" className="bg-gray-800 p-2 rounded border border-gray-700" required />
                         <input name="message_type" value={newTemplate.message_type} onChange={handleCreateChange} placeholder="Message Type (e.g., ADT^A08)" className="bg-gray-800 p-2 rounded border border-gray-700" required />
                     </div>
                     <textarea name="content" value={newTemplate.content} onChange={handleCreateChange} rows="10" placeholder="Enter HL7 message content with {$Faker...} cues..." className="bg-gray-800 p-2 rounded border border-gray-700 font-mono text-sm" required />
                     <div className="flex justify-end">
                         <button type="submit" className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-md font-semibold">Save New Template</button>
                     </div>
                 </form>
            )}

            <div className="space-y-4">
                {isLoading && <p>Loading templates...</p>}
                {templates.map(template => (
                    <div key={template.id} className="bg-gray-900/50 rounded-lg border border-gray-700">
                        {isEditing === template.id ? (
                            <div className="p-4 space-y-3">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <input name="name" value={editData.name} onChange={handleEditChange} className="bg-gray-800 p-2 rounded border border-gray-700" />
                                    <input name="message_type" value={editData.message_type} onChange={handleEditChange} className="bg-gray-800 p-2 rounded border border-gray-700" />
                                </div>
                                <textarea name="content" value={editData.content} onChange={handleEditChange} rows="10" className="w-full bg-gray-800 p-2 rounded border border-gray-700 font-mono text-sm" />
                                <div className="flex gap-2 justify-end">
                                    <button onClick={handleUpdate} className="p-2 bg-green-600 hover:bg-green-700 rounded"><CheckIcon className="h-5 w-5" /></button>
                                    <button onClick={cancelEditing} className="p-2 bg-gray-600 hover:bg-gray-500 rounded"><XMarkIcon className="h-5 w-5" /></button>
                                </div>
                            </div>
                        ) : (
                            <div className="p-4">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h4 className="font-bold text-lg text-white">{template.name}</h4>
                                        <p className="text-sm text-gray-400 font-mono">{template.message_type}</p>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={() => startEditing(template)} className="p-2 hover:bg-gray-700 rounded"><PencilSquareIcon className="h-5 w-5 text-indigo-400"/></button>
                                        <button onClick={() => handleDelete(template.id)} className="p-2 hover:bg-gray-700 rounded"><TrashIcon className="h-5 w-5 text-red-400"/></button>
                                    </div>
                                </div>
                                <pre className="mt-4 p-3 bg-gray-800 rounded text-xs text-gray-300 font-mono overflow-x-auto">
                                    <code>{template.content}</code>
                                </pre>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default GeneratorTemplateManager;
// --- END OF FILE: src/components/GeneratorTemplateManager.jsx ---