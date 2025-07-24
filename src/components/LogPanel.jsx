// --- START OF FILE src/components/LogPanel.jsx ---
import React from 'react';

// A simple chevron-up icon. No need for a whole library.
const ChevronUpIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
    </svg>
);

// And its brother, chevron-down.
const ChevronDownIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
);


const LogEntry = ({ entry }) => {
    const getLogColors = (type) => {
        switch (type) {
            case 'success': return 'bg-green-900/50 border-green-500/60 text-green-200';
            case 'error': return 'bg-red-900/50 border-red-500/60 text-red-200';
            default: return 'bg-gray-700/50 border-gray-600/60 text-gray-300';
        }
    };
    const colors = getLogColors(entry.type);
    return (
        <div className={`p-3 rounded-md border text-sm font-mono ${colors}`}>
            <div className="flex justify-between items-center mb-1">
                <span className="font-semibold text-gray-100">{entry.type.toUpperCase()}</span>
                <span className="text-xs text-gray-400">{entry.timestamp}</span>
            </div>
            <pre className="whitespace-pre-wrap break-all text-xs">{entry.message}</pre>
        </div>
    );
};

// --- MODIFIED: Accept new props for collapsing ---
const LogPanel = ({ logs, onClear, isCollapsed, onToggleCollapse }) => {
    return (
        <div className="flex flex-col h-full bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            <div className="flex justify-between items-center p-3 border-b border-gray-700 bg-gray-800/80 backdrop-blur-sm shrink-0">
                <h3 className="font-semibold text-gray-200">Send Log</h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={onClear}
                        disabled={logs.length === 0}
                        className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-500 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Clear Log
                    </button>
                    {/* --- NEW: Our glorious doohickey --- */}
                    <button
                        onClick={onToggleCollapse}
                        title={isCollapsed ? "Show Log" : "Hide Log"}
                        className="p-1 rounded-md hover:bg-gray-700"
                    >
                        {isCollapsed ? <ChevronDownIcon /> : <ChevronUpIcon />}
                    </button>
                </div>
            </div>
            {/* --- MODIFIED: Conditionally render the body based on the prop --- */}
            {!isCollapsed && (
                <>
                    {logs.length > 0 ? (
                        <div className="p-3 space-y-3 overflow-y-auto flex-grow">
                            {logs.map((entry) => (
                                <LogEntry key={entry.id} entry={entry} />
                            ))}
                        </div>
                    ) : (
                        <div className="flex-grow flex items-center justify-center p-4">
                            <p className="text-sm text-gray-500">Click "Send Message" to see connection logs here.</p>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default LogPanel;
// --- END OF FILE src/components/LogPanel.jsx ---