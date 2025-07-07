import { faker } from '@faker-js/faker';

// Helper functions to make our lives easier
const hl7Date = (date = new Date()) => {
    const YYYY = date.getFullYear();
    const MM = String(date.getMonth() + 1).padStart(2, '0');
    const DD = String(date.getDate()).padStart(2, '0');
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    const ss = String(date.getSeconds()).padStart(2, '0');
    return `${YYYY}${MM}${DD}${hh}${mm}${ss}`;
};

const shortDate = (date = new Date()) => {
    const YYYY = date.getFullYear();
    const MM = String(date.getMonth() + 1).padStart(2, '0');
    const DD = String(date.getDate()).padStart(2, '0');
    return `${YYYY}${MM}${DD}`;
}

const createPerson = () => ({
    lastName: faker.person.lastName().toUpperCase(),
    firstName: faker.person.firstName().toUpperCase(),
    middleInitial: faker.person.middleName().charAt(0).toUpperCase(),
    dob: shortDate(faker.date.birthdate({ min: 18, max: 80, mode: 'age' })),
    sex: faker.person.sex().charAt(0).toUpperCase(),
    mrn: faker.string.numeric(8),
    address: {
        street: faker.location.streetAddress(),
        city: faker.location.city(),
        state: faker.location.state({ abbreviated: true }),
        zip: faker.location.zipCode(),
    }
});

const createPhysician = () => ({
    id: faker.string.numeric(6),
    lastName: faker.person.lastName().toUpperCase(),
    firstName: faker.person.firstName().toUpperCase(),
});


// --- The Message Templates ---

export const createORU_R01 = () => {
    const person = createPerson();
    const physician = createPhysician();
    const now = new Date();
    // --- THE FIX ---
    // Generate a single, unique accession number for the order.
    const accessionNumber = `LIS-ACC-${faker.string.numeric(8)}`;

    return `// ORU^R01: Unsolicited Observation Result (e.g., Lab Results)
// MSH: Message Header.
MSH|^~\\&|MegaLIS|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ORU^R01|MSGID${faker.string.numeric(5)}|P|2.5.1

// PID: Patient Identification.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}||${faker.phone.number()}

// ORC: Common Order.
ORC|RE|EMR-ORDER-${faker.string.alphanumeric(4)}|${accessionNumber}|||||||${hl7Date(now)}|||${physician.id}^${physician.lastName}^${physician.firstName}

// OBR: Observation Request.
OBR|1|EMR-ORDER-${faker.string.alphanumeric(4)}|${accessionNumber}|24331-1^LIPID PANEL^LN|||${hl7Date(now)}|||||||||${physician.id}^${physician.lastName}^${physician.firstName}||||||${hl7Date(now)}|||F

// --- Start of Results (Repeating OBX Group) ---
OBX|1|NM|15009-4^CHOLESTEROL^LN|1|${faker.number.int({ min: 150, max: 250 })}|mg/dL|<200|N|||F|||${hl7Date(now)}
OBX|2|NM|2571-8^TRIGLYCERIDE^LN|1|${faker.number.int({ min: 80, max: 180 })}|mg/dL|<150|N|||F|||${hl7Date(now)}
`;
};

export const createORM_O01 = () => {
    const person = createPerson();
    const physician = createPhysician();
    const now = new Date();
    // --- THE FIX ---
    // 1. Generate a single, unique accession number.
    const accessionNumber = `RIS-ACC-${faker.string.numeric(8)}`;
    const placerOrderNumber = `EMR-ORDER-${faker.string.alphanumeric(5)}`;

    const modalities = ['CT', 'MRI', 'US', 'XA', 'CR', 'NM'];
    const randomModality = faker.helpers.arrayElement(modalities);
    const orderCode = faker.helpers.arrayElement([
        'CTCHEST^CT Chest W/O Contrast^C4',
        'MRBRAIN^MRI Brain W/O Contrast^C4',
        'USABD^Ultrasound Abdomen Complete^C4',
        'XRELBOW^X-Ray Elbow Left^C4'
    ]);
    
    // --- THE FIX ---
    // 2. We build the OBR segment cleanly, ensuring our new accession number is in OBR-3.
    const obrSegment = [
        'OBR', // Segment Name
        '1', // OBR-1: Set ID
        placerOrderNumber, // OBR-2: Placer Order Number
        accessionNumber, // OBR-3: Filler Order Number (Accession Number)
        orderCode, // OBR-4: Universal Service Identifier
        '', // OBR-5: Priority
        '', // OBR-6: Requested Date/Time
        hl7Date(now), // OBR-7: Observation Date/Time
        '', '', '', '', '', '', '', '', // OBR-8 through OBR-15
        `${physician.id}^${physician.lastName}^${physician.firstName}`, // OBR-16: Ordering Provider
        '', '', '', '', '', '', '', // OBR-17 through OBR-23
        randomModality, // OBR-24: Diagnostic Serv Sect ID
    ].join('|');


    return `// ORM^O01: General Order Message (e.g., placing a new Radiology order)
// MSH: Message Header.
MSH|^~\\&|ClinicEMR|MainClinic|MegaRIS|MainClinic|${hl7Date(now)}||ORM^O01|MSGID${faker.string.numeric(5)}|P|2.5.1

// PID: Patient Identification.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}

// PV1: Patient Visit Information.
PV1|1|O|OP^Outpatient^^|||||${physician.id}^${physician.lastName}^${physician.firstName}

// ORC: Common Order.
ORC|NW|${placerOrderNumber}|${accessionNumber}|O|||||${hl7Date(now)}|||${physician.id}^${physician.lastName}^${physician.firstName}

// OBR: Observation Request. What is being ordered.
${obrSegment}
`;
};

export const createADT_A08 = () => {
    const person = createPerson();
    const now = new Date();

    return `// ADT^A08: Update Patient Information.
MSH|^~\\&|MasterMPI|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ADT^A08|MSGID${faker.string.numeric(5)}|P|2.5.1
EVN|A08|${hl7Date(now)}
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}||${faker.phone.number()}
PV1|1|O|OP^Outpatient^^
`;
};

export const createADT_A40 = () => {
    const correctPerson = createPerson();
    const incorrectPerson = { ...createPerson(), lastName: correctPerson.lastName };
    const now = new Date();

    return `// ADT^A40: Merge Patient Records.
MSH|^~\\&|MasterMPI|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ADT^A40|MSGID${faker.string.numeric(5)}|P|2.5.1
EVN|A40|${hl7Date(now)}
PID|1||${incorrectPerson.mrn}^^^MRN^MR||${incorrectPerson.lastName}^${incorrectPerson.firstName}^${incorrectPerson.middleInitial}||${incorrectPerson.dob}|${incorrectPerson.sex}
MRG|${correctPerson.mrn}^^^MRN^MR
`;
};

export const createORU_R01_Radiology = () => {
    const person = createPerson();
    const physician = createPhysician();
    const now = new Date();
    // --- THE FIX ---
    // Generate a single, unique accession number for the radiology order.
    const accessionNumber = `RAD-ACC-${faker.string.numeric(8)}`;
    const modalities = ['CT', 'MRI', 'US', 'XA', 'CR', 'NM'];
    const randomModality = faker.helpers.arrayElement(modalities);

    return `// ORU^R01: Unsolicited Observation Result (Radiology)
// MSH: Message Header.
MSH|^~\\&|MegaRIS|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ORU^R01|MSGID${faker.string.numeric(5)}|P|2.5.1

// PID: Patient Identification.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}||${faker.phone.number()}

// ORC: Common Order.
ORC|RE|EMR-ORDER-RAD-${faker.string.alphanumeric(4)}|${accessionNumber}|||||||${hl7Date(now)}|||${physician.id}^${physician.lastName}^${physician.firstName}

// OBR: Observation Request.
OBR|1|EMR-ORDER-RAD-${faker.string.alphanumeric(4)}|${accessionNumber}|CHEST-PA-LAT^Chest X-Ray PA and Lateral^C4|||${hl7Date(now)}|||||||||${physician.id}^${physician.lastName}^${physician.firstName}||||||${hl7Date(now)}||${randomModality}|F

// OBX: Observation/Result. The value type is 'TX' for Text.
OBX|1|TX|RAD-REPORT^Radiology Report^L|1|FINDINGS: The lungs are clear. Cardiomediastinal silhouette is unremarkable.~IMPRESSION: No acute cardiopulmonary process.|
`;
};