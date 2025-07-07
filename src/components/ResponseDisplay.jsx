import React from 'react';
import { parseAck } from '../utils/ackParser'; // <-- IMPORT THE PARSER

const ResponseDisplay = ({ response }) => {
    // If we have an ACK, parse it. Otherwise, handle the simple error case.
    const displayData = response.ack ? parseAck(response.ack) : {
        status: response.success ? 'Success' : 'Error',
        color: response.success ? 'text-green-400' : 'text-red-400',
        message: response.message,
        raw: response.ack || null
    };

    return (
        <div className="mt-4 p-4 bg-gray-800 rounded-md">
            <h3 className={`font-bold text-lg mb-2 ${displayData.color}`}>
                {displayData.status}
            </h3>
            <p className="text-sm text-gray-300">{displayData.message}</p>
            {displayData.raw && (
                 <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-400">Show Raw ACK</summary>
                    <pre className="text-xs bg-gray-900 p-2 mt-1 rounded-md overflow-x-auto">{displayData.raw}</pre>
                </details>
            )}
        </div>
    );
};

export default ResponseDisplay;