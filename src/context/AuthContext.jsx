import React, { createContext, useState, useContext, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import { loginApi, registerApi, googleLoginApi } from '../api/auth';
import { API_BASE_URL } from '../api/config';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isAdmin, setIsAdmin] = useState(false);
    const [loading, setLoading] = useState(true);
    const [socket, setSocket] = useState(null);
    const socketRef = useRef(null);

    const SOCKET_URL = useRef(import.meta.env.VITE_SOCKET_URL || API_BASE_URL);

    const disconnectSocket = useCallback(() => {
        if (socketRef.current) {
            socketRef.current.removeAllListeners();
            socketRef.current.disconnect();
            socketRef.current = null;
        }
        setSocket(null);
    }, []);

    const connectSocket = useCallback((token) => {
        if (!token) {
            return null;
        }

        // Tear down any existing connection before creating a new one
        if (socketRef.current) {
            disconnectSocket();
        }

        const nextSocket = io(SOCKET_URL.current, {
            auth: { token },
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
        });

        const handleConnectError = (error) => {
            console.error('[HL7 Yeeter] Socket.IO connection error:', error.message);
        };

        nextSocket.on('connect_error', handleConnectError);

        socketRef.current = nextSocket;
        setSocket(nextSocket);

        return () => {
            nextSocket.off('connect_error', handleConnectError);
            nextSocket.removeAllListeners();
            nextSocket.disconnect();
            if (socketRef.current === nextSocket) {
                socketRef.current = null;
            }
            setSocket(null);
        };
    }, [disconnectSocket]);

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
        return () => {
            disconnectSocket();
        };
    }, [connectSocket, disconnectSocket]);

    useEffect(() => {
        if (!isAuthenticated) {
            disconnectSocket();
            return;
        }

        const token = localStorage.getItem('authToken');
        if (!token) {
            disconnectSocket();
            return;
        }

        const cleanup = connectSocket(token);
        return () => {
            if (cleanup) {
                cleanup();
            }
        };
    }, [isAuthenticated, connectSocket, disconnectSocket]);

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
        disconnectSocket();
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
        socket,
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
