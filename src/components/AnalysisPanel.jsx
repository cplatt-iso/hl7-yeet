import React from 'react';
import ReactMarkdown from 'react-markdown';
import AnalysisLoader from './AnalysisLoader';

const AnalysisPanel = ({ analysisResult, onShowDiff, onClear, onRetry, isLoading, totalTokenUsage, selectedModel, modelUsage }) => {
  if (!analysisResult && !isLoading) {
    return null;
  }

  const shouldShowFixSection = analysisResult?.fixed_message !== undefined;

  const handleApplyClick = () => {
    if (analysisResult?.fixed_message) {
      onShowDiff(analysisResult.fixed_message);
    }
  };

  const currentModelTotal = modelUsage[selectedModel] || 0;

  return (
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
                {analysisResult.fixed_message || "<No fix suggested or fix is empty>"}
              </pre>

              <div className="grid grid-cols-3 gap-2 mt-4">
                  <button 
                    onClick={handleApplyClick}
                    disabled={!analysisResult.fixed_message}
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

            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisPanel;