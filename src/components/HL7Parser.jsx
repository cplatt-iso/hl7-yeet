// --- START OF FILE src/components/HL7Parser.jsx ---
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { io } from 'socket.io-client';

// API Imports
import { parseHl7, sendHl7, analyzeHl7, getTotalUsage, getUsageByModel, getSupportedVersions, pingMllpApi } from '../api/mllp';
import { startListenerApi, stopListenerApi } from '../api/listener';
import { getTemplatesApi, saveTemplateApi } from '../api/templates';

// Util Imports
import { rebuildHl7Message, stripCommentsAndBlankLines } from '../utils/hl7';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';

// Component Imports
import ConnectionInputs from './ConnectionInputs';
import ParserOutput from './ParserOutput';
import Tooltip from './Tooltip';
import MessageTemplates from './MessageTemplates';
import AnalysisPanel from './AnalysisPanel';
import SettingsPanel from './SettingsPanel';
import DiffModal from './DiffModal';
import ListenerPanel from './ListenerPanel';
import ListenerOutput from './ListenerOutput';
import UserStatus from './UserStatus';
import SaveTemplateModal from './SaveTemplateModal';
import LogPanel from './LogPanel';
import AuthTooltip from './AuthTooltip'; // Assuming this import exists now
import TableDictionaryModal from './TableDictionaryModal';
import AdminPanel from './AdminPanel';
import Simulator from './Simulator';

const HL7Parser = () => {
    const { isAuthenticated, isAdmin } = useAuth(); // <-- MODIFIED: Get isAdmin from context
    const [activeTab, setActiveTab] = useState('sender');
    const [host, setHost] = useState('localhost');
    const [port, setPort] = useState('5001');
    const [hl7Message, setHl7Message] = useState('');
    const [segments, setSegments] = useState([]);
    const [error, setError] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [logs, setLogs] = useState([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const [showEmpty, setShowEmpty] = useState(true);
    const [tooltipContent, setTooltipContent] = useState(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
    const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
    const [originalMessageForDiff, setOriginalMessageForDiff] = useState('');
    const [newMessageForDiff, setNewMessageForDiff] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [totalTokenUsage, setTotalTokenUsage] = useState(0);
    const [showTooltips, setShowTooltips] = useState(true);
    const [selectedModel, setSelectedModel] = useState('gemini-1.5-flash');
    const [modelUsage, setModelUsage] = useState({});
    const [supportedVersions, setSupportedVersions] = useState([]);
    const [selectedHl7Version, setSelectedHl7Version] = useState('');
    const [listenerPort, setListenerPort] = useState('5002');
    const [isListening, setIsListening] = useState(false);
    const [listenerStatus, setListenerStatus] = useState('idle');
    const [receivedMessages, setReceivedMessages] = useState([]);
    const [userTemplates, setUserTemplates] = useState([]);
    const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
    const [saveTemplateError, setSaveTemplateError] = useState('');
    const [isLogCollapsed, setIsLogCollapsed] = useState(false);
    const [dictionaryModalState, setDictionaryModalState] = useState({
        isOpen: false,
        tableId: null,
        segmentIndex: null, // We need to know which field was clicked
        fieldIndex: null,
    });
    const socketRef = useRef(null);
    const scrollRef = useRef(null);
    const debounceTimerRef = useRef(null);

    const addLog = (type, message) => { const newLog = { id: Date.now() + Math.random(), timestamp: new Date().toLocaleTimeString(), type, message }; setLogs(prevLogs => [newLog, ...prevLogs]); };
    const handleClearLogs = () => { setLogs([]); };
    const handleToggleLogCollapse = () => { setIsLogCollapsed(prevState => !prevState); };
    const handleSend = async () => { if (!isAuthenticated) { addLog('error', 'You must be logged in to send messages.'); return; } setIsSending(true); try { const result = await sendHl7(host, port, rebuildHl7Message(segments)); addLog('success', `ACK Received from ${host}:${port}:\n\n${result.ack}`); } catch (e) { addLog('error', `Failed to connect to ${host}:${port}:\n\n${e.message}`); } finally { setIsSending(false); } };
    const fetchUserTemplates = useCallback(async () => { if (isAuthenticated) { try { const templates = await getTemplatesApi(); setUserTemplates(templates); } catch (error) { console.error("Failed to fetch user templates:", error); } } else { setUserTemplates([]); } }, [isAuthenticated]);
    useEffect(() => { if (!isAuthenticated) return; const socket = io(import.meta.env.VITE_API_URL || 'http://localhost:5001'); socketRef.current = socket; socket.on('connect', () => { }); socket.on('disconnect', () => { }); socket.on('listener_status', (data) => { setListenerStatus(data.status); setIsListening(data.status === 'listening'); }); socket.on('incoming_message', (data) => { setReceivedMessages(prev => [data, ...prev]); }); return () => { if (socket) socket.disconnect(); }; }, [isAuthenticated]);
    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const versions = await getSupportedVersions();
                const activeVersions = Array.isArray(versions) ? versions.filter(v => v.is_active) : [];
                setSupportedVersions(activeVersions);
                if (activeVersions.length > 0) {
                    const defaultVersion = activeVersions.find(v => v.is_default);
                    setSelectedHl7Version(defaultVersion ? defaultVersion.version : activeVersions[0].version);
                }
                if (isAuthenticated) {
                    const [total, byModel] = await Promise.all([getTotalUsage(), getUsageByModel()]);
                    setTotalTokenUsage(total);
                    setModelUsage(byModel);
                    fetchUserTemplates();
                }
            } catch (error) {
                toast.error("Failed to load initial app data. Some features may not work.");
            }
        };
        fetchInitialData();
    }, [isAuthenticated, fetchUserTemplates]);
    useEffect(() => { if (activeTab !== 'sender' || !hl7Message.trim()) { setSegments([]); setError(''); return; } const handler = setTimeout(() => { setIsProcessing(true); parseHl7(hl7Message, selectedHl7Version).then(data => { setSegments(data); setError(''); }).catch(err => { setSegments([]); setError(err.message); }).finally(() => { setIsProcessing(false); }); }, 500); return () => clearTimeout(handler); }, [hl7Message, selectedHl7Version, activeTab]);
    useEffect(() => { if (scrollRef.current > 0) { window.scrollTo(0, scrollRef.current); scrollRef.current = 0; } }, [segments]);
    const updateHl7MessageText = useCallback((newState) => { if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current); debounceTimerRef.current = setTimeout(() => { setHl7Message(rebuildHl7Message(newState)); }, 300); }, []);
    const handleFieldInteraction = (updateLogic) => { scrollRef.current = window.scrollY; setIsProcessing(true); setTimeout(() => { const newSegments = updateLogic(segments); setSegments(newSegments); updateHl7MessageText(newSegments); setIsProcessing(false); }, 0); };
    const handleStartListener = async () => { try { await startListenerApi(listenerPort); } catch (error) { console.error("API Error starting listener:", error); setListenerStatus('error'); } };
    const handleStopListener = async () => { try { await stopListenerApi(); } catch (error) { console.error("API Error stopping listener:", error); setListenerStatus('error'); } };
    const handleClearListener = () => { setReceivedMessages([]); };
    const handleLoadIntoParser = (messageToLoad) => { setHl7Message(messageToLoad); setActiveTab('sender'); };
    const handleAnalyze = async () => { if (!hl7Message || isAnalyzing || !isAuthenticated) return; setOriginalMessageForDiff(hl7Message); setIsAnalyzing(true); setAnalysisResult(null); try { const result = await analyzeHl7(hl7Message, selectedModel, selectedHl7Version); setAnalysisResult(result); if (result.usage?.total_tokens) { const tokens = result.usage.total_tokens; setTotalTokenUsage(pt => pt + tokens); setModelUsage(pu => ({ ...pu, [selectedModel]: (pu[selectedModel] || 0) + tokens })); } } catch (e) { setAnalysisResult({ explanation: `**Error:** ${e.message}` }); } finally { setIsAnalyzing(false); } };
    const handleFieldMove = useCallback((source, destination) => { handleFieldInteraction((cs) => cs.map((s, si) => (si === source.segmentIndex || si === destination.segmentIndex) ? { ...s, fields: s.fields.map((f, fi) => (si === source.segmentIndex && fi === source.fieldIndex) ? { ...f, value: '' } : (si === destination.segmentIndex && fi === destination.fieldIndex) ? { ...f, value: cs[source.segmentIndex].fields[source.fieldIndex].value } : f) } : s)); }, [segments, updateHl7MessageText]);
    const handleFieldUpdate = useCallback((segmentIndex, fieldIndex, newValue) => { handleFieldInteraction((cs) => cs.map((s, si) => (si === segmentIndex) ? { ...s, fields: s.fields.map((f, fi) => (fi === fieldIndex) ? { ...f, value: newValue } : f) } : s)); }, [segments, updateHl7MessageText]);
    const handleCopy = async () => { if (!hl7Message || isCopied) return; await navigator.clipboard.writeText(hl7Message); setIsCopied(true); setTimeout(() => setIsCopied(false), 2000); };
    const handleStrip = () => { if (!hl7Message) return; setHl7Message(stripCommentsAndBlankLines(hl7Message)); };
    const handleClear = () => { setHl7Message(''); };
    const handleTemplateSelect = (message) => { setHl7Message(message); setActiveTab('sender'); };
    const handleShowDiff = (fixedMessage) => { setNewMessageForDiff(fixedMessage); setIsDiffModalOpen(true); };
    const handleConfirmFix = () => { setHl7Message(newMessageForDiff); setIsDiffModalOpen(false); setAnalysisResult(null); };
    const handleMouseMove = (e) => { if (tooltipContent) setTooltipPos({ x: e.pageX, y: e.pageY }); };
    const handleSaveTemplate = async (templateName) => { setSaveTemplateError(''); if (!hl7Message.trim() || !templateName.trim()) { setSaveTemplateError("Template name and message content cannot be empty."); return; } try { await saveTemplateApi(templateName, hl7Message); setIsSaveModalOpen(false); await fetchUserTemplates(); } catch (error) { setSaveTemplateError(error.message || "Failed to save template."); } };
    const TabButton = ({ name, label }) => (<button onClick={() => setActiveTab(name)} className={`px-6 py-2 text-sm font-medium rounded-t-lg transition-colors border-b-2 ${activeTab === name ? 'border-indigo-500 text-white' : 'border-transparent text-gray-400 hover:border-gray-500 hover:text-gray-200'}`} > {label} </button>);
    const handleShowDictionary = (tableId, segmentIndex, fieldIndex) => {
        setDictionaryModalState({ isOpen: true, tableId, segmentIndex, fieldIndex });
    };

    const handleCloseDictionary = () => {
        setDictionaryModalState({ isOpen: false, tableId: null, segmentIndex: null, fieldIndex: null });
    };

    const handleSelectDictionaryValue = (value) => {
        handleFieldUpdate(dictionaryModalState.segmentIndex, dictionaryModalState.fieldIndex, value);
        handleCloseDictionary();
    }

    const handleSelectDestination = (destination) => {
        setHost(destination.hostname);
        setPort(destination.port);
    };

    const handlePing = async () => {
        if (!host || !port) {
            toast.error("Hostname and Port are required to run a connection test.");
            return;
        }

        const toastId = toast.loading(`Pinging ${host}:${port}...`);

        try {
            const result = await pingMllpApi(host, port);
            if (result.status === 'success') {
                const msaSegment = result.ack.split(/[\r\n]+/).find(seg => seg.startsWith('MSA'));
                const ackCode = msaSegment ? msaSegment.split('|')[1] : 'Unknown';
                toast.success(`Success! Received ACK (${ackCode})`, { id: toastId });
            } else {
                toast.error(result.message || 'Ping failed with an unknown error.', { id: toastId });
            }
        } catch (e) {
            toast.error(`Ping failed: ${e.message}`, { id: toastId });
        }
    };

    return (
        <div onMouseMove={handleMouseMove}>
            <TableDictionaryModal
                isOpen={dictionaryModalState.isOpen}
                tableId={dictionaryModalState.tableId}
                onClose={handleCloseDictionary}
                onSelectValue={handleSelectDictionaryValue}
            />

            <Tooltip content={tooltipContent} position={tooltipPos} />
            <DiffModal isOpen={isDiffModalOpen} onClose={() => setIsDiffModalOpen(false)} onConfirm={handleConfirmFix} originalText={originalMessageForDiff} newText={newMessageForDiff} />
            <SaveTemplateModal isOpen={isSaveModalOpen} onClose={() => { setIsSaveModalOpen(false); setSaveTemplateError(''); }} onSave={handleSaveTemplate} error={saveTemplateError} />

            <div className="flex items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-4">
                    <h1 className="text-4xl font-bold">HL7 Yeeter</h1><span className="text-4xl">🚀</span>
                </div>
                <UserStatus />
            </div>

            <div className="border-b border-gray-700">
                <TabButton name="sender" label="Sender & Parser" />
                {isAuthenticated && <TabButton name="listener" label="MLLP Listener" />}
                {isAuthenticated && <TabButton name="simulator" label="Simulator" />}
                {isAdmin && <TabButton name="admin" label="Admin" />}
            </div>

            <div className="pt-6">
                {activeTab === 'sender' && (
                    <div className="flex flex-col md:flex-row gap-8">
                        <div className="w-full md:w-1/4 lg:w-1/5 flex flex-col gap-8">
                            <MessageTemplates onTemplateSelect={handleTemplateSelect} userTemplates={userTemplates} onDeleteSuccess={fetchUserTemplates} />
                            <SettingsPanel showTooltips={showTooltips} setShowTooltips={setShowTooltips} selectedModel={selectedModel} setSelectedModel={setSelectedModel} supportedHl7Versions={supportedVersions} selectedHl7Version={selectedHl7Version} setSelectedHl7Version={setSelectedHl7Version} />
                        </div>
                        <div className={`w-full ${analysisResult || isAnalyzing ? 'md:w-2/4 lg:w-2/5' : 'md:w-3/4 lg:w-4/5'} transition-all duration-300`}>
                            <div className="flex flex-col gap-8">
                                <div className="sticky top-4 z-10 bg-gray-900 py-2 flex flex-col gap-4">
                                    <ConnectionInputs
                                        host={host}
                                        setHost={setHost}
                                        port={port}
                                        setPort={setPort}
                                        isSending={isSending}
                                        handleSend={handleSend}
                                        handlePing={handlePing}
                                    />
                                    <div className={`transition-all duration-300 ease-in-out ${isLogCollapsed ? 'h-14' : 'h-48'}`}>
                                        <LogPanel logs={logs} onClear={handleClearLogs} isCollapsed={isLogCollapsed} onToggleCollapse={handleToggleLogCollapse} />
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between items-center mb-1">
                                        <label htmlFor="hl7-message" className="block text-sm font-medium text-gray-400">HL7 Message</label>
                                        <div className="flex items-center gap-2">
                                            <AuthTooltip isAuthRequired={!isAuthenticated} message="Login to save as a template"><button onClick={() => setIsSaveModalOpen(true)} disabled={!isAuthenticated || !hl7Message} title="Save as Template" className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50"><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" /></svg></button></AuthTooltip>
                                            <AuthTooltip isAuthRequired={!isAuthenticated} message="Login to use AI Analyzer"><button onClick={handleAnalyze} disabled={!hl7Message || isAnalyzing || !isAuthenticated} className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50"><svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 text-gray-300 ${isAnalyzing ? 'animate-pulse text-indigo-400' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg></button></AuthTooltip>
                                            <button onClick={handleClear} disabled={!hl7Message} title="Clear message" className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50"><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
                                            <button onClick={handleStrip} disabled={!hl7Message} title="Strip comments & blank lines" className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50"><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-2.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg></button>
                                            <button onClick={handleCopy} disabled={!hl7Message} title={isCopied ? "Copied!" : "Copy to clipboard"} className="p-1.5 bg-gray-700 rounded-md hover:bg-gray-600 disabled:opacity-50">{isCopied ? <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg> : <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}</button>
                                        </div>
                                    </div>
                                    <textarea id="hl7-message" rows="10" className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2 font-mono" value={hl7Message} onChange={(e) => setHl7Message(e.target.value)} />
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
                                    showTooltips={showTooltips}
                                    onShowDictionary={handleShowDictionary}
                                />
                            </div>
                        </div>
                        {(analysisResult || isAnalyzing) && (
                            <div className="w-full md:w-2/4 lg:w-2/5 transition-all duration-300">
                                <AnalysisPanel analysisResult={analysisResult} onShowDiff={handleShowDiff} onClear={() => setAnalysisResult(null)} onRetry={handleAnalyze} isLoading={isAnalyzing} totalTokenUsage={totalTokenUsage} selectedModel={selectedModel} modelUsage={modelUsage} />
                            </div>
                        )}
                    </div>
                )}
                {activeTab === 'listener' && isAuthenticated && (
                    <div>
                        <ListenerPanel port={listenerPort} setPort={setListenerPort} isListening={isListening} status={listenerStatus} onStart={handleStartListener} onStop={handleStopListener} />
                        <ListenerOutput messages={receivedMessages} onClear={handleClearListener} onLoadIntoParser={handleLoadIntoParser} />
                    </div>
                )}
                {activeTab === 'simulator' && isAuthenticated && (
                    <Simulator />
                )}
                {activeTab === 'admin' && isAdmin && (
                    <AdminPanel />
                )}
            </div>
        </div>
    );
};

export default HL7Parser;
// --- END OF FILE src/components/HL7Parser.jsx ---