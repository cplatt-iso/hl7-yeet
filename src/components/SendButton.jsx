import React from 'react';

const SendButton = ({ isSending, onClick, className = '' }) => {
    // A base set of classes that all buttons will share
    const baseClasses = "bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white font-bold rounded-md flex items-center justify-center transition-all";

    return (
        <button
            onClick={onClick}
            disabled={isSending}
            // Combine the base classes with any custom classes passed in
            className={`${baseClasses} ${className}`}
        >
            {isSending ? (
                <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    YEETING...
                </>
            ) : (
                'YEET IT'
            )}
        </button>
    );
};

export default SendButton;