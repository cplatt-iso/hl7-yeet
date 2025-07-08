import React, { useState, useEffect } from 'react';
import AccordionItem from './AccordionItem';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import YeetLoader from './YeetLoader';

const ParserOutput = ({ isProcessing, segments, error, showEmpty, setShowEmpty, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips }) => {
    
    // --- NEW STATE ---
    // Keep track of the index of the segment we want to display in detail.
    // Default to 0 (the MSH segment) if segments exist.
    const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(0);

    // Effect to reset the selected index when the segments change (e.g., new message)
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
                {/* --- HEADER CONTROLS --- */}
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

                {/* --- MASTER-DETAIL LAYOUT --- */}
                <div className="flex gap-4">
                    {/* --- LEFT PANEL: The Navigator --- */}
                    <div className="w-48 flex-shrink-0 bg-gray-900/50 p-2 rounded-md border border-gray-700/50">
                        <div className="flex flex-col space-y-1">
                            {segments.map((segment, index) => (
                                <button
                                    key={`${segment.name}-${index}`}
                                    onClick={() => setSelectedSegmentIndex(index)}
                                    className={`w-full text-left px-3 py-1.5 text-sm font-mono rounded-md transition-colors ${
                                        selectedSegmentIndex === index 
                                        ? 'bg-indigo-600 text-white font-bold' 
                                        : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
                                    }`}
                                >
                                    {/* Handle repeating segments like OBX by showing their set ID */}
                                    {segment.name} {segment.name === 'OBX' && `[${segment.fields[0]?.value || '?'}]`}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* --- RIGHT PANEL: The Detail View --- */}
                    <div className="w-3/4 flex-grow">
                        {selectedSegment && (
                            <DndProvider backend={HTML5Backend}>
                                <AccordionItem
                                    // Use a key that changes when the segment changes to ensure it re-renders
                                    key={selectedSegmentIndex}
                                    segment={selectedSegment}
                                    segmentIndex={selectedSegmentIndex}
                                    showEmpty={showEmpty}
                                    onFieldMove={onFieldMove}
                                    onFieldUpdate={onFieldUpdate}
                                    setTooltipContent={setTooltipContent}
                                    showTooltips={showTooltips}
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