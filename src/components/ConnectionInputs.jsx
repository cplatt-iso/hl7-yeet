import React from 'react';
import SendButton from './SendButton'; // We'll need this here now

const ConnectionInputs = ({ host, setHost, port, setPort, isSending, handleSend }) => (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        {/* Host input now takes up 2 columns */}
        <div className="md:col-span-2">
            <label htmlFor="host" className="block text-sm font-medium text-gray-400">Host</label>
            <input 
                type="text" 
                id="host" 
                value={host} 
                onChange={(e) => setHost(e.target.value)} 
                className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2" 
            />
        </div>
        {/* Port input takes up 1 column */}
        <div>
            <label htmlFor="port" className="block text-sm font-medium text-gray-400">Port</label>
            <input 
                type="number" 
                id="port" 
                value={port} 
                onChange={(e) => setPort(e.target.value)} 
                className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2" 
            />
        </div>
        {/* The new YEET button takes up the last column */}
        <div className="flex items-end">
            <SendButton 
                onClick={handleSend} 
                isSending={isSending} 
                // We pass in specific classes for this smaller, inline version
                className="w-full h-[42px] text-base" 
            />
        </div>
    </div>
);

export default ConnectionInputs;