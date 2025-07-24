// --- START OF FILE src/components/TableDictionaryModal.jsx ---
import React, { useState, useEffect } from 'react';
import { getTableDefinitionsApi } from '../api/mllp';

const TableDictionaryModal = ({ isOpen, onClose, tableId, onSelectValue }) => {
    const [definitions, setDefinitions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        if (isOpen && tableId) {
            setLoading(true);
            setError('');
            setDefinitions([]);
            getTableDefinitionsApi(tableId)
                .then(data => {
                    setDefinitions(data);
                })
                .catch(err => {
                    setError(err.message || `Failed to load definitions for table ${tableId}.`);
                })
                .finally(() => {
                    setLoading(false);
                });
        }
    }, [isOpen, tableId]);

    if (!isOpen) return null;

    const filteredDefinitions = definitions.filter(def =>
        def.value.toLowerCase().includes(searchTerm.toLowerCase()) ||
        def.description.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
                <div className="p-4 border-b border-gray-700">
                    <h2 className="text-xl font-bold text-white">HL7 Table: {tableId}</h2>
                    <input
                        type="text"
                        placeholder="Search values or descriptions..."
                        className="w-full p-2 mt-2 bg-gray-900 border border-gray-600 rounded-md text-white"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <div className="overflow-y-auto p-4">
                    {loading && <p className="text-gray-400">Loading...</p>}
                    {error && <p className="text-red-400">{error}</p>}
                    {!loading && !error && (
                        <table className="w-full text-left table-auto">
                            <thead>
                                <tr className="border-b border-gray-600">
                                    <th className="p-2 text-sm font-semibold text-gray-300">Value</th>
                                    <th className="p-2 text-sm font-semibold text-gray-300">Description</th>
                                    <th className="p-2"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredDefinitions.map((def, index) => (
                                    <tr key={index} className="border-b border-gray-700/50 hover:bg-gray-700/40">
                                        <td className="p-2 font-mono text-indigo-300">{def.value}</td>
                                        <td className="p-2 text-gray-200">{def.description}</td>
                                        <td className="p-2 text-right">
                                            <button
                                                onClick={() => onSelectValue(def.value)}
                                                className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded text-white"
                                            >
                                                Use
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
                
                <div className="p-4 border-t border-gray-700 text-right">
                    <button onClick={onClose} className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-white">Close</button>
                </div>
            </div>
        </div>
    );
};

export default TableDictionaryModal;
// --- END OF FILE src/components/TableDictionaryModal.jsx ---