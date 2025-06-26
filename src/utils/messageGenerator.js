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

    return `// ORU^R01: Unsolicited Observation Result (e.g., Lab Results)
// MSH: Message Header. Identifies this as an ORU^R01 (Observation Result) from a Lab system to an EMR.
MSH|^~\\&|MegaLIS|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ORU^R01|MSGID${faker.string.numeric(5)}|P|2.5.1

// PID: Patient Identification. Identifies the patient.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}||${faker.phone.number()}

// ORC: Common Order. General information about the order.
ORC|RE|EMR-ORDER-${faker.string.alphanumeric(4)}|LIS-ORDER-${faker.string.alphanumeric(4)}||||||${hl7Date(now)}|||${physician.id}^${physician.lastName}^${physician.firstName}

// OBR: Observation Request. Describes the test that was ordered: a Lipid Panel.
OBR|1|EMR-ORDER-${faker.string.alphanumeric(4)}|LIS-ORDER-${faker.string.alphanumeric(4)}|24331-1^LIPID PANEL^LN|||${hl7Date(now)}|||||||||${physician.id}^${physician.lastName}^${physician.firstName}||||||${hl7Date(now)}|||F

// --- Start of Results (Repeating OBX Group) ---

// OBX #1: Cholesterol Result.
OBX|1|NM|15009-4^CHOLESTEROL^LN|1|${faker.number.int({ min: 150, max: 250 })}|mg/dL|<200|N|||F|||${hl7Date(now)}

// OBX #2: Triglycerides Result.
OBX|2|NM|2571-8^TRIGLYCERIDE^LN|1|${faker.number.int({ min: 80, max: 180 })}|mg/dL|<150|N|||F|||${hl7Date(now)}
`;
};

export const createORM_O01 = () => {
    const person = createPerson();
    const physician = createPhysician();
    const now = new Date();

    const modalities = ['CT', 'MRI', 'US', 'XA', 'CR', 'NM'];
    const randomModality = faker.helpers.arrayElement(modalities);
    const orderCode = faker.helpers.arrayElement([
        'CTCHEST^CT Chest W/O Contrast^C4',
        'MRBRAIN^MRI Brain W/O Contrast^C4',
        'USABD^Ultrasound Abdomen Complete^C4',
        'XRELBOW^X-Ray Elbow Left^C4'
    ]);

    const obrFields = new Array(25).fill(''); // Create an array for fields up to 24
    obrFields[1] = '1'; // OBR-1: Set ID
    obrFields[2] = `EMR-ORDER-${faker.string.alphanumeric(5)}`; // OBR-2: Placer Order Number
    obrFields[4] = orderCode; // OBR-4: Universal Service Identifier
    obrFields[7] = hl7Date(now); // OBR-7: Observation Date/Time
    obrFields[24] = randomModality; // OBR-24: Diagnostic Serv Sect ID (Modality)

    // Join the fields with pipes, starting with the segment name
    const obrSegment = 'OBR' + obrFields.join('|');


    return `// ORM^O01: General Order Message (e.g., placing a new Radiology order)
// MSH: Message Header. Identifies this as an ORM^O01 from an EMR to a Radiology system.
MSH|^~\\&|ClinicEMR|MainClinic|MegaRIS|MainClinic|${hl7Date(now)}||ORM^O01|MSGID${faker.string.numeric(5)}|P|2.5.1

// PID: Patient Identification.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}

// PV1: Patient Visit Information.
PV1|1|O|OP^Outpatient^^|||||${physician.id}^${physician.lastName}^${physician.firstName}

// ORC: Common Order. This is a New Order ('NW').
ORC|NW|EMR-ORDER-${faker.string.alphanumeric(5)}|||||||${hl7Date(now)}|||${physician.id}^${physician.lastName}^${physician.firstName}

// OBR: Observation Request. What is being ordered.
// Now constructed correctly to place the modality in OBR-24.
${obrSegment}
`;
};

export const createADT_A08 = () => {
    const person = createPerson();
    const now = new Date();

    return `// ADT^A08: Update Patient Information.
// MSH: Message Header.
MSH|^~\\&|MasterMPI|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ADT^A08|MSGID${faker.string.numeric(5)}|P|2.5.1

// EVN: Event Type. A08 signifies an update.
EVN|A08|${hl7Date(now)}

// PID: Patient Identification. Contains the updated information.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}||${faker.phone.number()}

// PV1: Patient Visit segment.
PV1|1|O|OP^Outpatient^^
`;
};

export const createADT_A40 = () => {
    const correctPerson = createPerson();
    const incorrectPerson = { ...createPerson(), lastName: correctPerson.lastName };
    const now = new Date();

    return `// ADT^A40: Merge Patient Records.
// MSH: Message Header.
MSH|^~\\&|MasterMPI|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ADT^A40|MSGID${faker.string.numeric(5)}|P|2.5.1

// EVN: Event Type. A40 for merge.
EVN|A40|${hl7Date(now)}

// PID: This is the INCORRECT record to be merged FROM.
// This record will become inactive after the merge.
PID|1||${incorrectPerson.mrn}^^^MRN^MR||${incorrectPerson.lastName}^${incorrectPerson.firstName}^${incorrectPerson.middleInitial}||${incorrectPerson.dob}|${incorrectPerson.sex}

// MRG: Merge Information. Links the incorrect MRN to the correct one.
MRG|${correctPerson.mrn}^^^MRN^MR
`;
};

export const createORU_R01_Radiology = () => {
    const person = createPerson();
    const physician = createPhysician();
    const now = new Date();

    // --- THE FIX IS HERE ---
    // 1. Define the possible modalities
    const modalities = ['CT', 'MRI', 'US', 'XA', 'CR', 'NM'];
    // 2. Pick one at random
    const randomModality = faker.helpers.arrayElement(modalities);

    return `// ORU^R01: Unsolicited Observation Result (Radiology)
// MSH: Message Header. From a Radiology system (RIS) to an EMR.
MSH|^~\\&|MegaRIS|MainClinic|ClinicEMR|MainClinic|${hl7Date(now)}||ORU^R01|MSGID${faker.string.numeric(5)}|P|2.5.1

// PID: Patient Identification.
PID|1||${person.mrn}^^^MRN^MR||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}||${faker.phone.number()}

// ORC: Common Order.
ORC|RE|EMR-ORDER-RAD-${faker.string.alphanumeric(4)}|RIS-ACCESSION-${faker.string.alphanumeric(4)}||||||${hl7Date(now)}|||${physician.id}^${physician.lastName}^${physician.firstName}

// OBR: Observation Request. Describes the Radiology study.
// 3. Inject the modality code into OBR-24 (the field before Result Status 'F').
OBR|1|EMR-ORDER-RAD-${faker.string.alphanumeric(4)}|RIS-ACCESSION-${faker.string.alphanumeric(4)}|CHEST-PA-LAT^Chest X-Ray PA and Lateral^C4|||${hl7Date(now)}|||||||||${physician.id}^${physician.lastName}^${physician.firstName}||||||${hl7Date(now)}||${randomModality}|F

// OBX: Observation/Result. The value type is 'TX' for Text.
// The observation value is a multi-line report using repeat delimiters (the '~' character by default).
OBX|1|TX|RAD-REPORT^Radiology Report^L|1|FINDINGS: The lungs are clear. Cardiomediastinal silhouette is unremarkable.~IMPRESSION: No acute cardiopulmonary process.|
`;
};