import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import AnalysisLoader from './AnalysisLoader';

const reconstructHl7FromJson = (fixedMessage) => {
  if (!fixedMessage || typeof fixedMessage !== 'object' || Object.keys(fixedMessage).length === 0) {
    return "<No fix suggested or fix is empty>";
  }

  try {
    // The order of segments is important. We can't rely on object key order.
    // We'll define a standard order and then add any other segments from the message.
    const standardSegmentOrder = ["MSH", "PID", "PV1", "ORC", "OBR", "ZDS"];
    const presentSegments = Object.keys(fixedMessage);
    
    const sortedSegments = standardSegmentOrder
      .filter(seg => presentSegments.includes(seg))
      .concat(presentSegments.filter(seg => !standardSegmentOrder.includes(seg)));

    return sortedSegments.map(segmentName => {
      const fields = fixedMessage[segmentName];
      const fieldSeparator = segmentName === 'MSH' ? fields['MSH.1'] : '|';
      
      // Get field keys (e.g., "MSH.1", "MSH.2"), extract the number, and sort.
      const fieldKeys = Object.keys(fields).sort((a, b) => {
        const numA = parseInt(a.split('.')[1], 10);
        const numB = parseInt(b.split('.')[1], 10);
        return numA - numB;
      });

      // Find the highest field number to determine the number of fields.
      const maxField = Math.max(...fieldKeys.map(k => parseInt(k.split('.')[1], 10)));
      
      // Create an array to hold all field values up to the max.
      const fieldValues = new Array(maxField).fill('');

      fieldKeys.forEach(key => {
        const index = parseInt(key.split('.')[1], 10) - 1;
        if (index >= 0) {
          fieldValues[index] = fields[key];
        }
      });

      // For MSH, the segment name is followed immediately by the field separator.
      // The first field is MSH.2, but our array is 0-indexed, so it's at index 1.
      if (segmentName === 'MSH') {
        return `${segmentName}${fieldSeparator}${fieldValues.slice(1).join(fieldSeparator)}`;
      }
      
      return `${segmentName}${fieldSeparator}${fieldValues.join(fieldSeparator)}`;
    }).join('\r');
  } catch (error) {
    console.error("Failed to reconstruct HL7 from JSON:", error);
    // Fallback to showing the raw object if reconstruction fails
    return JSON.stringify(fixedMessage, null, 2);
  }
};


const AnalysisPanel = ({ analysisResult, onShowDiff, onClear, onRetry, isLoading, totalTokenUsage, selectedModel, modelUsage }) => {
  const [isPromptVisible, setIsPromptVisible] = useState(false);
  const [isRawOutputVisible, setIsRawOutputVisible] = useState(false);

  const reconstructedHl7 = useMemo(() => {
    if (!analysisResult?.fixed_message) {
      return null;
    }

    try {
      let messageObject;
      if (typeof analysisResult.fixed_message === 'string') {
        // The backend sends fixed_message as a stringified JSON object,
        // but it doesn't properly escape backslashes for special characters, leading to invalid JSON.
        // e.g., it sends '..."MSH.2":"^~\&"...' instead of '..."MSH.2":"^~\\&"...'
        // This regex finds backslashes that are NOT followed by a valid JSON escape character
        // and replaces them with a double backslash.
        const correctedJsonString = analysisResult.fixed_message.replace(/\\(?![\\/"bfnrt]|u[0-9a-fA-F]{4})/g, '\\\\');
        messageObject = JSON.parse(correctedJsonString);
      } else {
        // If it's already an object, use it directly.
        messageObject = analysisResult.fixed_message;
      }
      return reconstructHl7FromJson(messageObject);
    } catch (error) {
      console.error("Failed to parse or reconstruct HL7 from fixed_message:", error);
      // Fallback for malformed JSON or other errors
      return "Error: Could not display the suggested fix.";
    }
  }, [analysisResult]);

  if (!analysisResult && !isLoading) {
    return null;
  }

  const shouldShowFixSection = analysisResult?.fixed_message !== undefined;
  const shouldShowPromptButton = analysisResult?.prompt;

  const handleApplyClick = () => {
    if (reconstructedHl7) {
      // Check if the reconstruction was successful before showing the diff.
      // A successful reconstruction will start with 'MSH|' or similar.
      // An unsuccessful one will start with "Error:" or "{".
      if (reconstructedHl7.startsWith('Error:') || reconstructedHl7.startsWith('{')) {
        alert("Cannot show diff because the suggested fix could not be formatted as a valid HL7 message. Please check the 'Raw AI Output' for details.");
        return;
      }
      onShowDiff(reconstructedHl7);
    }
  };
  const currentModelTotal = modelUsage[selectedModel] || 0;

  return (
    <>
      <div className="flex flex-col space-y-3 p-4 bg-gray-800 rounded-md border border-gray-700 h-fit">
        <div className="flex justify-between items-center border-b border-gray-600 pb-2 mb-2">
          <div className="flex items-baseline gap-2 flex-wrap">
              <h3 className="text-lg font-bold text-gray-300">AI Analysis</h3>
              
              {analysisResult?.usage && (
                  <>
                      <span className="text-xs text-gray-400 bg-gray-700 px-2 py-0.5 rounded-full" title="Tokens used for this specific request">
                          Request: {analysisResult.usage.total_tokens.toLocaleString()}
                      </span>
                      <span className="text-xs text-cyan-400 bg-cyan-900/50 px-2 py-0.5 rounded-full" title={`Total tokens used by ${selectedModel}`}>
                          {selectedModel}: {currentModelTotal.toLocaleString()}
                      </span>
                  </>
              )}
              
              {totalTokenUsage > 0 && (
                   <span className="text-xs text-indigo-400 bg-indigo-900/50 px-2 py-0.5 rounded-full" title="Grand total tokens used across all models">
                    Total: {totalTokenUsage.toLocaleString()}
                  </span>
              )}
          </div>
          <button onClick={onClear} title="Close Analysis" className="p-1 rounded-full hover:bg-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {isLoading && (
          <AnalysisLoader />
        )}

        {analysisResult && !isLoading && (
          <div className="text-sm text-gray-300 space-y-4">
            <div className="prose prose-sm prose-invert max-w-none">
              <ReactMarkdown>{analysisResult.explanation || "No explanation provided."}</ReactMarkdown>
            </div>
            
            {shouldShowFixSection && (
              <div>
                <h4 className="font-bold mb-2 text-gray-400">Suggested Fix:</h4>
                <pre className="text-xs bg-gray-900 p-2 mb-3 rounded-md overflow-x-auto max-h-60">
                  {reconstructedHl7 || "<No fix suggested or fix is empty>"}
                </pre>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-4">
                    <button 
                      onClick={handleApplyClick}
                      disabled={!reconstructedHl7}
                      className="px-4 py-2 font-semibold text-white bg-green-600 rounded-md hover:bg-green-700 disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors text-sm"
                    >
                      Apply & View Diff
                    </button>
                    <button
                      onClick={onRetry}
                      className="px-4 py-2 font-semibold text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors text-sm"
                    >
                      Try Again
                    </button>
                    <button
                      onClick={onClear}
                      className="px-4 py-2 font-semibold text-white bg-red-700 rounded-md hover:bg-red-800 transition-colors text-sm"
                    >
                      This is Crap
                    </button>
                </div>

                {shouldShowPromptButton && (
                  <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <button
                      onClick={() => setIsPromptVisible(true)}
                      className="w-full px-4 py-2 font-semibold text-white bg-gray-600 rounded-md hover:bg-gray-700 transition-colors text-sm"
                    >
                      Show AI Prompt
                    </button>
                    <button
                      onClick={() => setIsRawOutputVisible(true)}
                      className="w-full px-4 py-2 font-semibold text-white bg-gray-600 rounded-md hover:bg-gray-700 transition-colors text-sm"
                    >
                      Show Raw AI Output
                    </button>
                  </div>
                )}

              </div>
            )}
          </div>
        )}
      </div>

      {isPromptVisible && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setIsPromptVisible(false)}
        >
          <div 
            className="bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-4 border-b border-gray-700">
              <h3 className="text-lg font-bold text-gray-200">AI Prompt</h3>
              <button onClick={() => setIsPromptVisible(false)} className="p-1 rounded-full hover:bg-gray-700">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                {analysisResult.prompt}
              </pre>
            </div>
          </div>
        </div>
      )}

      {isRawOutputVisible && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setIsRawOutputVisible(false)}
        >
          <div 
            className="bg-gray-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex justify-between items-center p-4 border-b border-gray-700">
              <h3 className="text-lg font-bold text-gray-200">Raw AI Output</h3>
              <button onClick={() => setIsRawOutputVisible(false)} className="p-1 rounded-full hover:bg-gray-700">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                {JSON.stringify(analysisResult, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AnalysisPanel;