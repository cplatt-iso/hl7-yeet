import React from 'react';

const ListenerPanel = ({ port, setPort, isListening, onStart, onStop }) => {
    const handleToggle = () => {
        if (isListening) {
            onStop();
        } else {
            onStart();
        }
    };

    return (
        <div className="p-4 bg-gray-800 rounded-md border border-gray-700">
            <h3 className="text-lg font-bold text-gray-300 mb-4">MLLP Listener</h3>
            <div className="flex items-end gap-4">
                <div className="flex-grow">
                    <label htmlFor="listener-port" className="block text-sm font-medium text-gray-400">Listen on Port</label>
                    <input
                        type="number"
                        id="listener-port"
                        value={port}
                        onChange={(e) => setPort(e.target.value)}
                        disabled={isListening}
                        className="mt-1 block w-full bg-gray-700 border-gray-600 rounded-md shadow-sm p-2 disabled:bg-gray-800"
                    />
                </div>
                <button
                    onClick={handleToggle}
                    className={`w-36 h-[42px] font-bold rounded-md transition-colors text-white flex items-center justify-center ${
                        isListening 
                        ? 'bg-red-600 hover:bg-red-700' 
                        : 'bg-green-600 hover:bg-green-700'
                    }`}
                >
                    {isListening ? (
                        <>
                         <span className="relative flex h-3 w-3 mr-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-white"></span>
                        </span>
                        STOP
                        </>
                    ) : 'START'}
                </button>
            </div>
        </div>
    );
};

export default ListenerPanel;