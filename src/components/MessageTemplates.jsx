import React from 'react';
import { 
    createORU_R01, 
    createORM_O01, 
    createADT_A08, 
    createADT_A40,
    createORU_R01_Radiology // <-- IMPORT THE NEW FORGERY
} from '../utils/messageGenerator';

const MessageTemplates = ({ onTemplateSelect }) => {
    
    const templates = [
        { name: 'ORU (Lab Result)', generator: createORU_R01 },
        { name: 'ORU (Radiology Result)', generator: createORU_R01_Radiology }, // <-- ADD THE NEW BUTTON HERE
        { name: 'ORM (New Order)', generator: createORM_O01 },
        { name: 'ADT-A08 (Update Patient)', generator: createADT_A08 },
        { name: 'ADT-A40 (Merge Patient)', generator: createADT_A40 },
    ];

    const handleButtonClick = (generator) => {
        const message = generator();
        onTemplateSelect(message);
    };
    
    return (
        <div className="flex flex-col space-y-3 p-4 bg-gray-800 rounded-md border border-gray-700 h-fit">
            <h3 className="text-lg font-bold text-gray-300 border-b border-gray-600 pb-2 mb-2">Message Templates</h3>
            {templates.map(template => (
                <button
                    key={template.name}
                    onClick={() => handleButtonClick(template.generator)}
                    className="w-full text-left px-4 py-2 text-sm font-medium text-indigo-200 bg-indigo-900/50 rounded-md hover:bg-indigo-800/70 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
                >
                    {template.name}
                </button>
            ))}
        </div>
    );
};

export default MessageTemplates;