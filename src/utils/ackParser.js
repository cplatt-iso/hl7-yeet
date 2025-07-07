// A simple parser for the world's simplest "protocol".
// It checks MSA-1 for the acknowledgement code.

export const parseAck = (ackMessage) => {
    if (!ackMessage || typeof ackMessage !== 'string' || !ackMessage.startsWith('MSH')) {
        return {
            status: 'unknown',
            color: 'text-gray-400',
            message: 'Response was not a valid HL7 ACK message.',
            raw: ackMessage,
        };
    }

    const segments = ackMessage.split(/\r?\n|\r/);
    const msaSegment = segments.find(seg => seg.startsWith('MSA'));

    if (!msaSegment) {
        return {
            status: 'unknown',
            color: 'text-yellow-400',
            message: 'ACK is missing the required MSA segment.',
            raw: ackMessage,
        };
    }

    const fields = msaSegment.split('|');
    const ackCode = fields[1]; // MSA-1
    const errorMessage = fields[3]; // MSA-3

    switch (ackCode) {
        case 'AA':
            return {
                status: 'Success (AA)',
                color: 'text-green-400',
                message: 'Application Accept: The message was received and processed successfully by the remote system.',
                raw: ackMessage,
            };
        case 'AE':
            return {
                status: 'Error (AE)',
                color: 'text-red-400',
                message: `Application Error: The remote system reported an error. ${errorMessage ? `Details: ${errorMessage}` : 'No details provided.'}`,
                raw: ackMessage,
            };
        case 'AR':
            return {
                status: 'Rejected (AR)',
                color: 'text-orange-400',
                message: `Application Reject: The remote system rejected the message. ${errorMessage ? `Details: ${errorMessage}` : 'No details provided.'}`,
                raw: ackMessage,
            };
        default:
            return {
                status: `Unknown Code (${ackCode})`,
                color: 'text-yellow-400',
                message: 'An unknown or non-standard acknowledgement code was received.',
                raw: ackMessage,
            };
    }
};