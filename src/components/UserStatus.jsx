// --- START OF FILE src/components/UserStatus.jsx ---

import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';

const UserStatus = () => {
    const { user, logout } = useAuth();

    if (!user) {
        return (
            <div className="flex items-center gap-4">
                <Link to="/login" className="px-4 py-2 text-sm font-medium text-white bg-gray-700 rounded-md hover:bg-gray-600">
                    Login
                </Link>
                <Link to="/register" className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700">
                    Register
                </Link>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-4">
            <span className="text-gray-300">
                Welcome, <span className="font-bold text-indigo-400">{user.username}</span>
            </span>
            <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
            >
                Logout
            </button>
        </div>
    );
};

export default UserStatus;