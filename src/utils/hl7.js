// --- START OF FILE src/utils/hl7.js ---

// You have faker imported, I'll leave it in case you're using it elsewhere.
import { faker } from '@faker-js/faker';

// --- YOUR EXISTING STRIPPER FUNCTION - WE'LL KEEP IT ---
export const stripCommentsAndBlankLines = (message) => {
    if (!message) return '';

    const commentPrefixes = ['//', '#', '---'];
    // Split on any kind of newline, because the world is a messy place
    const lines = message.split(/\r?\n/);

    const validLines = lines.filter(line => {
        const trimmed = line.trim();
        if (!trimmed) {
            // It's a blank line, fuck it
            return false;
        }
        // Return true only if the line does NOT start with any of our comment prefixes
        return !commentPrefixes.some(prefix => trimmed.startsWith(prefix));
    });

    // Rejoin with the proper HL7 delimiter (carriage return)
    return validLines.join('\r');
};

// --- YOUR EXISTING, MORE ROBUST REBUILD FUNCTION - DEFINITELY KEEPING THIS ---
export function rebuildHl7Message(segments) {
    if (!segments || !segments.length) return "";

    return segments.map(segment => {
        const fieldSep = segments[0]?.fields?.find(f => f.index === 1)?.value || '|';
        
        // Use a more robust way to handle potentially sparse arrays
        const fieldValues = [];
        segment.fields.forEach(field => {
            // Adjust for 1-based indexing in HL7 vs 0-based in arrays
            const arrayIndex = (segment.name === 'MSH' && field.index > 1) ? field.index - 2 : field.index - 1;
            fieldValues[arrayIndex] = field.value;
        });

        // Fill any empty spots with empty strings to maintain correct pipe positions
        for (let i = 0; i < fieldValues.length; i++) {
            if (fieldValues[i] === undefined) {
                fieldValues[i] = '';
            }
        }
        
        if (segment.name === 'MSH') {
            // For MSH, the segment name and field separator are special
             return 'MSH' + fieldSep + fieldValues.join(fieldSep);
        } else {
            return segment.name + fieldSep + fieldValues.join(fieldSep);
        }
    }).join('\r');
}


// --- MY NEW FUNCTION, ADDED TO YOUR EXISTING FILE ---
/**
 * Peeks into an HL7 message string and yanks out the message type (e.g., "ADT", "ORU").
 * This is a lightweight, non-comprehensive parser for a very specific job.
 * @param {string} hl7Content The raw HL7 message content.
 * @returns {string} The message type (e.g., "ADT") or "Unknown".
 */
export const getHl7MessageType = (hl7Content) => {
    if (!hl7Content || typeof hl7Content !== 'string') {
        return 'Unknown';
    }

    try {
        // Find the MSH segment, no matter what line ending is used
        const lines = hl7Content.split(/[\r\n]+/);
        const mshLine = lines.find(line => line.trim().startsWith('MSH|'));

        if (!mshLine) {
            return 'Unknown';
        }

        const fields = mshLine.split('|');
        // MSH.9 is at index 8. It can be complex (e.g., "ADT^A01^ADT_A01")
        const msh9 = fields[8];

        if (!msh9) {
            return 'Unknown';
        }

        // The message type is the first component of MSH.9
        const messageType = msh9.split('^')[0].trim();
        
        return messageType || 'Unknown';

    } catch (e) {
        console.error("Failed to parse message type from HL7 content", e);
        return 'Unknown';
    }
};

// --- END OF FILE src/utils/hl7.js ---