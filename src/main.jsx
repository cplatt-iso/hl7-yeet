// --- START OF FILE src/main.jsx ---
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { AuthProvider } from './context/AuthContext.jsx'
// --- NEW GOOGLE IMPORT ---
import { GoogleOAuthProvider } from '@react-oauth/google';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

console.log('%c[HL7 Yeeter Frontend] Google Client ID being used:', 'color: cyan; font-weight: bold;', GOOGLE_CLIENT_ID);
if (!GOOGLE_CLIENT_ID) {
    console.error('%c[HL7 Yeeter Frontend] FATAL: VITE_GOOGLE_CLIENT_ID is not defined in your frontend .env file!', 'color: red; font-weight: bold;');
    // You could even render an error message to the screen here
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* --- WRAP EVERYTHING IN THE GOOGLE PROVIDER --- */}
    {GOOGLE_CLIENT_ID ? (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </GoogleOAuthProvider>
    ) : (
      <AuthProvider>
        <App />
      </AuthProvider>
    )}
  </React.StrictMode>,
)