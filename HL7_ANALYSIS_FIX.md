# Fix: HL7 Analysis Error - 'str' object has no attribute 'keys'

## Problem

The HL7 analysis endpoint was failing with:

```text
ERROR:root:Error during AI analysis: 'str' object has no attribute 'keys'
AttributeError: 'str' object has no attribute 'keys'
```

This occurred in the `_reconstruct_hl7_from_json` function when trying to reconstruct the fixed HL7 message from the AI's JSON response.

## Root Cause

The `_reconstruct_hl7_from_json` function expected the `fields` parameter to always be a dictionary with field keys like `"MSH.1"`, `"MSH.2"`, etc. However, the AI could return the `fixed_message` in different formats:

1. **As a dict of dicts**: `{"MSH": {"MSH.1": "|", "MSH.2": "value"}, ...}` ✅ Expected format
2. **As a dict of strings**: `{"MSH": "MSH|^~\\&|...", ...}` ❌ Caused the error
3. **As a plain string**: `"MSH|^~\\&|...\rPID|..."` ✅ Already reconstructed

The function didn't handle cases 2 and 3, causing the crash when `fields` was a string.

## Solution Applied

### 1. Added Type Checking to `_reconstruct_hl7_from_json`

Modified `/home/icculus/projects/yeeter/app/routes/mllp_routes.py`:

```python
def _reconstruct_hl7_from_json(fixed_message_json):
    reconstructed_segments = []
    for segment_name, fields in fixed_message_json.items():
        # Handle case where fields is already a string (segment line)
        if isinstance(fields, str):
            reconstructed_segments.append(fields)
            continue
        
        # Handle case where fields is not a dict
        if not isinstance(fields, dict):
            logging.warning(f"Unexpected type for fields in segment {segment_name}: {type(fields)}")
            continue
        
        # ... rest of the function
```

### 2. Improved Error Handling in `analyze_hl7_api`

Added better error handling before calling the reconstruction function:

```python
# Handle fixed_message reconstruction if it's a structured JSON object
if 'fixed_message' in analysis_result:
    fixed_msg = analysis_result['fixed_message']
    if isinstance(fixed_msg, dict):
        try:
            analysis_result['fixed_message'] = _reconstruct_hl7_from_json(fixed_msg)
        except Exception as e:
            logging.error(f"Error reconstructing HL7 from JSON: {e}", exc_info=True)
            # Keep the original dict if reconstruction fails
            analysis_result['fixed_message_error'] = str(e)
    elif isinstance(fixed_msg, str):
        # Already a string, use as-is
        pass
    else:
        logging.warning(f"Unexpected type for fixed_message: {type(fixed_msg)}")
```

## Benefits

- ✅ **Handles multiple AI response formats** - Works with dicts, strings, or mixed formats
- ✅ **Graceful error handling** - Doesn't crash if reconstruction fails
- ✅ **Better logging** - Warns about unexpected data types
- ✅ **Preserves original data** - If reconstruction fails, keeps the original response
- ✅ **Backward compatible** - Still works with the expected dict format

## Testing

After rebuilding, try the HL7 analysis feature:

1. Go to the HL7 Parser tab
2. Select "AI Analysis" tab
3. Paste an HL7 message
4. Click "Analyze with AI"
5. Should now work without the AttributeError

## Notes

The AI (Gemini) can return the `fixed_message` in various formats depending on how it interprets the prompt. This fix makes the code more robust to handle all possible formats the AI might return.
