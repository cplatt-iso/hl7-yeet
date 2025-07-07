import React from 'react';
import AccordionItem from './AccordionItem';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import YeetLoader from './YeetLoader';

// Adding showTooltips to the props list to pass it down
const ParserOutput = ({ isProcessing, segments, error, showEmpty, setShowEmpty, onFieldMove, onFieldUpdate, setTooltipContent, showTooltips }) => {
    
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

    return (
        <div className="relative">
            {isProcessing && <YeetLoader />}
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
            <DndProvider backend={HTML5Backend}>
                <div className={`space-y-2 transition-opacity duration-300 ${isProcessing ? 'opacity-30' : 'opacity-100'}`}>
                    {segments.map((segment, index) => (
                        <AccordionItem
                            key={`${segment.name}-${index}`}
                            segment={segment}
                            segmentIndex={index}
                            showEmpty={showEmpty}
                            onFieldMove={onFieldMove}
                            onFieldUpdate={onFieldUpdate}
                            setTooltipContent={setTooltipContent}
                            showTooltips={showTooltips} // <-- PASS IT DOWN
                        />
                    ))}
                </div>
            </DndProvider>
        </div>
    );
};

export default ParserOutput;