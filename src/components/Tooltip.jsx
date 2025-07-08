import React from 'react';

const Tooltip = ({ content, position }) => {
    if (!content) return null;

    const style = {
        position: 'absolute',
        left: `${position.x + 15}px`,
        top: `${position.y + 15}px`,
        padding: '10px',
        backgroundColor: '#1f2937', // bg-gray-800
        border: '1px solid #4b5563', // border-gray-600
        color: 'white',
        borderRadius: '8px',
        pointerEvents: 'none',
        zIndex: 100,
        maxWidth: '450px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.4)',
        transition: 'opacity 0.1s ease-in-out', // A little fade for pizzazz
    };

    // Check if the description is present and not the useless default string.
    const hasUsefulDescription = content.body && content.body !== 'No description available.';

    return (
        <div style={style}>
            <div style={{ fontWeight: 'bold', color: '#60a5fa', marginBottom: hasUsefulDescription ? '4px' : '0' }}>
                {content.title}
            </div>
            {/* ONLY render the description div if it's actually useful */}
            {hasUsefulDescription && (
                <div style={{ fontSize: '0.875rem', lineHeight: '1.25rem', color: '#d1d5db' }}>
                    {content.body}
                </div>
            )}
        </div>
    );
};

export default Tooltip;