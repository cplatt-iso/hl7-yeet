import React from 'react';

const Tooltip = ({ content, position }) => {
    if (!content) return null;

    const style = {
        position: 'absolute',
        left: `${position.x + 15}px`,
        top: `${position.y + 15}px`,
        padding: '10px',
        backgroundColor: '#1f2937',
        border: '1px solid #4b5563',
        color: 'white',
        borderRadius: '8px',
        pointerEvents: 'none',
        zIndex: 100,
        maxWidth: '450px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.4)',
    };

    return (
        <div style={style}>
            <div style={{ fontWeight: 'bold', color: '#60a5fa', marginBottom: '4px' }}>{content.title}</div>
            <div style={{ fontSize: '0.875rem', lineHeight: '1.25rem', color: '#d1d5db' }}>{content.description}</div>
        </div>
    );
};

export default Tooltip;