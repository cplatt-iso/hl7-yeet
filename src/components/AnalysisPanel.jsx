import React from 'react';
import ReactMarkdown from 'react-markdown';
import AnalysisLoader from './AnalysisLoader'; // <-- IMPORT OUR NEW MASTERPIECE

const AnalysisPanel = ({ analysisResult, onApplyFix, onClear, isLoading }) => {
  if (!analysisResult && !isLoading) {
    return null; // Don't render anything if there's no analysis
  }

  const shouldShowFixSection = analysisResult?.fixed_message !== undefined;

  return (
    <div className="flex flex-col space-y-3 p-4 bg-gray-800 rounded-md border border-gray-700 h-fit">
      <div className="flex justify-between items-center border-b border-gray-600 pb-2 mb-2">
        <h3 className="text-lg font-bold text-gray-300">AI Analysis</h3>
        <button onClick={onClear} title="Close Analysis" className="p-1 rounded-full hover:bg-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {isLoading && (
        // SAY GOODBYE TO THE WHIRLYGIG OF SHAME...
        // AND HELLO TO THE TERMINAL OF POWER!
        <AnalysisLoader />
      )}

      {analysisResult && !isLoading && ( // Added !isLoading to ensure loader is gone
        <div className="text-sm text-gray-300 space-y-4">
          <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown>{analysisResult.explanation || "No explanation provided."}</ReactMarkdown>
          </div>
          
          {shouldShowFixSection && (
            <div>
              <h4 className="font-bold mb-2 text-gray-400">Suggested Fix:</h4>
              <pre className="text-xs bg-gray-900 p-2 mb-3 rounded-md overflow-x-auto max-h-60">
                {analysisResult.fixed_message || "<No fix suggested or fix is empty>"}
              </pre>

              <button 
                onClick={() => onApplyFix(analysisResult.fixed_message)}
                disabled={!analysisResult.fixed_message}
                className="w-full px-4 py-2 font-semibold text-white bg-green-600 rounded-md hover:bg-green-700 disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors"
              >
                Apply Fix
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisPanel;