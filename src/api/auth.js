const API_URL = ''; // Uses the Vite proxy

// A helper to handle auth responses, because they're a bit different
const handleAuthResponse = async (response) => {
    const data = await response.json();
    if (!response.ok) {
        // The backend should return an 'error' key with a message
        throw new Error(data.error || `Server responded with ${response.status}`);
    }
    return data;
};

export const registerApi = async (username, email, password) => {
    const response = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
    });
    return handleAuthResponse(response);
};

export const loginApi = async (username, password) => {
    const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });
    // On success, this will return { access_token, username }
    return handleAuthResponse(response);
};

// There's no backend endpoint for logout with JWTs.
// Logout is a purely client-side action: just delete the token.
// We include this function here for consistency.
export const logoutApi = async () => {
    // This is a formality. The real work happens in the AuthContext.
    return Promise.resolve();
};