// --- START OF FILE FieldRow.jsx ---

import React, { useState } from 'react';
import { useDrag, useDrop } from 'react-dnd';

const ItemTypes = {
    FIELD: 'field'
};

const FieldRow = ({ field, segmentIndex, fieldIndex, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(field.value);

    const hasErrors = field.errors && field.errors.length > 0;
    
    const handleDoubleClick = () => {
        setIsEditing(true);
        setEditValue(field.value);
    };

    const handleBlur = () => {
        setIsEditing(false);
        if (editValue !== field.value) {
            onFieldUpdate(segmentIndex, fieldIndex, editValue);
        }
    };
    
    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleBlur();
        } else if (e.key === 'Escape') {
            setIsEditing(false);
        }
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
    
    // --- Drag-and-Drop Logic ---
    const originalIndex = { segmentIndex, fieldIndex };
    const [{ isDragging }, drag] = useDrag(() => ({
        type: ItemTypes.FIELD,
        item: { type: ItemTypes.FIELD, source: originalIndex, value: field.value },
        canDrag: () => field.value && field.value.trim() !== '',
        collect: (monitor) => ({
            isDragging: monitor.isDragging(),
        }),
    }), [segmentIndex, fieldIndex, field.value]);

    const [, drop] = useDrop(() => ({
        accept: ItemTypes.FIELD,
        drop: (item) => {
            if (item.source.segmentIndex !== segmentIndex || item.source.fieldIndex !== fieldIndex) {
                onFieldMove(item.source, { segmentIndex, fieldIndex });
            }
        },
        collect: (monitor) => ({
            isOver: monitor.isOver(),
            canDrop: monitor.canDrop(),
        }),
    }), [segmentIndex, fieldIndex, onFieldMove]);


    return (
        <tr
            className={`${hasErrors ? 'bg-red-500/10' : ''}`}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <td className="py-1 px-2 text-gray-500">{field.field_id}</td>
            <td className="py-1 px-2 text-gray-300">{field.name}</td>
            <td className="py-1 px-2 text-indigo-300">{field.data_type}</td>
            
            {/* --- OPTIONALITY CELL --- */}
            <td 
                className={`py-1 px-2 text-center font-bold ${
                    field.optionality === 'R' ? 'text-orange-400' :
                    field.optionality === 'C' ? 'text-blue-400' :
                    'text-gray-500 font-normal'
                }`}
                title={
                    field.optionality === 'R' ? 'Required' :
                    field.optionality === 'O' ? 'Optional' :
                    field.optionality === 'C' ? 'Conditional' :
                    field.optionality
                }
            >
                {field.optionality}
            </td>
            
            {/* --- REPEATABILITY CELL --- */}
            <td
                className={`py-1 px-2 text-center font-bold ${
                    field.repeatable === 'Y' ? 'text-green-400' : 'text-gray-500 font-normal'
                }`}
                title={field.repeatable === 'Y' ? 'Repeatable' : 'Not Repeatable'}
            >
                {field.repeatable}
            </td>

            <td className="py-1 px-2 text-yellow-300">{field.length}</td>
            <td 
                ref={drop}
                className={`py-1 px-2 value-cell rounded-sm ${hasErrors ? 'bg-red-500/20' : ''}`}
                onDoubleClick={handleDoubleClick}
            >
                {isEditing ? (
                    <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={handleBlur}
                        onKeyDown={handleKeyDown}
                        autoFocus
                    />
                ) : (
                    <div
                        ref={drag}
                        className={`w-full h-full ${isDragging ? 'dragging' : ''} ${field.value ? 'draggable-value' : ''}`}
                    >
                        {field.value || <span className="text-gray-600">""</span>}
                    </div>
                )}
            </td>
        </tr>
    );
};

export default FieldRow;