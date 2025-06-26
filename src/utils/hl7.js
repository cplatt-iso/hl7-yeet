import { faker } from '@faker-js/faker';

// --- NEW STRIPPER UTILITY FUNCTION ---
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

// This function remains unchanged
export function rebuildHl7Message(segments) {
    if (!segments || !segments.length) return "";

    return segments.map(segment => {
        if (segment.name === 'MSH') {
            const maxIndex = Math.max(0, ...segment.fields.map(f => f.index));
            const fields = new Array(maxIndex + 1).fill('');
            segment.fields.forEach(field => {
                if (field.index === 1) fields[0] = field.value;
                else if (field.index === 2) fields[1] = field.value;
                else if (field.index > 2) fields[field.index - 1] = field.value;
            });
            const fieldSep = fields[0] || '|';
            return 'MSH' + fieldSep + fields.slice(1).join(fieldSep);
        } else {
            const maxIndex = Math.max(0, ...segment.fields.map(f => f.index));
            const fields = new Array(maxIndex + 1).fill('');
            fields[0] = segment.name;
            segment.fields.forEach(field => {
                fields[field.index] = field.value;
            });
            return fields.join('|');
        }
    }).join('\r');
}