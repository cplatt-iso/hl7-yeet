import React from 'react';
import AccordionItem from './AccordionItem';
import YeetLoader from './YeetLoader';

const ParserOutput = ({ isProcessing, segments, error, showEmpty, setShowEmpty, onFieldMove, onFieldUpdate, setTooltipContent }) => {
    
    // Determine the content to show inside the container
    const content = (
        <>
            {error && error !== 'Parsing...' && <div className="text-red-400 p-4">{error}</div>}
            {(!error || error === 'Parsing...') && segments.length === 0 && <div className="text-gray-500 p-4">Waiting to parse... go on, do something</div>}
            {(!error || error === 'Parsing...') && segments.length > 0 && segments.map((segment, index) => (
                <AccordionItem
                    key={`${segment.name}-${index}`}
                    segment={segment}
                    segmentIndex={index}
                    showEmpty={showEmpty}
                    onFieldMove={onFieldMove}
                    onFieldUpdate={onFieldUpdate}
                    setTooltipContent={setTooltipContent}
                />
            ))}
        </>
    );

    return (
        <div>
            <div className="flex justify-between items-center mb-1">
                <label className="block text-sm font-medium text-gray-400">Live hl7appy Parser | Drag to move | Double click to edit</label>
                <label htmlFor="show-empty-toggle" className="flex items-center cursor-pointer">
                    <span className="mr-3 text-sm font-medium text-gray-400">Show Empty Fields</span>
                    <div className="relative">
                        <input type="checkbox" id="show-empty-toggle" className="sr-only peer" checked={showEmpty} onChange={() => setShowEmpty(!showEmpty)} />
                        <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-checked:bg-indigo-600"></div>
                        <div className="absolute left-1 top-1 bg-white border-gray-300 border rounded-full h-4 w-4 transition-transform peer-checked:translate-x-full">
                        </div>
                    </div>
                </label>
            </div>
            <div id="parser-output" className="relative mt-1 border border-gray-700 rounded-md bg-gray-800 space-y-1 p-1 min-h-[200px]">
                {/* The YeetLoader is an overlay */}
                {isProcessing && <YeetLoader />}

                {/* The content underneath is ALWAYS rendered to maintain page height.
                    We just make it invisible when processing. This is the key to fixing the scroll jump. */}
                <div className={isProcessing ? 'invisible' : ''}>
                    {content}
                </div>
            </div>
        </div>
    );
};

export default ParserOutput;