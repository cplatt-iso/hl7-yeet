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