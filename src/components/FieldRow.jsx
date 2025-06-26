import React, { useState } from 'react';

const FieldRow = ({ field, segmentIndex, fieldIndex, onFieldMove, onFieldUpdate, setTooltipContent }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(field.value);

    // This effect ensures our local edit state updates if the prop from above changes
    // (e.g., from another drag/drop operation)
    React.useEffect(() => {
        setEditValue(field.value);
    }, [field.value]);

    const handleDoubleClick = () => {
        setIsEditing(true);
    };

    const handleBlur = () => {
        if (editValue !== field.value) {
            onFieldUpdate(segmentIndex, fieldIndex, editValue);
        }
        setIsEditing(false);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleBlur();
        } else if (e.key === 'Escape') {
            setEditValue(field.value); // Revert
            setIsEditing(false);
        }
    };
    
    const handleDragStart = (e) => {
        e.dataTransfer.setData('application/json', JSON.stringify({ segmentIndex, fieldIndex }));
        e.dataTransfer.effectAllowed = 'move';
        setTimeout(() => e.target.closest('.value-cell').classList.add('dragging'), 0);
    };
    const handleDragEnd = (e) => {
        const cell = e.target.closest('.value-cell') || document.querySelector('.dragging');
        if (cell) cell.classList.remove('dragging');
    }
    const handleDragOver = (e) => e.preventDefault();
    const handleDragEnter = (e) => e.currentTarget.classList.add('drag-over');
    const handleDragLeave = (e) => e.currentTarget.classList.remove('drag-over');

    const handleDrop = (e) => {
        e.preventDefault();
        e.currentTarget.classList.remove('drag-over');
        const source = JSON.parse(e.dataTransfer.getData('application/json'));
        const destination = { segmentIndex, fieldIndex };
        if (source.segmentIndex === destination.segmentIndex && source.fieldIndex === destination.fieldIndex) return;
        onFieldMove(source, destination);
    };

    return (
        <tr
            onMouseEnter={() => setTooltipContent({ title: field.name || field.field_id, description: field.description })}
            onMouseLeave={() => setTooltipContent(null)}
        >
            <td className="p-2 text-gray-500 align-top">{field.field_id}</td>
            <td className="p-2 text-gray-300 align-top">{field.name}</td>
            <td className="p-2 text-cyan-400 align-top text-xs">{field.data_type}</td>
            <td className="p-2 text-gray-400 align-top">{field.length}</td>
            <td
                className="p-2 text-green-300 break-words align-top value-cell draggable-value"
                onDoubleClick={handleDoubleClick}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
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
                        draggable={!isEditing && field.value && field.value.trim() !== ''} 
                        onDragStart={handleDragStart} 
                        onDragEnd={handleDragEnd}
                        className="w-full h-full"
                    >
                        {field.value ? field.value : <span className="text-gray-600">&lt;empty&gt;</span>}
                    </div>
                )}
            </td>
        </tr>
    );
};

// --- AND ANOTHER MAGIC SHIELD ---
export default React.memo(FieldRow);