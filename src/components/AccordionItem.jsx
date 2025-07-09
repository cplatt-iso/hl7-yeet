// --- START OF FILE AccordionItem.jsx ---

import React, { useState } from 'react';
import FieldRow from './FieldRow';

const AccordionItem = ({ segment, segmentIndex, showEmpty, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips }) => {
    const [isOpen, setIsOpen] = useState(true);

    const visibleFields = segment.fields.filter(field => showEmpty || (field.value && field.value.trim() !== ''));

    if (visibleFields.length === 0) {
        return null;
    }

    return (
        <div className="bg-gray-800 rounded-md">
            <div className="flex justify-between items-center p-3 cursor-pointer bg-gray-700 hover:bg-gray-600 rounded-md" onClick={() => setIsOpen(!isOpen)}>
                <span className="font-bold text-white">{segment.name}</span>
                <svg className={`chevron h-5 w-5 text-gray-400 ${isOpen ? 'rotate-180' : ''}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
            </div>
            {isOpen && (
                <div className="p-2">
                    <table className="w-full text-left font-mono text-sm">
                        <thead className="text-gray-400 text-xs uppercase">
                            <tr>
                                <th className="py-2 px-2 w-20">ID</th>
                                <th className="py-2 px-2 w-1/4">Name</th>
                                <th className="py-2 px-2 w-32">Data Type</th>
                                {/* --- NEW COMPACT HEADERS --- */}
                                <th className="py-2 px-2 w-12 text-center" title="Optionality">Opt</th>
                                <th className="py-2 px-2 w-12 text-center" title="Repeatability">Rpt</th>
                                <th className="py-2 px-2 w-16">Length</th>
                                <th className="py-2 px-2 w-auto">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {segment.fields.map((field, fieldIndex) => {
                                const isFieldEmpty = !field.value || field.value.trim() === '';
                                if (!showEmpty && isFieldEmpty) return null;

                                return (
                                    <FieldRow
                                        key={field.field_id}
                                        field={field}
                                        segmentIndex={segmentIndex}
                                        fieldIndex={fieldIndex}
                                        onFieldMove={onFieldMove}
                                        onFieldUpdate={onFieldUpdate}
                                        setTooltipContent={setTooltipContent}
                                        showTooltips={showTooltips}
                                    />
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default React.memo(AccordionItem);