// --- START OF FILE src/components/MessageTemplates.jsx ---

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { deleteTemplateApi } from '../api/templates';

// --- THE CRITICAL FIX: IMPORT FROM THE CORRECT FILE ---
import { 
    createORU_R01, 
    createORM_O01, 
    createADT_A08, 
    createADT_A40,
    createORU_R01_Radiology
} from '../utils/messageGenerator';

// An Accordion helper component to keep the UI clean
const Accordion = ({ title, children, defaultOpen = false }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    return (
        <div className="bg-gray-900/50 p-4 rounded-md border border-gray-700/50">
            <button onClick={() => setIsOpen(!isOpen)} className="w-full flex justify-between items-center text-white font-bold">
                <span>{title}</span>
                <span className="text-xl">{isOpen ? '−' : '+'}</span>
            </button>
            {isOpen && <div className="pt-3 mt-3 border-t border-gray-700 space-y-2">{children}</div>}
        </div>
    );
};

// A generic button for any template
const TemplateButton = ({ children, onClick, onDelete }) => (
    <div className="flex items-center gap-2 group">
        <button onClick={onClick} className="w-full text-left p-2 bg-gray-800 hover:bg-indigo-900/50 rounded-md text-sm transition-colors">
            {children}
        </button>
        {onDelete && (
            <button onClick={onDelete} className="p-1 text-gray-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
        )}
    </div>
);

const MessageTemplates = ({ onTemplateSelect, userTemplates, onDeleteSuccess }) => {
    const { isAuthenticated } = useAuth();

    // --- ANOTHER FIX: CREATE THE FAKER TEMPLATES LIST HERE ---
    const fakerTemplates = [
        { name: 'ORU (Lab Result)', generator: createORU_R01 },
        { name: 'ORU (Radiology Result)', generator: createORU_R01_Radiology },
        { name: 'ORM (New Order)', generator: createORM_O01 },
        { name: 'ADT-A08 (Update Patient)', generator: createADT_A08 },
        { name: 'ADT-A40 (Merge Patient)', generator: createADT_A40 },
    ];

    const handleDelete = async (templateId) => {
        if (window.confirm('Are you sure you want to delete this template?')) {
            try {
                await deleteTemplateApi(templateId);
                onDeleteSuccess(); // Tell the parent to refetch the list
            } catch (error) {
                console.error("Failed to delete template:", error);
                alert("Error: Could not delete the template.");
            }
        }
    };

    return (
        <div className="space-y-4">
            <h2 className="text-lg font-semibold px-4">Message Templates</h2>
            
            {isAuthenticated && userTemplates.length > 0 && (
                <Accordion title="My Templates" defaultOpen={true}>
                    {userTemplates.map(template => (
                        <TemplateButton 
                            key={template.id} 
                            onClick={() => onTemplateSelect(template.content)}
                            onDelete={() => handleDelete(template.id)}
                        >
                            {template.name}
                        </TemplateButton>
                    ))}
                </Accordion>
            )}

            <Accordion title="Faker Templates" defaultOpen={!isAuthenticated || userTemplates.length === 0}>
                {fakerTemplates.map((template) => (
                    <TemplateButton key={template.name} onClick={() => onTemplateSelect(template.generator())}>
                        {template.name}
                    </TemplateButton>
                ))}
            </Accordion>
        </div>
    );
};

export default MessageTemplates;