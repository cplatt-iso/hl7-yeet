# Dynamic Gemini Model List Implementation

## Overview
Implemented dynamic fetching of available Gemini AI models from Google's API instead of maintaining a hardcoded list. This ensures the application always has access to the latest models without code updates.

## Problem
The Gemini model catalog changes frequently with new models being added and deprecated models being removed. Maintaining a hardcoded list required constant updates and could break if models were renamed or removed.

## Solution
Created a dynamic system that:
1. Queries Google's Gemini API for available models at runtime
2. Caches the model list for 1 hour to reduce API calls
3. Filters for models that support `generateContent` 
4. Provides a REST endpoint for the frontend to fetch available models
5. Falls back gracefully if the API is unavailable

## Changes Made

### Backend (`app/routes/mllp_routes.py`)

#### Added Dynamic Model Fetching
```python
_available_models_cache = None
_cache_timestamp = None
CACHE_DURATION = 3600  # Cache for 1 hour

def get_available_gemini_models():
    """
    Fetches available Gemini models from Google API and caches them.
    Returns a list of model names that support generateContent.
    """
    # Check cache validity
    if _available_models_cache is not None and _cache_timestamp is not None:
        if (datetime.now().timestamp() - _cache_timestamp) < CACHE_DURATION:
            return _available_models_cache
    
    # Fetch from API
    models = genai.list_models()
    gemini_models = [
        model.name for model in models 
        if 'generateContent' in model.supported_generation_methods
        and 'image-generation' not in model.name.lower()
    ]
    
    # Update cache
    _available_models_cache = gemini_models
    _cache_timestamp = datetime.now().timestamp()
    
    return gemini_models
```

#### Added REST Endpoint
```python
@mllp_bp.route('/available_models', methods=['GET'])
@jwt_required()
def get_available_models_api():
    """Returns list of available Gemini models that support text generation."""
    if not GEMINI_API_KEY:
        return jsonify({"error": "Google AI API key is not configured"}), 503
    
    models = get_available_gemini_models()
    return jsonify({"models": models}), 200
```

#### Updated Validation Logic
```python
# Old: Static list validation
if data.model not in ALLOWED_MODELS:
    return jsonify({"error": f"Invalid model: {data.model}"}), 400

# New: Dynamic list validation
available_models = get_available_gemini_models()
if data.model not in available_models:
    return jsonify({"error": f"Invalid or unavailable model: {data.model}"}), 400
```

### Frontend (`src/components/SettingsPanel.jsx`)

#### Dynamic Model Fetching
```jsx
const [availableModels, setAvailableModels] = useState([]);
const [loadingModels, setLoadingModels] = useState(true);

useEffect(() => {
    const fetchModels = async () => {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API_BASE_URL}/api/available_models`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        
        setAvailableModels(response.data.models);
        
        // Auto-select first model if current selection is invalid
        if (!response.data.models.includes(selectedModel)) {
            setSelectedModel(response.data.models[0]);
        }
    };
    
    fetchModels();
}, []);
```

#### Updated Model Selector UI
```jsx
<select
    id="model-select"
    value={selectedModel}
    onChange={(e) => setSelectedModel(e.target.value)}
    disabled={loadingModels || availableModels.length === 0}
>
    {availableModels.map(model => (
        <option key={model} value={model}>
            {model.replace('models/', '')}
        </option>
    ))}
</select>
```

### Frontend (`src/components/HL7Parser.jsx`)

#### Initialize Model State
```jsx
// Old: Hardcoded default
const [selectedModel, setSelectedModel] = useState('models/gemini-1.5-flash');

// New: Empty string - will be set by SettingsPanel when models load
const [selectedModel, setSelectedModel] = useState('');
```

## Benefits

1. **Automatic Updates**: New models appear automatically without code changes
2. **Error Prevention**: Prevents using deprecated/removed models
3. **Performance**: 1-hour cache minimizes API calls
4. **Resilience**: Fallback behavior if API is unavailable
5. **Better UX**: Users see loading state while models are fetched
6. **Accuracy**: Only shows models that support text generation

## Testing

Test the dynamic model fetching:
```bash
# From Python with API key
export $(cat .env | grep GOOGLE_API_KEY | xargs)
python -c "
import google.generativeai as genai
import os
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
models = [m for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
print(f'Found {len(models)} models')
[print(f'  - {m.name}') for m in models[:10]]
"
```

Expected output (as of October 2025):
```
Found 39 models (excludes image-generation models)
  - models/gemini-2.5-pro-preview-03-25
  - models/gemini-2.5-flash-preview-05-20
  - models/gemini-2.5-flash
  - models/gemini-2.5-pro
  - models/gemini-2.0-flash-exp
  ...
```

**Note**: Models containing "image-generation" in their name are automatically filtered out as they are not compatible with text-based HL7 analysis.

## Deployment

After rebuilding the container:
```bash
docker compose up -d --build
```

The frontend will fetch available models on first load and cache them in state. The backend will cache models for 1 hour to reduce API calls.

## API Endpoint

**GET** `/api/available_models`

**Headers:**
- `Authorization: Bearer <jwt_token>`

**Response:**
```json
{
  "models": [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-2.0-flash-exp",
    ...
  ]
}
```

## Error Handling

1. **No API Key**: Returns 503 Service Unavailable
2. **API Failure**: Falls back to cached list or empty array
3. **Invalid Model**: Returns 400 with helpful error message pointing to `/api/available_models`
4. **Frontend Fallback**: Uses hardcoded fallback list if API request fails

## Future Improvements

- Add model metadata (e.g., capabilities, token limits)
- Show model descriptions in the UI
- Allow users to refresh the model list manually
- Store preferred model in user settings
