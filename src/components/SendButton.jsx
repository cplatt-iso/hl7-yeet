// --- START OF FILE src/components/SendButton.jsx ---

import React from 'react';

// We accept a `className` prop now and actually USE it.
const SendButton = ({ isSending, onClick, disabled, className = '' }) => {
    const baseClasses = "w-full py-2 px-4 font-bold text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900 transition-colors";
    const enabledClasses = "bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500";
    const disabledClasses = "bg-gray-600 cursor-not-allowed";

    return (
        <button
            onClick={onClick}
            // If disabled, use disabled styles, otherwise use enabled styles.
            // Crucially, we append the passed-in className at the end.
            className={`${baseClasses} ${disabled ? disabledClasses : enabledClasses} ${className}`}
            disabled={disabled || isSending}
        >
            {isSending ? 'YEETING...' : 'YEET IT'}
        </button>
    );
};

export default SendButton;