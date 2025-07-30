// --- START OF FILE src/components/TerminologyBrowser.jsx ---
import React, { useState } from 'react';
import TableListView from './TableListView';
import TableDetailView from './TableDetailView';

const TerminologyBrowser = ({ onClose }) => {
    const [view, setView] = useState('list'); // 'list' or 'detail'
    const [selectedTableId, setSelectedTableId] = useState(null);

    const handleSelectTable = (tableId) => {
        setSelectedTableId(tableId);
        setView('detail');
    };

    const handleBackToList = () => {
        setSelectedTableId(null);
        setView('list');
    };

    return (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl h-[90vh] flex flex-col" onClick={e => e.stopPropagation()}>
                <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                    <h2 className="text-xl font-bold text-white">Terminology Browser</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">×</button>
                </div>
                <div className="flex-grow overflow-y-auto">
                    {view === 'list' && <TableListView onSelectTable={handleSelectTable} />}
                    {view === 'detail' && <TableDetailView tableId={selectedTableId} onBack={handleBackToList} />}
                </div>
            </div>
        </div>
    );
};

export default TerminologyBrowser;
// --- END OF FILE src/components/TerminologyBrowser.jsx ---