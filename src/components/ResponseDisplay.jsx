import React from 'react';

const ResponseDisplay = ({ response }) => (
    <div className="mt-4 p-4 bg-gray-800 rounded-md">
        <h3 className={`font-bold text-lg mb-2 ${response.success ? 'text-green-400' : 'text-red-400'}`}>
            {response.success ? '✅ Success' : '❌ Error'}
        </h3>
        <p className="text-sm">{response.message}</p>
        {response.ack && (
            <pre className="text-xs bg-gray-900 p-2 mt-2 rounded-md overflow-x-auto">{response.ack}</pre>
        )}
    </div>
);

export default ResponseDisplay;