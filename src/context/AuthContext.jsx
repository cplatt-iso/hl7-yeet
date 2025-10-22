import React, { createContext, useState, useContext, useEffect } from 'react';
import { loginApi, registerApi, googleLoginApi } from '../api/auth';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isAdmin, setIsAdmin] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check for existing token on app load
        const token = localStorage.getItem('authToken');
        const storedUser = localStorage.getItem('userData');
        
        if (token && storedUser) {
            // For JWT tokens, we can decode to check if valid
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                const currentTime = Date.now() / 1000;
                
                if (payload.exp > currentTime) {
                    // Token is still valid, restore user data
                    const userData = JSON.parse(storedUser);
                    setUser(userData);
                    setIsAuthenticated(true);
                    setIsAdmin(userData.is_admin || false);
                } else {
                    // Token expired, clear it
                    localStorage.removeItem('authToken');
                    localStorage.removeItem('userData');
                }
            } catch {
                // Invalid token or data format, clear it
                localStorage.removeItem('authToken');
                localStorage.removeItem('userData');
            }
        }
        setLoading(false);
    }, []);

    const login = async (credentials) => {
        // loginApi expects (username, password)
        const response = await loginApi(credentials.username || credentials.email, credentials.password);
        const { access_token, username, is_admin } = response;
        
        localStorage.setItem('authToken', access_token);
        
        // Use is_admin from the API response
        const userData = {
            username: username,
            is_admin: is_admin || false
        };
        
        // Store user data for persistence across page reloads
        localStorage.setItem('userData', JSON.stringify(userData));
        
        setUser(userData);
        setIsAuthenticated(true);
        setIsAdmin(userData.is_admin);
        
        return { data: { token: access_token, user: userData } };
    };

    const register = async (userData) => {
        // registerApi expects (username, email, password)
        const response = await registerApi(userData.username, userData.email, userData.password);
        const { access_token, username, is_admin } = response;
        
        localStorage.setItem('authToken', access_token);
        
        // Use is_admin from the API response
        const user = {
            username: username,
            is_admin: is_admin || false
        };
        
        // Store user data for persistence across page reloads
        localStorage.setItem('userData', JSON.stringify(user));
        
        setUser(user);
        setIsAuthenticated(true);
        setIsAdmin(user.is_admin);
        
        return { data: { token: access_token, user } };
    };

    const googleLogin = async (googleUser) => {
        const response = await googleLoginApi(googleUser.token || googleUser);
        const { access_token, username, is_admin } = response;
        
        localStorage.setItem('authToken', access_token);
        
        // Use is_admin from the API response
        const userData = {
            username: username,
            is_admin: is_admin || false
        };
        
        // Store user data for persistence across page reloads
        localStorage.setItem('userData', JSON.stringify(userData));
        
        setUser(userData);
        setIsAuthenticated(true);
        setIsAdmin(userData.is_admin);
        
        return { data: { token: access_token, user: userData } };
    };

    const logout = () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
        setUser(null);
        setIsAuthenticated(false);
        setIsAdmin(false);
    };

    const value = {
        user,
        isAuthenticated,
        isAdmin,
        loading,
        login,
        register,
        googleLogin,
        logout,
        // Legacy socket property for components that still reference it
        socket: null
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

// Fast Refresh rule does not apply to shared hooks in this file.
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
