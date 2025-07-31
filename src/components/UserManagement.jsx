// --- START OF FILE src/components/UserManagement.jsx ---

import React, { useState, useEffect } from 'react';

// --- NEW: Helper function to get auth headers ---
// This ensures every request is sent with the user's token.
const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');
    const headers = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchUsers = async () => {
        setIsLoading(true);
        setError(null); // Clear previous errors
        try {
            // --- CHANGE: Update the URL and add authentication headers ---
            const response = await fetch('/api/admin/users', { headers: getAuthHeaders() });
            
            if (response.status === 401) throw new Error('Unauthorized. Please log in as an admin.');
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.msg || 'Failed to fetch users');
            }
            const data = await response.json();
            setUsers(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleDelete = async (userId) => {
        if (window.confirm('Are you sure you want to delete this user?')) {
            try {
                // --- CHANGE: Update the URL and add authentication headers ---
                const response = await fetch(`/api/admin/users/${userId}`, { 
                    method: 'DELETE',
                    headers: getAuthHeaders() 
                });
                
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.msg || 'Failed to delete user');
                }
                fetchUsers(); // Refresh the list
            } catch (err) {
                setError(err.message);
            }
        }
    };

    const handleToggleAdmin = async (userId, isAdmin) => {
        const action = isAdmin ? 'revoke admin privileges from' : 'make';
        if (window.confirm(`Are you sure you want to ${action} this user an admin?`)) {
            try {
                 // --- CHANGE: Update the URL and add authentication headers ---
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ is_admin: !isAdmin })
                });
                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.msg || 'Failed to update user');
                }
                fetchUsers(); // Refresh the list
            } catch (err) {
                setError(err.message);
            }
        }
    };

    if (isLoading) {
        return <p className="text-white">Loading users...</p>;
    }

    if (error) {
        return <p className="text-red-500">Error: {error}</p>;
    }

    return (
        <div>
            <h3 className="text-xl font-semibold text-white mb-4">User Management</h3>
            <div className="overflow-x-auto">
                <table className="min-w-full bg-gray-900 rounded-lg">
                    {/* The table structure below remains the same */}
                    <thead>
                        <tr className="border-b border-gray-700">
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">ID</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Username</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Email</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Admin Status</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {users.map(user => (
                            <tr key={user.id}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{user.id}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{user.username}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{user.email}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${user.is_admin ? 'bg-green-900 text-green-300' : 'bg-gray-600 text-gray-300'}`}>
                                        {user.is_admin ? 'Admin' : 'User'}
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <button 
                                        onClick={() => handleToggleAdmin(user.id, user.is_admin)}
                                        className="text-indigo-400 hover:text-indigo-300 mr-4"
                                    >
                                        {user.is_admin ? 'Revoke Admin' : 'Make Admin'}
                                    </button>
                                    <button 
                                        onClick={() => handleDelete(user.id)}
                                        className="text-red-500 hover:text-red-400"
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserManagement;

// --- END OF FILE src/components/UserManagement.jsx ---