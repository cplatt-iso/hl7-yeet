// --- CREATE NEW FILE: src/components/ApiKeyManager.jsx ---
import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { getApiKeysApi, createApiKeyApi, deleteApiKeyApi } from '../api/admin';
import { TrashIcon, PlusIcon, ClipboardIcon, CheckIcon, EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';

const ApiKeyManager = () => {
    const [keys, setKeys] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [newKeyName, setNewKeyName] = useState('');
    const [newlyGeneratedKey, setNewlyGeneratedKey] = useState(null);
    const [isCopied, setIsCopied] = useState(false);
    const [isRevealed, setIsRevealed] = useState(false);

    const fetchKeys = async () => {
        try {
            const data = await getApiKeysApi();
            setKeys(data);
        } catch (error) {
            toast.error(`Failed to fetch API keys: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchKeys();
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        if (!newKeyName.trim()) {
            toast.error("Please provide a name for the key.");
            return;
        }
        const toastId = toast.loading("Creating key...");
        try {
            const result = await createApiKeyApi(newKeyName);
            setNewlyGeneratedKey(result);
            setNewKeyName('');
            fetchKeys();
            toast.success("API Key created!", { id: toastId });
        } catch (error) {
            toast.error(`Failed to create key: ${error.message}`, { id: toastId });
        }
    };
    
    const handleDelete = async (keyId, keyName) => {
        if (!window.confirm(`Are you sure you want to delete the key "${keyName}"? This is irreversible.`)) return;
        
        const toastId = toast.loading("Deleting key...");
        try {
            await deleteApiKeyApi(keyId);
            fetchKeys(); // Refresh the list
            toast.success("Key deleted.", { id: toastId });
        } catch (error) {
            toast.error(`Failed to delete key: ${error.message}`, { id: toastId });
        }
    };
    
    const handleCopy = () => {
        navigator.clipboard.writeText(newlyGeneratedKey.raw_key);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    return (
        <div>
            <h3 className="text-xl font-bold mb-4 text-gray-200">Manage API Keys</h3>

            {newlyGeneratedKey && (
                <div className="p-4 bg-green-900/50 border border-green-700 rounded-lg mb-6">
                    <h4 className="font-bold text-green-300">New Key Generated: {newlyGeneratedKey.name}</h4>
                    <p className="text-sm text-gray-400 mb-2">Please copy this key and store it securely. You will not be able to see it again.</p>
                    <div className="flex items-center gap-2 bg-gray-900 p-2 rounded">
                        <input 
                            type={isRevealed ? "text" : "password"}
                            readOnly 
                            value={newlyGeneratedKey.raw_key} 
                            className="flex-grow bg-transparent font-mono text-sm"
                        />
                        <button onClick={() => setIsRevealed(!isRevealed)} className="p-1.5 text-gray-400 hover:text-white">
                            {isRevealed ? <EyeSlashIcon className="h-5 w-5"/> : <EyeIcon className="h-5 w-5"/>}
                        </button>
                        <button onClick={handleCopy} className="p-1.5 text-gray-400 hover:text-white">
                            {isCopied ? <CheckIcon className="h-5 w-5 text-green-400"/> : <ClipboardIcon className="h-5 w-5"/>}
                        </button>
                    </div>
                     <button onClick={() => setNewlyGeneratedKey(null)} className="mt-4 text-xs text-gray-500 hover:underline">Close</button>
                </div>
            )}
            
            <form onSubmit={handleCreate} className="flex gap-2 mb-4">
                <input 
                    type="text" 
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    placeholder="Enter a descriptive name for the new key"
                    className="flex-grow bg-gray-900 p-2 rounded border border-gray-700"
                />
                <button type="submit" className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded font-bold">
                    <PlusIcon className="h-5 w-5"/> Create Key
                </button>
            </form>
            
            <div className="bg-gray-900 rounded-lg overflow-hidden">
                <table className="w-full text-left text-sm">
                    <thead className="bg-gray-950 text-xs text-gray-400 uppercase">
                        <tr>
                            <th className="p-3">Name</th>
                            <th className="p-3">Key Prefix</th>
                            <th className="p-3">Created</th>
                            <th className="p-3">Last Used</th>
                            <th className="p-3">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {isLoading ? (
                             <tr><td colSpan="5" className="p-4 text-center">Loading...</td></tr>
                        ) : keys.length === 0 ? (
                             <tr><td colSpan="5" className="p-4 text-center text-gray-500">No API keys found.</td></tr>
                        ) : (
                            keys.map(key => (
                                <tr key={key.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                                    <td className="p-3 font-semibold">{key.name}</td>
                                    <td className="p-3 font-mono">{key.key_prefix}...</td>
                                    <td className="p-3">{new Date(key.created_at).toLocaleString()}</td>
                                    <td className="p-3">{key.last_used ? new Date(key.last_used).toLocaleString() : 'Never'}</td>
                                    <td className="p-3">
                                        <button onClick={() => handleDelete(key.id, key.name)} className="text-red-400 hover:text-red-300">
                                            <TrashIcon className="h-5 w-5"/>
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ApiKeyManager;