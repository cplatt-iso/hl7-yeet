// --- START OF FILE src/components/ApiKeysPage.jsx ---
import React from 'react';
import { Link } from 'react-router-dom';
import ApiKeyManager from './ApiKeyManager';
import UserStatus from './UserStatus';

const ApiKeysPage = () => {
    return (
        <div className="max-w-5xl mx-auto">
            <div className="flex items-center justify-between gap-4 mb-6">
                <div className="flex items-center gap-3">
                    <Link to="/" className="text-sm text-indigo-400 hover:text-indigo-200">
                        &larr; Back to Yeeter
                    </Link>
                    <h1 className="text-3xl font-bold text-gray-100">API Keys</h1>
                </div>
                <UserStatus />
            </div>
            <div className="bg-gray-900/70 border border-gray-800 rounded-lg p-6">
                <p className="text-sm text-gray-400 mb-4">
                    Generate API keys for CLI automation or integrations. Newly created keys are shown once; copy and store them securely.
                </p>
                <ApiKeyManager />
            </div>
        </div>
    );
};

export default ApiKeysPage;
// --- END OF FILE src/components/ApiKeysPage.jsx ---
