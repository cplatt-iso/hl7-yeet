// --- START OF FILE src/components/UserStatus.jsx ---

import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useLocation } from 'react-router-dom';

const UserStatus = () => {
    // Get everything we need from the context
    const { isAuthenticated, user, logout } = useAuth();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const menuRef = useRef(null);
    const location = useLocation();

    useEffect(() => {
        setIsMenuOpen(false);
    }, [location.pathname]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleMenu = () => setIsMenuOpen((prev) => !prev);

    const handleLogout = () => {
        setIsMenuOpen(false);
        logout();
    };

    if (!isAuthenticated || !user) {
        // This is the state when the user is logged out
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

    // This is the state when the user is logged in
    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={toggleMenu}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gray-800 border border-gray-700 rounded-md hover:bg-gray-700"
            >
                <span className="text-gray-200">{user.username}</span>
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className={`h-4 w-4 text-gray-400 transition-transform ${isMenuOpen ? 'rotate-180' : ''}`}
                    viewBox="0 0 20 20"
                    fill="currentColor"
                >
                    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.25a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z" clipRule="evenodd" />
                </svg>
            </button>
            {isMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 rounded-md border border-gray-700 bg-gray-900 shadow-lg z-20">
                    <Link
                        to="/"
                        className="block px-4 py-2 text-sm text-gray-200 hover:bg-gray-800"
                        onClick={() => setIsMenuOpen(false)}
                    >
                        Dashboard
                    </Link>
                    <Link
                        to="/metrics"
                        className="block px-4 py-2 text-sm text-gray-200 hover:bg-gray-800"
                        onClick={() => setIsMenuOpen(false)}
                    >
                        Metrics
                    </Link>
                    <Link
                        to="/api-keys"
                        className="block px-4 py-2 text-sm text-gray-200 hover:bg-gray-800"
                        onClick={() => setIsMenuOpen(false)}
                    >
                        API Keys
                    </Link>
                    <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-sm text-red-300 hover:bg-gray-800"
                    >
                        Logout
                    </button>
                </div>
            )}
        </div>
    );
};

export default UserStatus;
// --- END OF FILE src/components/UserStatus.jsx ---