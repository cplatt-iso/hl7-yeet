// --- START OF FILE src/context/AuthContext.jsx ---

import React, { createContext, useState, useContext, useEffect } from 'react';
import { loginApi, registerApi, googleLoginApi } from '../api/auth' // Adjust the import path as needed

// 1. Create the context
const AuthContext = createContext(null);

// 2. Create the provider component
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null); // { username: 'testuser' }
    const [token, setToken] = useState(null); // The JWT token string
    const [loading, setLoading] = useState(true); // For initial load check

    // On initial app load, check localStorage for a saved session
    useEffect(() => {
        try {
            const storedToken = localStorage.getItem('authToken');
            const storedUser = localStorage.getItem('authUser');
            if (storedToken && storedUser) {
                setToken(storedToken);
                setUser(JSON.parse(storedUser));
            }
        } catch (error) {
            console.error("Failed to parse auth data from localStorage", error);
            // Clear corrupted data
            localStorage.removeItem('authToken');
            localStorage.removeItem('authUser');
        } finally {
            setLoading(false);
        }
    }, []);

    const login = async (username, password) => {
        const data = await loginApi(username, password);
        setToken(data.access_token);
        const userData = { username: data.username };
        setUser(userData);
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('authUser', JSON.stringify(userData));
    };

    const register = async (username, email, password) => {
        // Register API just returns a success message, doesn't log in
        await registerApi(username, email, password);
    };

    const logout = () => {
        setUser(null);
        setToken(null);
        localStorage.removeItem('authToken');
        localStorage.removeItem('authUser');
    };

    const googleLogin = async (googleToken) => {
        // This function calls our backend with the token from Google
        const data = await googleLoginApi(googleToken);
        setToken(data.access_token);
        const userData = { username: data.username };
        setUser(userData);
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('authUser', JSON.stringify(userData));
    };

    // The value provided to consuming components
    const value = {
        user,
        token,
        isAuthenticated: !!token, // Easy boolean check
        loading,
        login,
        register,
        logout,
        googleLogin,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

// 3. Create a custom hook for easy consumption
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};