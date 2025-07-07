import React from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer';

const DiffModal = ({ isOpen, onClose, onConfirm, originalText, newText }) => {
    if (!isOpen) return null;

    // --- NEW: NORMALIZE LINE ENDINGS FOR THE VIEWER ---
    // The diff viewer library works best with standard newline characters (\n).
    // HL7 often uses carriage returns (\r), so we'll replace them.
    const originalTextForViewer = originalText.replace(/\r/g, '\n');
    const newTextForViewer = newText.replace(/\r/g, '\n');

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex justify-center items-center z-[100]" onClick={onClose}>
            <div 
                // --- FIX 1: MAKE IT WIDER ---
                className="bg-gray-800 rounded-lg shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col" 
                onClick={e => e.stopPropagation()} // Prevent click from closing modal
            >
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h2 className="text-xl font-bold text-white">Confirm AI Suggested Fix</h2>
                    <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-700">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="overflow-auto flex-grow p-4">
                    <div className="font-mono text-xs border border-gray-700 rounded-md">
                        <ReactDiffViewer
                            // --- FIX 2: USE THE NORMALIZED TEXT ---
                            oldValue={originalTextForViewer}
                            newValue={newTextForViewer}
                            splitView={true}
                            compareMethod={DiffMethod.WORDS}
                            leftTitle="Original Message"
                            rightTitle="Suggested Fix"
                            styles={{
                                diffContainer: { backgroundColor: '#1f2937' },
                                gutter: { backgroundColor: '#374151', '&:hover': { backgroundColor: '#4b5563' } },
                                diffViewer: { backgroundColor: '#1f2937', border: 'none' },
                                // No need to mess with white-space, the newline fix is cleaner.
                                line: { fontFamily: 'monospace', fontSize: '12px' },
                                wordDiff: { padding: '2px' },
                                wordAdded: { backgroundColor: '#059669', color: '#d1fae5' },
                                wordRemoved: { backgroundColor: '#dc2626', color: '#fee2e2' },
                                emptyLine: { backgroundColor: '#374151' },
                                lineNum: { color: '#9ca3af' },
                            }}
                        />
                    </div>
                </div>

                <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 font-semibold text-white bg-gray-600 rounded-md hover:bg-gray-500 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        className="px-4 py-2 font-semibold text-white bg-green-600 rounded-md hover:bg-green-700 transition-colors"
                    >
                        Confirm and Apply Fix
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DiffModal;