// --- START OF FILE src/components/ParserOutput.jsx ---
import React, { useState, useEffect } from 'react';
import AccordionItem from './AccordionItem';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import YeetLoader from './YeetLoader';

// No changes to this component's own code, just passing a new prop down.

const ParserOutput = ({ isProcessing, segments, error, showEmpty, setShowEmpty, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips, onShowDictionary }) => {
    
    const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(0);

    useEffect(() => {
        if (segments && segments.length > 0) {
            setSelectedSegmentIndex(0);
        }
    }, [segments]);

    const handleToggleEmpty = () => {
        setShowEmpty(!showEmpty);
    };

    if (error) {
        return <div className="p-4 bg-red-900/50 text-red-300 rounded-md">{error}</div>;
    }

    if (!segments.length && !isProcessing) {
        return (
            <div className="p-4 text-center text-gray-500 border-2 border-dashed border-gray-700 rounded-md">
                No message parsed yet. Paste something in the box above, ya dingus.
            </div>
        );
    }
    
    const selectedSegment = segments[selectedSegmentIndex];

    return (
        <div className="relative">
            {isProcessing && <YeetLoader />}
            <div className={`transition-opacity duration-300 ${isProcessing ? 'opacity-30' : 'opacity-100'}`}>
                <div className="flex justify-end items-center mb-2">
                    <div className="flex items-center">
                        <input 
                            type="checkbox" 
                            id="show-empty" 
                            checked={showEmpty} 
                            onChange={handleToggleEmpty}
                            className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-indigo-600 focus:ring-indigo-500"
                        />
                        <label htmlFor="show-empty" className="ml-2 text-sm text-gray-300">Show Empty Fields</label>
                    </div>
                </div>

                <div className="flex gap-4">
                    <div className="w-48 flex-shrink-0 bg-gray-900/50 p-2 rounded-md border border-gray-700/50">
                        <div className="flex flex-col space-y-1">
                            {segments.map((segment, index) => {
                                const errorCount = segment.fields.reduce((acc, field) => acc + (field.errors?.length || 0), 0);
                                return (
                                    <button
                                        key={`${segment.name}-${index}`}
                                        onClick={() => setSelectedSegmentIndex(index)}
                                        className={`flex items-center justify-between w-full text-left px-3 py-1.5 text-sm font-mono rounded-md transition-colors ${
                                            selectedSegmentIndex === index 
                                            ? 'bg-indigo-600 text-white font-bold' 
                                            : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
                                        }`}
                                    >
                                        <span>{segment.name}</span>
                                        {errorCount > 0 ? (
                                            <span className="bg-red-500 text-white text-xs font-semibold rounded-full px-2 py-0.5">{errorCount}</span>
                                        ) : (
                                            <span className="text-green-500">
                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                            </span>
                                        )}
                                    </button>
                                )
                            })}
                        </div>
                    </div>

                    <div className="w-3/4 flex-grow">
                        {selectedSegment && (
                            <DndProvider backend={HTML5Backend}>
                                <AccordionItem
                                    key={selectedSegmentIndex}
                                    segment={selectedSegment}
                                    segmentIndex={selectedSegmentIndex}
                                    showEmpty={showEmpty}
                                    onFieldMove={onFieldMove}
                                    onFieldUpdate={onFieldUpdate}
                                    setTooltipContent={setTooltipContent}
                                    showTooltips={showTooltips}
                                    // --- THE ONLY CHANGE IS RIGHT HERE ---
                                    // Pass the handler down to the next level.
                                    onShowDictionary={onShowDictionary}
                                />
                            </DndProvider>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ParserOutput;
// --- END OF FILE src/components/ParserOutput.jsx ---