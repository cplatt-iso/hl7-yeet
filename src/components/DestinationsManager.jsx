import React, { useState, useEffect } from 'react';
import { getDestinations, addDestination, deleteDestination } from '../api/destinations';
import { toast } from 'react-hot-toast';
import { PlusCircleIcon, TrashIcon, ServerIcon } from '@heroicons/react/24/outline';

const DestinationsManager = ({ onSelectDestination, show, onClose }) => {
    const [destinations, setDestinations] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    // Use 'hostname' in the state to be perfectly consistent with the backend model and API payload.
    const [newDestination, setNewDestination] = useState({ name: '', hostname: '', port: '' });

    const fetchDestinations = async () => {
        setIsLoading(true);
        try {
            const data = await getDestinations();
            setDestinations(data);
        } catch (error) {
            toast.error(`Failed to fetch destinations: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch destinations only when the modal is shown.
    useEffect(() => {
        if (show) {
            fetchDestinations();
        }
    }, [show]);

    const handleAddDestination = async (e) => {
        e.preventDefault();
        if (!newDestination.name || !newDestination.hostname || !newDestination.port) {
            toast.error('Please fill out all fields for the new destination.');
            return;
        }
        try {
            // The addDestination API call now correctly receives `hostname`.
            const added = await addDestination(newDestination.name, newDestination.hostname, newDestination.port);
            setDestinations([...destinations, added]);
            setNewDestination({ name: '', hostname: '', port: '' }); // Clear the form
            toast.success(`Destination "${added.name}" added!`);
        } catch (error) {
            toast.error(`Failed to add destination: ${error.message}`);
        }
    };

    const handleDeleteDestination = async (id) => {
        if (window.confirm('Are you sure you want to delete this destination?')) {
            try {
                await deleteDestination(id);
                setDestinations(destinations.filter(d => d.id !== id));
                toast.success('Destination deleted.');
            } catch (error) {
                toast.error(`Failed to delete destination: ${error.message}`);
            }
        }
    };

    const handleSelect = (destination) => {
        onSelectDestination(destination);
        onClose();
    };

    // Don't render anything if the modal is not supposed to be shown.
    if (!show) {
        return null;
    }

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-2xl" onClick={e => e.stopPropagation()}>
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-white">Manage Destinations</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-gray-700">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Add new destination form */}
                <form onSubmit={handleAddDestination} className="mb-6 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                    <h3 className="text-lg font-semibold mb-3 text-gray-200">Add New Destination</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <input
                            type="text"
                            placeholder="Name (e.g., 'RIS Dev')"
                            value={newDestination.name}
                            onChange={(e) => setNewDestination({ ...newDestination, name: e.target.value })}
                            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white"
                        />
                        <input
                            type="text"
                            placeholder="Hostname or IP"
                            value={newDestination.hostname}
                            onChange={(e) => setNewDestination({ ...newDestination, hostname: e.target.value })}
                            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white"
                        />
                        <input
                            type="number"
                            placeholder="Port"
                            value={newDestination.port}
                            onChange={(e) => setNewDestination({ ...newDestination, port: e.target.value })}
                            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-white"
                        />
                    </div>
                    <button type="submit" className="mt-4 w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center transition-colors">
                        <PlusCircleIcon className="h-5 w-5 mr-2" /> Add
                    </button>
                </form>

                {/* List of saved destinations */}
                <h3 className="text-lg font-semibold mb-3 text-gray-200">Saved Destinations</h3>
                <div className="space-y-3 max-h-80 overflow-y-auto p-1">
                    {isLoading ? (
                        <p className="text-center text-gray-400 p-4">Loading destinations...</p>
                    ) : destinations.length > 0 ? (
                        destinations.map(dest => (
                            <div key={dest.id} className="bg-gray-700/80 p-3 rounded-lg flex items-center justify-between hover:bg-gray-700/100 transition-colors">
                                <div className="flex items-center">
                                    <ServerIcon className="h-6 w-6 mr-4 text-gray-400 flex-shrink-0" />
                                    <div>
                                        <p className="font-semibold text-white">{dest.name}</p>
                                        <p className="text-sm text-gray-300 font-mono">{dest.hostname}:{dest.port}</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <button onClick={() => handleSelect(dest)} className="bg-green-600 hover:bg-green-700 text-white font-bold py-1 px-3 rounded-md text-sm transition-colors">
                                        Use
                                    </button>
                                    <button onClick={() => handleDeleteDestination(dest.id)} className="bg-red-600 hover:bg-red-700 text-white p-2 rounded-md transition-colors" title="Delete">
                                        <TrashIcon className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                        ))
                    ) : (
                        <p className="text-center text-gray-500 p-4 border-2 border-dashed border-gray-700 rounded-lg">No saved destinations found.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DestinationsManager;