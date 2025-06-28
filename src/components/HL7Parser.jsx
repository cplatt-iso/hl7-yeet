import React, { useState, useEffect, useCallback, useRef } from 'react';
import { parseHl7, sendHl7, analyzeHl7 } from '../api/mllp';
import { rebuildHl7Message, stripCommentsAndBlankLines } from '../utils/hl7';
import ConnectionInputs from './ConnectionInputs';
import ParserOutput from './ParserOutput';
import SendButton from './SendButton';
import ResponseDisplay from './ResponseDisplay';
import Tooltip from './Tooltip';
import MessageTemplates from './MessageTemplates';
import AnalysisPanel from './AnalysisPanel';

const HL7Parser = () => {
    // All of our beautiful, sprawling state
    const [host, setHost] = useState('localhost');
    const [port, setPort] = useState('5001');
    const [hl7Message, setHl7Message] = useState('');
    const [segments, setSegments] = useState([]);
    const [error, setError] = useState('');
    const [showEmpty, setShowEmpty] = useState(true);
    const [isSending, setIsSending] = useState(false);
    const [response, setResponse] = useState(null);
    const [tooltipContent, setTooltipContent] = useState(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
    const [isProcessing, setIsProcessing] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);

    const scrollRef = useRef(0);
    const debounceTimerRef = useRef(null);

    // This effect handles initial parsing from the textarea
    useEffect(() => {
        if (!hl7Message.trim()) {
            setSegments([]);
            setError('');
            return;
        }
        const handler = setTimeout(() => {
            setIsProcessing(true);
            parseHl7(hl7Message)
                .then(data => { setSegments(data); setError(''); })
                .catch(err => { setSegments([]); setError(err.message); })
                .finally(() => { setIsProcessing(false); });
        }, 500);
        return () => clearTimeout(handler);
    }, [hl7Message]);

    // This effect handles restoring scroll position
    useEffect(() => {
        if (scrollRef.current > 0) {
            window.scrollTo(0, scrollRef.current);
            scrollRef.current = 0;
        }
    }, [segments]);

    const updateHl7MessageText = useCallback((newState) => {
        if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = setTimeout(() => {
            const newMessage = rebuildHl7Message(newState);
            setHl7Message(newMessage);
        }, 300);
    }, []);

    const handleFieldInteraction = (updateLogic) => {
        scrollRef.current = window.scrollY;
        setIsProcessing(true);
        setTimeout(() => {
            const newSegments = updateLogic(segments);
            setSegments(newSegments);
            updateHl7MessageText(newSegments);
            setIsProcessing(false);
        }, 0);
    };

    const handleFieldMove = useCallback((source, destination) => {
        handleFieldInteraction((currentSegments) => {
            return currentSegments.map((segment, segIdx) => {
                if (segIdx === source.segmentIndex || segIdx === destination.segmentIndex) {
                    const newSegment = { ...segment, fields: [...segment.fields] };
                    if (segIdx === source.segmentIndex) newSegment.fields[source.fieldIndex] = { ...newSegment.fields[source.fieldIndex], value: '' };
                    if (segIdx === destination.segmentIndex) {
                        const valueToMove = currentSegments[source.segmentIndex].fields[source.fieldIndex].value;
                        newSegment.fields[destination.fieldIndex] = { ...newSegment.fields[destination.fieldIndex], value: valueToMove };
                    }
                    return newSegment;
                }
                return segment;
            });
        });
    }, [segments, updateHl7MessageText]);

    const handleFieldUpdate = useCallback((segmentIndex, fieldIndex, newValue) => {
        handleFieldInteraction((currentSegments) => {
            return currentSegments.map((segment, segIdx) => {
                if (segIdx === segmentIndex) {
                    const newFields = segment.fields.map((field, fldIdx) => (fldIdx === fieldIndex) ? { ...field, value: newValue } : field);
                    return { ...segment, fields: newFields };
                }
                return segment;
            });
        });
    }, [segments, updateHl7MessageText]);

    const handleCopy = async () => {
        if (!hl7Message || isCopied) return;
        await navigator.clipboard.writeText(hl7Message);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };
    
    const handleStrip = () => {
        if (!hl7Message) return;
        const cleanedMessage = stripCommentsAndBlankLines(hl7Message);
        setHl7Message(cleanedMessage);
    };

    const handleClear = () => {
        setHl7Message('');
    };

    const handleSend = async () => {
        setIsSending(true);
        setResponse(null);
        try {
            const currentMessage = rebuildHl7Message(segments);
            const result = await sendHl7(host, port, currentMessage);
            setResponse({ success: true, ...result });
        } catch (error) {
            setResponse({ success: false, message: error.message });
        } finally {
            setIsSending(false);
        }
    };

    const handleMouseMove = (e) => {
        if(tooltipContent) setTooltipPos({ x: e.pageX, y: e.pageY });
    };
    
    const handleTemplateSelect = (message) => {
        setHl7Message(message);
    };

    const handleAnalyze = async () => {
        if (!hl7Message || isAnalyzing) return;
        setIsAnalyzing(true);
        setAnalysisResult(null);
        try {
            const result = await analyzeHl7(hl7Message);
            setAnalysisResult(result);
        } catch (error) {
            setAnalysisResult({ explanation: `**Error:** ${error.message}` });
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleApplyFix = (fixedMessage) => {
        setHl7Message(fixedMessage);
        setAnalysisResult(null);
    };

    return (
        <div onMouseMove={handleMouseMove}>
            <Tooltip content={tooltipContent} position={tooltipPos} />
            <div className="flex items-center gap-4 mb-6">
                <h1 className="text-4xl font-bold">HL7 Yeeter</h1>
                <span className="text-4xl">🚀</span>
            </div>

            <div className="flex flex-col md:flex-row gap-8">
                
                <div className="w-full md:w-1/4 lg:w-1/5">
                    <MessageTemplates onTemplateSelect={handleTemplateSelect} />
                </div>
                
                <div className={`w-full ${analysisResult || isAnalyzing ? 'md:w-2/4 lg:w-2/5' : 'md:w-3/4 lg:w-4/5'} transition-all duration-300`}>
                    <div className="flex flex-col gap-8">
                        <div id="input-container">
                            <ConnectionInputs 
                                host={host} 
                                setHost={setHost} 
                                port={port} 
                                setPort={setPort}
                                isSending={isSending}
                                handleSend={handleSend}
                            />
                            <div>
                                <div className="flex justify-between items-center mb-1">
                                    <label htmlFor="hl7-message" className="block text-sm font-medium text-gray-400">HL7 Message (Paste your crap here)</label>
                                    <div className="flex items-center gap-2">
                                        <button onClick={handleAnalyze} disabled={!hl7Message || isAnalyzing} title="Analyze with AI" className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors">
                                            <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 text-gray-300 ${isAnalyzing ? 'animate-pulse text-indigo-400' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                            </svg>
                                        </button>
                                        <button onClick={handleClear} disabled={!hl7Message} title="Clear message" className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors">
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                        </button>
                                        <button onClick={handleStrip} disabled={!hl7Message} title="Strip comments & blank lines" className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors">
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M5 11a1 1 0 011-1h12a1 1 0 110 2H6a1 1 0 01-1-1z" /><path strokeLinecap="round" strokeLinejoin="round" d="M19 11v10a2 2 0 01-2 2H7a2 2 0 01-2-2V11m14 0-4-4m-4 4L7 7" /></svg>
                                        </button>
                                        <button onClick={handleCopy} disabled={!hl7Message} title={isCopied ? "Copied!" : "Copy to clipboard"} className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                                            {isCopied ? (<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>) : (<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>)}
                                        </button>
                                    </div>
                                </div>
                                <textarea
                                    id="hl7-message"
                                    rows="10"
                                    className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2 font-mono"
                                    value={hl7Message}
                                    onChange={(e) => setHl7Message(e.target.value)}
                                />
                            </div>
                        </div>

                        <ParserOutput
                            isProcessing={isProcessing}
                            segments={segments}
                            error={error}
                            showEmpty={showEmpty}
                            setShowEmpty={setShowEmpty}
                            onFieldMove={handleFieldMove}
                            onFieldUpdate={handleFieldUpdate}
                            setTooltipContent={setTooltipContent}
                        />

                        <div>
                            <SendButton 
                                isSending={isSending} 
                                onClick={handleSend} 
                                className="w-full text-lg py-3 px-4"
                            />
                            {response && <ResponseDisplay response={response} />}
                        </div>
                    </div>
                </div>

                {(analysisResult || isAnalyzing) && (
                     <div className="w-full md:w-2/4 lg:w-2/5 transition-all duration-300">
                        <AnalysisPanel 
                            analysisResult={analysisResult}
                            onApplyFix={handleApplyFix}
                            onClear={() => setAnalysisResult(null)}
                            isLoading={isAnalyzing}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};

export default HL7Parser;