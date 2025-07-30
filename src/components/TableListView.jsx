// --- START OF FILE src/components/TableListView.jsx ---
import React, { useState, useEffect } from 'react';
import { getTablesListApi } from '../api/admin';
import { toast } from 'react-hot-toast';

const TableListView = ({ onSelectTable }) => {
    const [tables, setTables] = useState([]);
    const [filteredTables, setFilteredTables] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        getTablesListApi()
            .then(data => {
                setTables(data);
                setFilteredTables(data);
            })
            .catch(err => toast.error(`Failed to load tables: ${err.message}`))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (!searchTerm) {
            setFilteredTables(tables);
        } else {
            setFilteredTables(tables.filter(t => t.includes(searchTerm)));
        }
    }, [searchTerm, tables]);

    if (loading) return <div className="p-6 text-center text-gray-400">Loading tables...</div>;

    return (
        <div className="p-6">
            <input
                type="text"
                placeholder="Filter by table ID..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full p-2 mb-4 bg-gray-900 border border-gray-600 rounded-md text-white"
            />
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                {filteredTables.map(tableId => (
                    <button
                        key={tableId}
                        onClick={() => onSelectTable(tableId)}
                        className="p-3 bg-indigo-800 hover:bg-indigo-700 rounded-md text-white font-mono text-center transition-colors"
                    >
                        {tableId}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default TableListView;
// --- END OF FILE src/components/TableListView.jsx ---