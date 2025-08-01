// --- START OF FILE src/components/VersionManagement.jsx ---

import React, { useState, useEffect, useCallback } from 'react';

import { getHl7VersionsApi, toggleVersionStatusApi, uploadVersionApi, setDefaultVersionApi } from '../api/admin';
import { toast } from 'react-hot-toast';
import YeetLoader from './YeetLoader';
import InfoCallout from './InfoCallout';

const VersionManagement = () => {
    const [versions, setVersions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);

    // Form state for new version upload
    const [file, setFile] = useState(null);
    const [versionString, setVersionString] = useState('');
    const [description, setDescription] = useState('');

    const fetchVersions = useCallback(async () => {
        try {
            setIsLoading(true);
            const data = await getHl7VersionsApi();
            setVersions(data);
        } catch (error) {
            toast.error(`Failed to fetch versions: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchVersions();
    }, [fetchVersions]);

    const handleToggle = async (versionId) => {
        // Optimistically update the UI
        setVersions(prev =>
            prev.map(v => (v.id === versionId ? { ...v, is_active: !v.is_active } : v))
        );

        try {
            await toggleVersionStatusApi(versionId);
            toast.success('Version status updated!');
            // If we are deactivating the default version, we need to refresh
            const deactivatedVersion = versions.find(v => v.id === versionId);
            if (deactivatedVersion?.is_default) {
                fetchVersions();
            }
        } catch (error) {
            toast.error(`Failed to update status: ${error.message}`);
            // Revert optimistic update on failure
            fetchVersions(); 
        }
    };

    const handleSetDefault = async (versionId) => {
        try {
            await setDefaultVersionApi(versionId);
            toast.success('Version set as default!');
            fetchVersions(); // Refresh to show the new default status
        } catch (error) {
            toast.error(`Failed to set default: ${error.message}`);
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!file || !versionString) {
            toast.error('Version string and a zip file are required.');
            return;
        }

        setIsUploading(true);
        const toastId = toast.loading(`Uploading version ${versionString}...`);

        try {
            const result = await uploadVersionApi(file, versionString, description);
            toast.success(result.message, { id: toastId });
            // Reset form and refresh list
            setFile(null);
            setVersionString('');
            setDescription('');
            if (document.getElementById('file-upload-form')) {
                document.getElementById('file-upload-form').reset();
            }
            fetchVersions();
        } catch (error) {
            toast.error(`Upload failed: ${error.message}`, { id: toastId });
        } finally {
            setIsUploading(false);
        }
    };

    if (isLoading) {
        return <YeetLoader />;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Left side: List of existing versions */}
            <div>
                <h3 className="text-xl font-semibold mb-3 text-gray-200">Processed HL7 Versions</h3>
                <div className="space-y-2 max-h-[450px] overflow-y-auto pr-2">
                    {versions.map(v => (
                        <div key={v.id} className="p-3 bg-gray-900/50 rounded-lg flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-2">
                                    <p className="font-bold text-white">{v.version}</p>
                                    {v.is_default && (
                                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-yellow-500/50 text-yellow-200" title="This is the default version for the parser.">
                                            Default
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-gray-400">{v.description || 'No description'}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                    Processed by {v.processed_by} on {new Date(v.processed_at).toLocaleDateString()}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${v.is_active ? 'bg-green-600/50 text-green-300' : 'bg-red-600/50 text-red-300'}`}>
                                    {v.is_active ? 'Active' : 'Inactive'}
                                </span>
                                <button
                                    onClick={() => handleToggle(v.id)}
                                    className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded-md"
                                >
                                    Toggle
                                </button>
                                <button
                                    onClick={() => handleSetDefault(v.id)}
                                    disabled={v.is_default || !v.is_active}
                                    title={!v.is_active ? "Cannot set an inactive version as default" : "Set as default version"}
                                    className="px-3 py-1 text-sm bg-indigo-700 hover:bg-indigo-600 rounded-md disabled:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Set Default
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right side: Upload new version form */}
            <div>
                 <h3 className="text-xl font-semibold mb-3 text-gray-200">Upload New Version</h3>
                 <InfoCallout>
                    <p className="font-semibold mb-2">Expected File Format:</p>
                    <p>
                        Please upload the official HL7 V2.x Messaging Standard as a ZIP file. You can find these on the official HL7 website:
                        <a href="https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline ml-1">
                            HL7 V2 Product Page
                        </a>.
                    </p>
                    <p className="mt-2">
                        From the list, select a version and download the "XML Schema" zip file. The system expects this zip file to contain the chapter-specific XSD files (e.g., `datatypes.xsd`, `segments.xsd`, etc.).
                    </p>
                </InfoCallout>
                 <form id="file-upload-form" onSubmit={handleUpload} className="p-4 bg-gray-900/50 rounded-lg space-y-4">
                    <div>
                        <label htmlFor="version-string" className="block text-sm font-medium text-gray-300">Version (e.g., 2.5.1)</label>
                        <input
                            type="text"
                            id="version-string"
                            value={versionString}
                            onChange={e => setVersionString(e.target.value)}
                            required
                            className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2"
                        />
                    </div>
                     <div>
                        <label htmlFor="description" className="block text-sm font-medium text-gray-300">Description</label>
                        <input
                            type="text"
                            id="description"
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            placeholder="Optional short description"
                            className="mt-1 block w-full bg-gray-800 border-gray-700 rounded-md shadow-sm p-2"
                        />
                    </div>
                    <div>
                        <label htmlFor="file-upload" className="block text-sm font-medium text-gray-300">HL7 Messaging ZIP File</label>
                         <input
                            type="file"
                            id="file-upload"
                            accept=".zip"
                            onChange={e => setFile(e.target.files[0])}
                            required
                            className="mt-1 block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={isUploading}
                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                         {isUploading ? 'Uploading...' : 'Upload and Process'}
                    </button>
                 </form>
            </div>
        </div>
    );
};

export default VersionManagement;

// --- END OF FILE src/components/VersionManagement.jsx ---