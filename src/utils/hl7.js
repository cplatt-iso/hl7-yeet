// --- START OF FILE src/utils/hl7.js ---

// ... your existing stripCommentsAndBlankLines and rebuildHl7Message functions are here ...
export const stripCommentsAndBlankLines = (message) => {
    if (!message) return '';

    const commentPrefixes = ['//', '#', '---'];
    const lines = message.split(/\r?\n/);

    const validLines = lines.filter(line => {
        const trimmed = line.trim();
        if (!trimmed) {
            return false;
        }
        return !commentPrefixes.some(prefix => trimmed.startsWith(prefix));
    });

    return validLines.join('\r');
};

export function rebuildHl7Message(segments) {
    if (!segments || !segments.length) return "";

    return segments.map(segment => {
        const fieldSep = segments[0]?.fields?.find(f => f.index === 1)?.value || '|';
        
        const fieldValues = [];
        segment.fields.forEach(field => {
            const arrayIndex = (segment.name === 'MSH' && field.index > 1) ? field.index - 2 : field.index - 1;
            fieldValues[arrayIndex] = field.value;
        });

        for (let i = 0; i < fieldValues.length; i++) {
            if (fieldValues[i] === undefined) {
                fieldValues[i] = '';
            }
        }
        
        if (segment.name === 'MSH') {
             return 'MSH' + fieldSep + fieldValues.join(fieldSep);
        } else {
            return segment.name + fieldSep + fieldValues.join(fieldSep);
        }
    }).join('\r');
}


export const getHl7MessageType = (hl7Content) => {
    if (!hl7Content || typeof hl7Content !== 'string') {
        return 'Unknown';
    }

    try {
        const lines = hl7Content.split(/[\r\n]+/);
        const mshLine = lines.find(line => line.trim().startsWith('MSH|'));

        if (!mshLine) {
            return 'Unknown';
        }

        const fields = mshLine.split('|');
        const msh9 = fields[8];

        if (!msh9) {
            return 'Unknown';
        }

        const messageType = msh9.split('^')[0].trim();
        
        return messageType || 'Unknown';

    } catch (e) {
        console.error("Failed to parse message type from HL7 content", e);
        return 'Unknown';
    }
};


// --- NEW FUNCTION, YOU BEAUTIFUL BASTARD ---
/**
 * Converts a bastardized JSON representation of an HL7 message into a proper,
 * carriage-return delimited HL7 string.
 * @param {string} jsonString The JSON string to convert.
 * @returns {string} The formatted HL7 message.
 * @throws {Error} If the input is not valid JSON or is missing the MSH segment.
 */
export const convertJsonToHl7 = (jsonString) => {
    let messageObject;
    try {
        messageObject = JSON.parse(jsonString);
    } catch {
        throw new Error("Invalid JSON provided. Could not parse.");
    }

    if (!messageObject || typeof messageObject !== 'object' || Array.isArray(messageObject)) {
        throw new Error("Input is not a valid JSON object.");
    }

    // MSH must exist and must come first.
    if (!messageObject.MSH || !messageObject.MSH.startsWith('MSH|')) {
        throw new Error("JSON is missing a valid MSH segment key/value.");
    }

    const segments = [];
    
    // 1. Add the MSH segment
    segments.push(messageObject.MSH);

    // 2. Add all other segments in the order they appear
    for (const key in messageObject) {
        // We've already handled MSH, so skip it here.
        if (key.toUpperCase() === 'MSH') {
            continue;
        }
        
        // This handles cases where a segment might appear multiple times, e.g. "OBX": ["OBX|1...", "OBX|2..."]
        if (Array.isArray(messageObject[key])) {
            segments.push(...messageObject[key]);
        } else {
            segments.push(messageObject[key]);
        }
    }

    // 3. Join with the one true HL7 delimiter.
    return segments.join('\r');
};

// --- END OF FILE src/utils/hl7.js ---