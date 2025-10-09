# Troubleshooting: Only 2 Models Showing in UI

## Problem
The UI only shows 2 models (gemini-2.5-flash and gemini-1.5-flash) instead of the 39 models available from the API.

## Diagnosis

The component has fallback logic that displays 2 default models if the API call fails:

```javascript
// Fallback models shown when API fails
const fallbackModels = [
    'models/gemini-2.5-flash',
    'models/gemini-1.5-flash',
];
```

## Possible Causes

1. **Not Logged In**: The API requires authentication. If you're not logged in when the component loads, the API call will fail with 401 Unauthorized.

2. **Invalid/Expired Token**: The JWT token might be expired or invalid.

3. **API Call Timing**: The component tries to fetch models on mount, but the auth token might not be available yet.

4. **Network/CORS Issue**: The API endpoint might not be accessible from the frontend.

## How to Debug

### Check Browser Console
Open the browser developer console (F12) and look for these messages:

- `✓ Fetched X models from API` - Success message
- `Error fetching available models:` - Error message with details
- `Error details: 401 {...}` - Shows the HTTP status code

### Verify You're Logged In
1. Check if you see the user status in the UI
2. Open DevTools → Application → Local Storage → Check for `token` key

### Test API Directly
```bash
# Get a valid token first
TOKEN=$(curl -s -X POST https://yeet.trazen.org/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}' | \
  grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test the endpoint
curl -H "Authorization: Bearer $TOKEN" https://yeet.trazen.org/api/available_models
```

## Solutions

### Solution 1: Wait for Login
The component now checks if a token exists before making the API call. If you're not logged in, it will skip the fetch.

### Solution 2: Refresh After Login
If the page was loaded before you logged in, try refreshing the page after logging in.

### Solution 3: Check Token Expiration
If your token expired, log out and log back in to get a fresh token.

### Solution 4: Manual Verification
Check the backend logs to see if the request is reaching the server:

```bash
docker compose logs hl7-yeeter --tail 50 | grep available_models
```

## Expected Behavior

When working correctly, you should see:
- A brief "Loading..." indicator
- Then a dropdown with 39+ model options
- Models displayed without the `models/` prefix for readability

## Code Changes Made

Added logging to help diagnose:
```javascript
// Success logging
console.log(`✓ Fetched ${response.data.models.length} models from API`);

// Error logging
console.error('Error fetching available models:', error);
console.error('Error details:', error.response?.status, error.response?.data);

// Token check
if (!token) {
    console.warn('No auth token available, skipping model fetch');
    setLoadingModels(false);
    return;
}
```

## Next Steps

1. Check browser console for error messages
2. Verify you're logged in with a valid token
3. If still failing, check the backend logs
4. Report the specific error message you see in the console
