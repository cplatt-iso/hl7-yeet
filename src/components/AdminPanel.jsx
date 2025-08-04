// --- START OF FILE src/components/AdminPanel.jsx ---

import React, { useState } from 'react';
import VersionManagement from './VersionManagement';
import TerminologyManagement from './TerminologyManagement';
import UserManagement from './UserManagement';
import EndpointManager from './EndpointManager'; 
import ApiKeyManager from './ApiKeyManager'; 

const AdminPanel = () => {
    const [activeSubTab, setActiveSubTab] = useState('versions');    

    const SubTabButton = ({ name, label }) => (
        <button
            onClick={() => setActiveSubTab(name)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeSubTab === name 
                ? 'bg-indigo-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
        >
            {label}
        </button>
    );

    return (
        <div className="p-6 bg-gray-800 rounded-lg shadow-xl">
             <h2 className="text-2xl font-bold mb-4 text-white">Admin Panel</h2>
             <div className="flex items-center gap-4 mb-6 border-b border-gray-700 pb-4">
                <SubTabButton name="users" label="User Management" />
                <SubTabButton name="versions" label="HL7 Versions" />
                <SubTabButton name="terminology" label="HL7 Terminology" />
                <SubTabButton name="endpoints" label="Endpoints" />
                <SubTabButton name="apikeys" label="API Keys" /> {/* <-- ADD BUTTON */}
             </div>
             <div>
                {activeSubTab === 'users' && <UserManagement />}
                {activeSubTab === 'versions' && <VersionManagement />}
                {activeSubTab === 'terminology' && <TerminologyManagement />}
                {activeSubTab === 'endpoints' && <EndpointManager />}
                {activeSubTab === 'apikeys' && <ApiKeyManager />} {/* <-- ADD COMPONENT */}
             </div>
        </div>
    );
};

export default AdminPanel;

// --- END OF FILE src/components/AdminPanel.jsx ---