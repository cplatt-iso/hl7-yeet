// --- START OF FILE src/components/TableDetailView.jsx ---
import React, { useState, useEffect, useCallback } from 'react';
import { getTableDetailsApi, createDefinitionApi, updateDefinitionApi, deleteDefinitionApi } from '../api/admin';
import { toast } from 'react-hot-toast';

const TableDetailView = ({ tableId, onBack }) => {
    const [definitions, setDefinitions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingRowId, setEditingRowId] = useState(null);
    const [editData, setEditData] = useState({ value: '', description: '' });
    const [newData, setNewData] = useState({ value: '', description: '' });

    const fetchData = useCallback(() => {
        setLoading(true);
        getTableDetailsApi(tableId)
            .then(data => setDefinitions(data))
            .catch(err => toast.error(`Failed to load details for table ${tableId}: ${err.message}`))
            .finally(() => setLoading(false));
    }, [tableId]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleEditClick = (definition) => {
        setEditingRowId(definition.id);
        setEditData({ value: definition.value, description: definition.description });
    };

    const handleCancelEdit = () => {
        setEditingRowId(null);
        setEditData({ value: '', description: '' });
    };

    const handleSaveEdit = async () => {
        if (!editData.value || !editData.description) {
            toast.error("Value and Description cannot be empty.");
            return;
        }
        try {
            await updateDefinitionApi(editingRowId, editData);
            toast.success("Definition updated!");
            handleCancelEdit();
            fetchData();
        } catch (err) {
            toast.error(`Update failed: ${err.message}`);
        }
    };

    const handleDelete = async (defId) => {
        if (!window.confirm("Are you sure you want to delete this definition forever? This cannot be undone.")) return;
        try {
            await deleteDefinitionApi(defId);
            toast.success("Definition deleted.");
            fetchData();
        } catch (err) {
            toast.error(`Delete failed: ${err.message}`);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!newData.value || !newData.description) {
            toast.error("Value and Description cannot be empty for new definition.");
            return;
        }
        try {
            await createDefinitionApi({ ...newData, table_id: tableId });
            toast.success("New definition created!");
            setNewData({ value: '', description: '' });
            fetchData();
        } catch (err) {
            toast.error(`Create failed: ${err.message}`);
        }
    };

    if (loading) return <div className="p-6 text-center text-gray-400">Loading definitions for table {tableId}...</div>;

    return (
        <div className="p-6">
            <div className="flex items-center mb-4">
                <button onClick={onBack} className="mr-4 px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded">← Back</button>
                <h3 className="text-2xl font-bold text-white font-mono">{tableId}</h3>
            </div>
            
            <div className="bg-gray-900/50 rounded-lg">
                <table className="w-full text-left table-auto">
                    <thead>
                        <tr className="border-b border-gray-600">
                            <th className="p-3 text-sm font-semibold text-gray-300">Value</th>
                            <th className="p-3 text-sm font-semibold text-gray-300">Description</th>
                            <th className="p-3 text-sm font-semibold text-gray-300 w-48 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {definitions.map((def) => (
                            <tr key={def.id} className="border-b border-gray-700/50">
                                {editingRowId === def.id ? (
                                    <>
                                        <td className="p-2"><input type="text" value={editData.value} onChange={e => setEditData(d => ({...d, value: e.target.value}))} className="w-full bg-gray-700 p-1 rounded" /></td>
                                        <td className="p-2"><input type="text" value={editData.description} onChange={e => setEditData(d => ({...d, description: e.target.value}))} className="w-full bg-gray-700 p-1 rounded" /></td>
                                        <td className="p-2 text-right">
                                            <button onClick={handleSaveEdit} className="px-3 py-1 text-xs bg-green-600 hover:bg-green-500 rounded text-white mr-2">Save</button>
                                            <button onClick={handleCancelEdit} className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-500 rounded text-white">Cancel</button>
                                        </td>
                                    </>
                                ) : (
                                    <>
                                        <td className="p-3 font-mono text-indigo-300">{def.value}</td>
                                        <td className="p-3 text-gray-200">{def.description}</td>
                                        <td className="p-3 text-right">
                                            <button onClick={() => handleEditClick(def)} className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 rounded text-white mr-2">Edit</button>
                                            <button onClick={() => handleDelete(def.id)} className="px-3 py-1 text-xs bg-red-600 hover:bg-red-500 rounded text-white">Delete</button>
                                        </td>
                                    </>
                                )}
                            </tr>
                        ))}
                        {/* --- ADD NEW ROW --- */}
                        <tr className="bg-gray-800">
                           <td className="p-2"><input type="text" value={newData.value} onChange={e => setNewData(d => ({...d, value: e.target.value}))} placeholder="New Value" className="w-full bg-gray-700 p-1 rounded" /></td>
                           <td className="p-2"><input type="text" value={newData.description} onChange={e => setNewData(d => ({...d, description: e.target.value}))} placeholder="New Description" className="w-full bg-gray-700 p-1 rounded" /></td>
                           <td className="p-2 text-right">
                                <form onSubmit={handleCreate}>
                                    <button type="submit" className="w-full px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded text-white">Add New</button>
                                </form>
                           </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TableDetailView;
// --- END OF FILE src/components/TableDetailView.jsx ---