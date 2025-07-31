import React from 'react';

const InfoCallout = ({ children }) => (
    <div className="p-4 mb-4 text-sm text-blue-200 bg-blue-900/50 rounded-lg flex items-start gap-3">
        <div className="font-bold text-blue-400 text-xl shrink-0">ℹ️</div>
        <div>
            {children}
        </div>
    </div>
);

export default InfoCallout;
