// --- START OF FILE src/components/MessageTemplates.jsx ---
import React, { useState, useMemo } from 'react';
import { deleteTemplateApi } from '../api/templates';
import { getHl7MessageType } from '../utils/hl7';
import { fakerTemplates } from '../api/fakerTemplates';

const ChevronIcon = ({ isOpen }) => ( <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}> <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /> </svg> );
const StarIcon = () => ( <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-amber-400 mr-2" viewBox="0 0 20 20" fill="currentColor"> <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /> </svg> );

const MessageTemplates = ({ onTemplateSelect, userTemplates, onDeleteSuccess }) => {
    const [openGroups, setOpenGroups] = useState([]);

    const handleToggleGroup = (groupName) => {
        setOpenGroups(prevOpenGroups => {
            if (prevOpenGroups.includes(groupName)) {
                return prevOpenGroups.filter(name => name !== groupName);
            } else {
                return [...prevOpenGroups, groupName];
            }
        });
    };

    const handleDelete = async (e, templateId) => { e.stopPropagation(); if (window.confirm('Are you sure you want to delete this template?')) { try { await deleteTemplateApi(templateId); onDeleteSuccess(); } catch (error) { console.error('Failed to delete template:', error); alert(`Error: ${error.message}`); } } };

    // --- MODIFIED: Grouping logic is now simpler and more direct ---
    const groupedTemplates = useMemo(() => {
        const allTemplates = [...fakerTemplates, ...(userTemplates || [])];
        if (allTemplates.length === 0) return {};
        
        return allTemplates.reduce((accumulator, template) => {
            // Use the pre-defined type for static templates, parse for user templates.
            const messageType = template.isStatic 
                ? template.messageType 
                : getHl7MessageType(template.content) || 'Uncategorized';
            
            if (!accumulator[messageType]) {
                accumulator[messageType] = [];
            }
            accumulator[messageType].push(template);
            return accumulator;
        }, {});
    }, [userTemplates]);

    // --- NEW: The click handler is now much smarter ---
    const handleTemplateClick = (template) => {
        if (template.isStatic && template.generator) {
            // It's a faker template, call the generator function to get fresh content
            onTemplateSelect(template.generator());
        } else {
            // It's a user-saved template, use the stored content
            onTemplateSelect(template.content);
        }
    };

    const sortedGroupKeys = Object.keys(groupedTemplates).sort();

    return (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-gray-200 p-4 border-b border-gray-700">Message Templates</h3>
            <div className="p-2 space-y-1">
                {sortedGroupKeys.length > 0 ? (
                    sortedGroupKeys.map(groupName => {
                        const templatesInGroup = groupedTemplates[groupName];
                        const isOpen = openGroups.includes(groupName);

                        return (
                            <div key={groupName}>
                                <button onClick={() => handleToggleGroup(groupName)} className="w-full flex justify-between items-center p-3 text-left bg-gray-700/50 hover:bg-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500">
                                    <span className="font-semibold text-gray-100">{groupName} ({templatesInGroup.length})</span>
                                    <ChevronIcon isOpen={isOpen} />
                                </button>
                                <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? 'max-h-screen' : 'max-h-0'}`}>
                                    <div className="pt-2 pl-4 space-y-1">
                                        {templatesInGroup.map(template => (
                                            <div key={template.id} className="group flex justify-between items-center text-sm p-2 rounded-md hover:bg-indigo-600/20 cursor-pointer"
                                                // --- MODIFIED: Use the new smart click handler ---
                                                onClick={() => handleTemplateClick(template)}
                                            >
                                                <div className="flex items-center">
                                                    {template.isStatic && <StarIcon />}
                                                    <span className="text-gray-300 group-hover:text-white">{template.name}</span>
                                                </div>
                                                {!template.isStatic && (
                                                    <button onClick={(e) => handleDelete(e, template.id)} className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 p-1 rounded-full hover:bg-red-500/20 transition-opacity" title="Delete Template">
                                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        );
                    })
                ) : ( <p className="p-4 text-sm text-gray-500">No saved templates.</p> )}
            </div>
        </div>
    );
};

export default MessageTemplates;
// --- END OF FILE src/components/MessageTemplates.jsx ---