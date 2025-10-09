# Fix: Auth Token Key Mismatch

## Problem
1. MLLP listener doesn't fire from the UI
2. Only 2 models showing instead of 39 available models

## Root Cause
**localStorage key mismatch**: The application stores the auth token as `authToken`, but the SettingsPanel component was looking for `token`.

```javascript
// AuthContext stores token as:
localStorage.setItem('authToken', access_token);

// SettingsPanel was looking for:
const token = localStorage.getItem('token');  // ❌ WRONG KEY!
```

This caused all API calls to fail with 401 Unauthorized because no valid token was being sent.

## Impact
- **SettingsPanel**: Couldn't fetch available models → fell back to 2 hardcoded models
- **Listener API**: All calls failed silently with 401 → listener never started
- **Any other features using the models**: Would fail

## Fix
Changed SettingsPanel to use the correct localStorage key:

```javascript
// Before (incorrect)
const token = localStorage.getItem('token');

// After (correct)
const token = localStorage.getItem('authToken');
```

## Files Changed
- `src/components/SettingsPanel.jsx` - Fixed localStorage key

## Verification

### Test Models Dropdown
1. Log in to the application
2. Navigate to the HL7 Parser page
3. Check the "AI Analysis Model" dropdown
4. **Expected**: Should show 39+ models
5. **Browser Console**: Should see `✓ Fetched 39 models from API`

### Test MLLP Listener
1. Go to the Listener tab
2. Set a port (e.g., 5002)
3. Click "Start Listener"
4. **Expected**: Listener starts successfully
5. **Backend logs**: Should show listener starting on the specified port

### Check Browser Console
```javascript
// Success - you should see:
✓ Fetched 39 models from API

// Failure - you would see:
Error fetching available models: ...
Error details: 401 { "msg": "Missing Authorization Header" }
```

## Related Issues
All API calls in the application use `apiUtils.getAuthHeaders()` which correctly looks for `authToken`:

```javascript
export const getAuthHeaders = () => {
    const token = localStorage.getItem('authToken');  // ✓ CORRECT
    // ...
}
```

The SettingsPanel was the only component directly accessing localStorage instead of using the utility function.

## Lesson Learned
- Always use centralized auth utility functions (`getAuthHeaders()`)
- Don't directly access localStorage for auth tokens
- Consistent naming conventions across the codebase prevent these issues

## Deployment
Changes are in the frontend code. No backend changes needed.

Refresh the browser after deployment to load the fixed JavaScript bundle.
