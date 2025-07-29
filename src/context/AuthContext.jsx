// --- START OF FILE src/context/AuthContext.jsx ---

import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import { loginApi, registerApi, googleLoginApi } from '../api/auth';
import { io } from 'socket.io-client'; // <-- IMPORT SOCKET.IO

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);
    const [loading, setLoading] = useState(true);
    const socketRef = useRef(null); // <-- REF TO HOLD THE SOCKET INSTANCE

    useEffect(() => {
        try {
            const storedToken = localStorage.getItem('authToken');
            const storedUser = localStorage.getItem('authUser');
            const storedIsAdmin = localStorage.getItem('isAdmin');
            if (storedToken && storedUser) {
                setToken(storedToken);
                setUser(JSON.parse(storedUser));
                setIsAdmin(storedIsAdmin === 'true');
                // Connect socket if token exists on initial load
                connectSocket(storedToken); 
            }
        } catch (error) {
            console.error("Failed to parse auth data from localStorage", error);
            localStorage.clear();
        } finally {
            setLoading(false);
        }
        // Disconnect on component unmount
        return () => disconnectSocket();
    }, []);

    const connectSocket = (authToken) => {
        if (socketRef.current) return; // Already connected
        const newSocket = io(import.meta.env.VITE_API_URL || 'http://localhost:5001', {
            // We don't need this for polling, but good for WebSocket transport
            // auth: { token: authToken } 
        });
        newSocket.on('connect', () => console.log('Socket.IO Client Connected'));
        newSocket.on('disconnect', () => console.log('Socket.IO Client Disconnected'));
        socketRef.current = newSocket;
    };

    const disconnectSocket = () => {
        if (socketRef.current) {
            socketRef.current.disconnect();
            socketRef.current = null;
        }
    };

    const login = async (username, password) => {
        const data = await loginApi(username, password);
        setToken(data.access_token);
        const userData = { username: data.username };
        setUser(userData);
        setIsAdmin(data.is_admin);
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('authUser', JSON.stringify(userData));
        localStorage.setItem('isAdmin', data.is_admin);
        connectSocket(data.access_token); // Connect after login
    };
    
    const googleLogin = async (googleToken) => {
        const data = await googleLoginApi(googleToken);
        setToken(data.access_token);
        const userData = { username: data.username };
        setUser(userData);
        setIsAdmin(data.is_admin);
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('authUser', JSON.stringify(userData));
        localStorage.setItem('isAdmin', data.is_admin);
        connectSocket(data.access_token);
    };

    const register = async (username, email, password) => {
        await registerApi(username, email, password);
    };

    const logout = () => {
        disconnectSocket(); // Disconnect before clearing data
        setUser(null);
        setToken(null);
        setIsAdmin(false);
        localStorage.clear();
    };

    const value = {
        user,
        token,
        isAuthenticated: !!token,
        isAdmin,
        loading,
        socket: socketRef.current, // <-- EXPOSE THE SOCKET
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

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
// --- END OF FILE src/context/AuthContext.jsx ---