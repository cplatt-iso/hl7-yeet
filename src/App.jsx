// --- START OF FILE src/App.jsx ---

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import HL7Parser from './components/HL7Parser';
import Login from './components/Login';
import Register from './components/Register';
import { useAuth } from './context/AuthContext';
import YeetLoader from './components/YeetLoader';
// --- NEW IMPORT ---
import { Toaster } from 'react-hot-toast';

function App() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <YeetLoader />
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-gray-100 p-4 md:p-8">
          {/* --- NEW: RENDER THE TOASTER COMPONENT --- */}
          {/* This component handles rendering all the toast notifications */}
          <Toaster 
            position="top-center"
            reverseOrder={false}
            toastOptions={{
              style: {
                background: '#374151', // bg-gray-700
                color: '#F9FAFB', // text-gray-100
              },
            }}
          />
          <Routes>
            <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/" />} />
            <Route path="/register" element={!isAuthenticated ? <Register /> : <Navigate to="/" />} />
            <Route path="/" element={<HL7Parser />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
      </div>
    </Router>
  );
}

export default App;
// --- END OF FILE src/App.jsx ---