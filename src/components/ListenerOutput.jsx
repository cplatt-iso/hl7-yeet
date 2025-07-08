import React from 'react';

// A small, self-contained component for each received message
const ReceivedMessage = ({ message }) => {
    const [isCopied, setIsCopied] = React.useState(false);

    const handleCopy = async () => {
        if (isCopied) return;
        await navigator.clipboard.writeText(message.message);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    return (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700/50 shadow-lg relative">
            <div className="flex justify-between items-center text-xs text-gray-400 mb-2 font-mono">
                <span>FROM: {message.from}</span>
                <span>{message.timestamp}</span>
            </div>
            <pre className="text-sm font-mono bg-gray-900 p-3 rounded-md overflow-x-auto whitespace-pre-wrap break-words">
                {message.message}
            </pre>
            <button
                onClick={handleCopy}
                title={isCopied ? "Copied!" : "Copy to clipboard"}
                className="absolute top-2 right-2 p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
            >
                {isCopied ? (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                )}
            </button>
        </div>
    );
};


// The main output component, now with a clear button
const ListenerOutput = ({ messages, onClear }) => {
    if (!messages.length) {
        return (
            <div className="p-8 text-center text-gray-500 border-2 border-dashed border-gray-700 rounded-md mt-8">
                Waiting for incoming messages...
            </div>
        );
    }

    return (
        <div className="mt-8">
            <div className="flex justify-end mb-4">
                <button
                    onClick={onClear}
                    className="px-4 py-2 text-xs font-semibold text-white bg-red-700 rounded-md hover:bg-red-800 transition-colors"
                >
                    Clear Log
                </button>
            </div>
            <div className="space-y-4">
                {messages.map((msg, index) => (
                    // Use a unique key based on timestamp and content to prevent weird re-renders
                    <ReceivedMessage key={`${msg.timestamp}-${index}`} message={msg} />
                ))}
            </div>
        </div>
    );
};

export default ListenerOutput;