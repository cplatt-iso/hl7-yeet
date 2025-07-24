// --- START OF FILE src/components/FieldRow.jsx ---
import React, { useState, useEffect } from 'react';
import { useDrag, useDrop } from 'react-dnd';

const ItemTypes = {
    FIELD: 'field'
};

const BookIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
);

const FieldRow = ({ field, segmentIndex, fieldIndex, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips, onShowDictionary }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(field.value);
    const [componentValues, setComponentValues] = useState([]);

    // The critical useEffect hook that syncs incoming props with internal state.
    // This was missing from one of my versions, and is essential.
    useEffect(() => {
        setComponentValues(field.components?.map(c => c.value || '') || []);
    }, [field.components]);


    const hasErrors = field.errors && field.errors.length > 0;
    const isComponentized = field.components && field.components.length > 0;

    const handleDoubleClick = () => {
        setIsEditing(true);
        // We set the simple editValue here for non-componentized fields
        setEditValue(field.value);
        // The componentValues are already synced by the useEffect hook.
    };

    const handleBlur = () => {
        setIsEditing(false);
        if (isComponentized) {
            const newValue = componentValues.join('^');
            if (newValue !== field.value) {
                onFieldUpdate(segmentIndex, fieldIndex, newValue);
            }
        } else {
            if (editValue !== field.value) {
                onFieldUpdate(segmentIndex, fieldIndex, editValue);
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleBlur();
        }
        if (e.key === 'Escape') {
            setIsEditing(false);
        }
    };

    const handleComponentChange = (compIndex, newCompValue) => {
        const newComponentValues = [...componentValues];
        newComponentValues[compIndex] = newCompValue;
        setComponentValues(newComponentValues);
    };

    const handleMouseEnter = () => {
        if (hasErrors) {
            setTooltipContent({
                title: 'Validation Errors',
                body: field.errors.join('\n'),
                type: 'error'
            });
        } else if (showTooltips) {
            setTooltipContent({
                title: field.name,
                body: field.description
            });
        }
    };

    const handleMouseLeave = () => {
        setTooltipContent(null);
    };
    
    const originalIndex = { segmentIndex, fieldIndex };
    const [{ isDragging }, drag] = useDrag(() => ({
        type: ItemTypes.FIELD,
        item: { source: originalIndex, value: field.value },
        canDrag: () => field.value && field.value.trim() !== '',
        collect: (monitor) => ({
            isDragging: monitor.isDragging(),
        }),
    }), [segmentIndex, fieldIndex, field.value]);

    const [, drop] = useDrop(() => ({
        accept: ItemTypes.FIELD,
        drop: (item) => {
            onFieldMove(item.source, { segmentIndex, fieldIndex });
        },
    }), [segmentIndex, fieldIndex, onFieldMove]);

    return (
        <tr className={`${hasErrors ? 'bg-red-500/10' : ''}`} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
            <td className="py-1 px-2 text-gray-500">{field.field_id}</td>
            <td className="py-1 px-2 text-gray-300">{field.name}</td>
            <td className="py-1 px-2 text-indigo-300">
                <div className="flex items-center gap-2">
                    <span>{field.data_type}</span>
                    {field.table && (
                        <button onClick={() => onShowDictionary(field.table, segmentIndex, fieldIndex)} className="text-blue-400 hover:text-blue-300 transition-colors" title={`View values for Table ${field.table}`}>
                            <BookIcon />
                        </button>
                    )}
                </div>
            </td>
            <td className={`py-1 px-2 text-center font-bold ${field.optionality === 'R' ? 'text-orange-400' : field.optionality === 'C' ? 'text-blue-400' : 'text-gray-500 font-normal'}`} title={field.optionality === 'R' ? 'Required' : 'Optional'}>{field.optionality}</td>
            <td className={`py-1 px-2 text-center font-bold ${field.repeatable === 'Y' ? 'text-green-400' : 'text-gray-500 font-normal'}`} title={field.repeatable === 'Y' ? 'Repeatable' : 'Not Repeatable'}>{field.repeatable}</td>
            <td className="py-1 px-2 text-yellow-300">{field.length}</td>
            <td ref={drop} className={`py-1 px-2 value-cell rounded-sm ${hasErrors ? 'bg-red-500/20' : ''}`} onDoubleClick={handleDoubleClick}>
                {isEditing ? (
                    isComponentized ? (
                        <div className="flex flex-wrap gap-1" onBlur={handleBlur} onKeyDown={handleKeyDown}>
                            {field.components.map((comp, compIndex) => (
                                <div key={compIndex} className="flex items-center bg-gray-900/50 rounded">
                                    <span className="text-xs text-gray-500 px-1" title={comp.name}>{compIndex + 1}</span>
                                    <input type="text" value={componentValues[compIndex] || ''} onChange={(e) => handleComponentChange(compIndex, e.target.value)} className="bg-transparent focus:bg-gray-700 w-auto min-w-[50px] flex-grow p-0.5 rounded-r" autoFocus={compIndex === 0}/>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <input type="text" value={editValue} onChange={(e) => setEditValue(e.target.value)} onBlur={handleBlur} onKeyDown={handleKeyDown} autoFocus className="w-full bg-gray-700 p-0.5 rounded"/>
                    )
                ) : (
                    <div ref={drag} className={`w-full h-full min-h-[24px] ${isDragging ? 'opacity-30' : ''} ${field.value ? 'cursor-grab' : ''}`}>
                        {isComponentized ? (
                            <div className="flex flex-wrap gap-1 items-center">
                                {field.components.map((comp, index) => (
                                    comp.value && <span key={index} className="bg-indigo-900/60 px-2 py-0.5 rounded text-indigo-200 text-xs" title={comp.name}>{comp.value}</span>
                                ))}
                                {!field.value && <span className="text-gray-600">""</span>}
                            </div>
                        ) : (
                            field.value || <span className="text-gray-600">""</span>
                        )}
                    </div>
                )}
            </td>
        </tr>
    );
};

export default React.memo(FieldRow);
// --- END OF FILE src/components/FieldRow.jsx ---