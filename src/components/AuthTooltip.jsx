// --- START OF FILE src/components/AuthTooltip.jsx ---
import React from 'react';

const AuthTooltip = ({ children, isAuthRequired, message }) => {
    if (isAuthRequired) {
        // The outer div with cursor-not-allowed is crucial for it to work on disabled buttons
        return (
            <div title={message} className="cursor-not-allowed">
                {/* We need to wrap the children to apply pointer-events-none so the tooltip shows */}
                <div className="pointer-events-none">
                    {children}
                </div>
            </div>
        );
    }
    return <>{children}</>; // Use a fragment for the non-authed case
};

export default AuthTooltip;
// --- END OF FILE src/components/AuthTooltip.jsx ---