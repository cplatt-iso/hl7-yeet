import React, { useState } from 'react';
import { useDrag, useDrop } from 'react-dnd';

const ItemTypes = {
    FIELD: 'field'
};

// We now accept 'showTooltips' to conditionally show the definitions
const FieldRow = ({ field, segmentIndex, fieldIndex, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(field.value);
    
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
        // ONLY show tooltip if the setting is enabled
        if (showTooltips) {
            setTooltipContent({
                title: field.name,
                body: field.description
            });
        }
    };

    const handleMouseLeave = () => {
        // ALWAYS clear tooltip on leave
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
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
        >
            <td className="py-1 px-2 text-gray-500">{field.field_id}</td>
            <td className="py-1 px-2 text-gray-300">{field.name}</td>
            <td className="py-1 px-2 text-indigo-300">{field.data_type}</td>
            <td className="py-1 px-2 text-yellow-300">{field.length}</td>
            <td 
                ref={drop}
                className="py-1 px-2 value-cell"
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