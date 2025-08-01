// --- CREATE NEW FILE: src/components/EndpointManager.jsx ---
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { getEndpointsApi, createEndpointApi, updateEndpointApi, deleteEndpointApi } from '../api/endpoints';

const EndpointManager = () => {
    const [endpoints, setEndpoints] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(null); // Holds the ID of the endpoint being edited
    const [editFormData, setEditFormData] = useState({});

    const initialFormState = {
        name: '',
        endpoint_type: 'MLLP',
        hostname: '',
        port: '',
        ae_title: '',
        aet_title: ''
    };
    const [newEndpoint, setNewEndpoint] = useState(initialFormState);

    const fetchEndpoints = async () => {
        setIsLoading(true);
        try {
            const data = await getEndpointsApi();
            setEndpoints(data);
        } catch (error) {
            toast.error(`Failed to fetch endpoints: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchEndpoints();
    }, []);

    const handleNewChange = (e) => {
        const { name, value } = e.target;
        setNewEndpoint(prev => ({ ...prev, [name]: value }));
    };

    const handleEditChange = (e) => {
        const { name, value } = e.target;
        setEditFormData(prev => ({ ...prev, [name]: value }));
    }

    const handleCreate = async (e) => {
        e.preventDefault();
        const toastId = toast.loading('Adding endpoint...');
        try {
            const created = await createEndpointApi(newEndpoint);
            setEndpoints(prev => [...prev, created]);
            setNewEndpoint(initialFormState);
            toast.success(`Endpoint "${created.name}" created.`, { id: toastId });
        } catch (error) {
            toast.error(`Failed to create endpoint: ${error.message}`, { id: toastId });
        }
    };
    
    const handleUpdate = async (id) => {
        const toastId = toast.loading('Updating endpoint...');
        try {
            const updated = await updateEndpointApi(id, editFormData);
            setEndpoints(prev => prev.map(ep => (ep.id === id ? updated : ep)));
            setIsEditing(null);
            toast.success(`Endpoint "${updated.name}" updated.`, { id: toastId });
        } catch (error) {
            toast.error(`Failed to update endpoint: ${error.message}`, { id: toastId });
        }
    };
    
    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to permanently delete this endpoint?")) return;
        const toastId = toast.loading('Deleting endpoint...');
        try {
            await deleteEndpointApi(id);
            setEndpoints(prev => prev.filter(ep => ep.id !== id));
            toast.success('Endpoint deleted.', { id: toastId });
        } catch (error) {
            toast.error(`Failed to delete endpoint: ${error.message}`, { id: toastId });
        }
    };

    const startEditing = (endpoint) => {
        setIsEditing(endpoint.id);
        setEditFormData(endpoint);
    };

    const renderRow = (endpoint) => {
        const isCurrentEditing = isEditing === endpoint.id;
        const data = isCurrentEditing ? editFormData : endpoint;
        const changeHandler = isCurrentEditing ? handleEditChange : () => {};

        return (
            <tr key={endpoint.id} className="bg-gray-800 hover:bg-gray-700/50">
                <td className="p-3"><input type="text" name="name" value={data.name} onChange={changeHandler} disabled={!isCurrentEditing} className="w-full bg-transparent disabled:bg-transparent p-1 rounded border border-transparent disabled:border-transparent focus:bg-gray-900 focus:border-indigo-500"/></td>
                <td className="p-3">
                    <select name="endpoint_type" value={data.endpoint_type} onChange={changeHandler} disabled={!isCurrentEditing} className="w-full bg-transparent disabled:bg-transparent p-1 rounded border border-transparent disabled:border-transparent focus:bg-gray-900 focus:border-indigo-500">
                        <option value="MLLP">MLLP</option>
                        <option value="DICOM_SCP">DICOM_SCP</option>
                    </select>
                </td>
                <td className="p-3"><input type="text" name="hostname" value={data.hostname} onChange={changeHandler} disabled={!isCurrentEditing} className="w-full bg-transparent disabled:bg-transparent p-1 rounded border border-transparent disabled:border-transparent focus:bg-gray-900 focus:border-indigo-500"/></td>
                <td className="p-3"><input type="number" name="port" value={data.port} onChange={changeHandler} disabled={!isCurrentEditing} className="w-20 bg-transparent disabled:bg-transparent p-1 rounded border border-transparent disabled:border-transparent focus:bg-gray-900 focus:border-indigo-500"/></td>
                <td className="p-3"><input type="text" name="ae_title" value={data.ae_title || ''} onChange={changeHandler} disabled={!isCurrentEditing || data.endpoint_type !== 'DICOM_SCP'} className="w-full bg-transparent disabled:bg-transparent p-1 rounded border border-transparent disabled:border-transparent focus:bg-gray-900 focus:border-indigo-500"/></td>
                <td className="p-3"><input type="text" name="aet_title" value={data.aet_title || ''} onChange={changeHandler} disabled={!isCurrentEditing || data.endpoint_type !== 'DICOM_SCP'} className="w-full bg-transparent disabled:bg-transparent p-1 rounded border border-transparent disabled:border-transparent focus:bg-gray-900 focus:border-indigo-500"/></td>
                <td className="p-3">
                    <div className="flex gap-2">
                        {isCurrentEditing ? (
                            <>
                                <button onClick={() => handleUpdate(endpoint.id)} className="text-green-400 hover:text-green-300">Save</button>
                                <button onClick={() => setIsEditing(null)} className="text-gray-400 hover:text-gray-300">Cancel</button>
                            </>
                        ) : (
                            <>
                                <button onClick={() => startEditing(endpoint)} className="text-indigo-400 hover:text-indigo-300">Edit</button>
                                <button onClick={() => handleDelete(endpoint.id)} className="text-red-400 hover:text-red-300">Delete</button>
                            </>
                        )}
                    </div>
                </td>
            </tr>
        )
    };

    return (
        <div>
            <h3 className="text-xl font-bold mb-4 text-gray-200">Manage Endpoints</h3>
            
            <div className="bg-gray-900 rounded-lg overflow-hidden mb-8">
                <table className="w-full text-left text-sm">
                    <thead className="bg-gray-950 text-xs text-gray-400 uppercase">
                        <tr>
                            <th className="p-3">Name</th>
                            <th className="p-3">Type</th>
                            <th className="p-3">Hostname</th>
                            <th className="p-3">Port</th>
                            <th className="p-3">Remote AE Title</th>
                            <th className="p-3">Our AE Title</th>
                            <th className="p-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                             <tr><td colSpan="7" className="p-4 text-center text-gray-500">Loading...</td></tr>
                        ) : endpoints.map(renderRow) }
                    </tbody>
                </table>
            </div>

            <h3 className="text-xl font-bold mb-4 text-gray-200">Add New Endpoint</h3>
            <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 p-4 bg-gray-900 rounded-lg">
                <input name="name" value={newEndpoint.name} onChange={handleNewChange} placeholder="Unique Name" className="bg-gray-800 p-2 rounded border border-gray-700 focus:border-indigo-500" required />
                <select name="endpoint_type" value={newEndpoint.endpoint_type} onChange={handleNewChange} className="bg-gray-800 p-2 rounded border border-gray-700 focus:border-indigo-500">
                    <option value="MLLP">MLLP</option>
                    <option value="DICOM_SCP">DICOM_SCP</option>
                </select>
                <input name="hostname" value={newEndpoint.hostname} onChange={handleNewChange} placeholder="Hostname or IP" className="bg-gray-800 p-2 rounded border border-gray-700 focus:border-indigo-500" required />
                <input name="port" type="number" value={newEndpoint.port} onChange={handleNewChange} placeholder="Port" className="bg-gray-800 p-2 rounded border border-gray-700 focus:border-indigo-500" required />
                {newEndpoint.endpoint_type === 'DICOM_SCP' && (
                    <>
                         <input name="ae_title" value={newEndpoint.ae_title} onChange={handleNewChange} placeholder="Remote AE Title" className="bg-gray-800 p-2 rounded border border-gray-700 focus:border-indigo-500" />
                         <input name="aet_title" value={newEndpoint.aet_title} onChange={handleNewChange} placeholder="Our AE Title (Optional)" className="bg-gray-800 p-2 rounded border border-gray-700 focus:border-indigo-500" />
                    </>
                )}
                 <button type="submit" className="md:col-start-1 lg:col-start-auto bg-indigo-600 hover:bg-indigo-700 rounded p-2 font-bold">Add Endpoint</button>
            </form>
        </div>
    );
};

export default EndpointManager;
// --- END OF FILE: src/components/EndpointManager.jsx ---