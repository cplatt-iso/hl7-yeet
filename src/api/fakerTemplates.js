import { faker } from '@faker-js/faker';

const generateTimestamp = () => new Date().toISOString().replace(/[-:.]/g, '').slice(0, 14);

// A data structure for our smart order generation
const radiologyExams = [
    { name: "Chest X-Ray (2 views)", code: "71046", modality: "CR" },
    { name: "CT Head w/o contrast", code: "70450", modality: "CT" },
    { name: "MRI Brain w/ & w/o contrast", code: "70553", modality: "MR" },
    { name: "Ultrasound Abdomen Complete", code: "76700", modality: "US" },
    { name: "PET Whole Body", code: "78815", modality: "PT" },
    { name: "Digital Mammography Screening", code: "77067", modality: "MG" },
];

// --- NEW: Arrays for MSH field variability ---
const sendingApps = ['ORDER_ENTRY', 'EMR_MAIN', 'CLINIC_SYS', 'WEB_PORTAL', 'LAB_APP'];
const sendingFacilities = ['CENTRAL_HOSP', 'NORTH_CLINIC', 'SOUTH_HOSP', 'WEST_IMAGING', 'EAST_LAB'];
const receivingApps = ['RIS_MAIN', 'EHR_MASTER', 'BILLING_SYS', 'PACS_ARCHIVE', 'PHARMACY_APP'];
const receivingFacilities = ['RADIOLOGY_DEPT', 'MAIN_CAMPUS', 'IMAGING_CTR', 'SPECIALTY_LAB', 'INPATIENT_PHARM'];

// --- HELPER FUNCTIONS ---
const createPerson = () => {
    const sex = faker.person.sex();
    const firstName = faker.person.firstName(sex);
    const lastName = faker.person.lastName();
    const birthDate = faker.date.birthdate({ min: 18, max: 85, mode: 'age' });

    return {
        firstName: firstName.toUpperCase(),
        lastName: lastName.toUpperCase(),
        middleInitial: faker.person.middleName().charAt(0).toUpperCase(),
        dob: birthDate.toISOString().slice(0, 10).replace(/-/g, ''),
        sex: sex.charAt(0).toUpperCase(),
        mrn: faker.string.numeric(8),
        address: {
            street: faker.location.streetAddress(),
            city: faker.location.city(),
            state: faker.location.state({ abbreviated: true }),
            zip: faker.location.zipCode(),
        }
    };
};

const createPhysician = () => ({
    id: faker.string.numeric(6),
    lastName: faker.person.lastName().toUpperCase(),
    firstName: faker.person.firstName().toUpperCase(),
    middleInitial: faker.person.middleName().charAt(0).toUpperCase(),
});

const hl7Date = (date) => date.toISOString().replace(/[-:.]/g, '').slice(0, 14);

// --- MESSAGE TEMPLATE GENERATORS ---

const createADT_A01 = () => {
    const now = new Date();
    const person = createPerson();
    const physician = createPhysician();
    const sendingApp = faker.helpers.arrayElement(sendingApps);
    const sendingFacility = faker.helpers.arrayElement(sendingFacilities);
    const receivingApp = faker.helpers.arrayElement(receivingApps);
    const receivingFacility = faker.helpers.arrayElement(receivingFacilities);
    return `// ADT^A01: Patient Admission
${[
        `MSH|^~\\&|${sendingApp}|${sendingFacility}|${receivingApp}|${receivingFacility}|${hl7Date(now)}||ADT^A01^ADT_A01|MSG${faker.string.numeric(7)}|P|2.5.1`,
        `EVN|A01|${hl7Date(now)}`,
        `PID|1||${person.mrn}||${person.lastName}^${person.firstName}^${person.middleInitial}||${person.dob}|${person.sex}`,
        `PV1|1|I|AMB^^^AMB|||||${physician.id}^${physician.lastName}^${physician.firstName}`
    ].join('\r')}
`;
};

const createORU_R01 = () => {
    const now = new Date();
    const person = createPerson();
    const physician = createPhysician();
    const placerNum = `${faker.string.numeric(8)}^EHR`;
    const sendingApp = faker.helpers.arrayElement(sendingApps);
    const sendingFacility = faker.helpers.arrayElement(sendingFacilities);
    const receivingApp = faker.helpers.arrayElement(receivingApps);
    const receivingFacility = faker.helpers.arrayElement(receivingFacilities);
    return `// ORU^R01: Unsolicited Lab Result
${[
        `MSH|^~\\&|${sendingApp}|${sendingFacility}|${receivingApp}|${receivingFacility}|${hl7Date(now)}||ORU^R01^ORU_R01|MSG${faker.string.numeric(7)}|P|2.5.1`,
        `PID|1||${person.mrn}||${person.lastName}^${person.firstName}||${person.dob}|${person.sex}|||${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}`,
        `OBR|1|${placerNum}||CBC^Complete Blood Count|||${hl7Date(now)}|||||||||${physician.id}^${physician.lastName}^${physician.firstName}||||||F`,
        `OBX|1|NM|WBC^White Blood Cell Count||${faker.number.float({ min: 4.0, max: 11.0, precision: 0.1 })}|10*3/uL|4.0-11.0|N|||F`,
        `OBX|2|NM|RBC^Red Blood Cell Count||${faker.number.float({ min: 4.2, max: 5.9, precision: 0.2 })}|10*6/uL|4.2-5.9|N|||F`
    ].join('\r')}
`;
};

const createSIU_S12 = () => {
    const now = new Date();
    const person = createPerson();
    const appointmentTime = faker.date.future({ years: 0.1 });
    const sendingApp = faker.helpers.arrayElement(sendingApps);
    const sendingFacility = faker.helpers.arrayElement(sendingFacilities);
    const receivingApp = faker.helpers.arrayElement(receivingApps);
    const receivingFacility = faker.helpers.arrayElement(receivingFacilities);
    return `// SIU^S12: New Appointment Booking
${[
        `MSH|^~\\&|${sendingApp}|${sendingFacility}|${receivingApp}|${receivingFacility}|${hl7Date(now)}||SIU^S12^SIU_S12|MSG${faker.string.numeric(7)}|P|2.5.1`,
        `SCH|1|${faker.string.numeric(6)}|||EVT_REASON^New Appointment|||20^Min|^^^${hl7Date(appointmentTime)}`,
        `PID|1||${person.mrn}||${person.lastName}^${person.firstName}`,
        `PV1|1|O`,
        `AIL|1||RADIOLOGY^Rad Dept||${hl7Date(appointmentTime)}|`
    ].join('\r')}
`;
};

const createMDM_T02 = () => {
    const now = new Date();
    const person = createPerson();
    const documentContent = btoa(faker.lorem.paragraphs(2)); // Base64 encode text content
    const sendingApp = faker.helpers.arrayElement(sendingApps);
    const sendingFacility = faker.helpers.arrayElement(sendingFacilities);
    const receivingApp = faker.helpers.arrayElement(receivingApps);
    const receivingFacility = faker.helpers.arrayElement(receivingFacilities);
    return `// MDM^T02: Document Notification
${[
        `MSH|^~\\&|${sendingApp}|${sendingFacility}|${receivingApp}|${receivingFacility}|${hl7Date(now)}||MDM^T02^MDM_T01|MSG${faker.string.numeric(7)}|P|2.5.1`,
        `PID|1||${person.mrn}||${person.lastName}^${person.firstName}`,
        `TXA|1|${faker.string.numeric(10)}|DS|${hl7Date(now)}`,
        `OBX|1|ED|12345^ConsultNote^L||^TEXT^Base64^${documentContent}`
    ].join('\r')}
`;
};

const createORM_O01 = () => {
    const now = new Date();
    // --- FIX: Create a future date for scheduling ---
    const scheduledDateTime = new Date(now.getTime() + faker.number.int({ min: 1, max: 24 }) * 60 * 60 * 1000); // 1 to 24 hours in the future

    const person = createPerson();
    const orderingProvider = createPhysician();
    const referringDoctor = createPhysician();
    const technician = createPhysician();
    const exam = faker.helpers.arrayElement(radiologyExams);

    const placerOrderNum = { id: faker.string.numeric(8), namespace: 'ORD_APP' };
    const fillerOrderNum = { id: faker.string.numeric(8), namespace: 'RAD_SYS' }; // This is the Accession Number
    const placerGroupNum = { id: `GRP${faker.string.numeric(5)}`, namespace: 'ORD_APP' };
    const visitNum = `V${faker.string.numeric(7)}`;
    const accountNum = `ACCT${faker.string.numeric(5)}`;

    const sendingApp = faker.helpers.arrayElement(sendingApps);
    const sendingFacility = faker.helpers.arrayElement(sendingFacilities);
    const receivingApp = faker.helpers.arrayElement(receivingApps);
    const receivingFacility = faker.helpers.arrayElement(receivingFacilities);

    const msh = [
        'MSH', '^~\\&', sendingApp, sendingFacility, receivingApp, receivingFacility, hl7Date(now), '', 'ORM^O01^ORM_O01', `MSG${faker.string.numeric(7)}`, 'P', '2.5.1', '', '', 'AL', 'AL', 'USA', 'UNICODE UTF-8'
    ].join('|');

    const pid = [
        'PID', '1', '', `${person.mrn}^^^${sendingFacility}^MR`, '', `${person.lastName}^${person.firstName}^${person.middleInitial}`, '', person.dob, person.sex, '', '2106-3^White^CDCREC', `${person.address.street}^^${person.address.city}^${person.address.state}^${person.address.zip}^USA^H`, '', `(555)${faker.string.numeric(7)}`, '', 'en', 'M^Married', '', accountNum
    ].join('|');

    const pv1 = [
        'PV1', '1', 'O', 'RAD^R101^1^RADIOLOGY', 'R', '', '', `${referringDoctor.id}^${referringDoctor.lastName}^${referringDoctor.firstName}`, `${orderingProvider.id}^${orderingProvider.lastName}^${orderingProvider.firstName}`, '', 'RAD', '', '', 'R', '', '', 'A0', '', '', visitNum
    ].join('|');

    const orc = [
        'ORC',
        'NW', // ORC-1: Order Control
        `${placerOrderNum.id}^${placerOrderNum.namespace}`, // ORC-2: Placer Order Number
        `${fillerOrderNum.id}^${fillerOrderNum.namespace}`, // ORC-3: Filler Order Number
        `${placerGroupNum.id}^${placerGroupNum.namespace}`, // ORC-4: Placer Group Number
        'SC', // ORC-5: Order Status
        '', // ORC-6: Response Flag
        `1^^^${hl7Date(scheduledDateTime)}^S`, // ORC-7: Quantity/Timing with Start Date in TQ.4
        '', // ORC-8: Parent
        hl7Date(now), // ORC-9: Date/Time of Transaction
        `U${faker.string.numeric(4)}^USER^TEST`, // ORC-10: Entered By
        '', // ORC-11: Verified By
        `${orderingProvider.id}^${orderingProvider.lastName}^${orderingProvider.firstName}`, // ORC-12: Ordering Provider
        'UROLOGY_CLINIC^C1', // ORC-13: Enterer's Location
        `(555)${faker.string.numeric(7)}`, // ORC-14: Call Back Phone Number
        hl7Date(scheduledDateTime) // ORC-15: Order Effective Date/Time
    ].join('|');

    const obr = [
        // --- FIX: Use the future scheduledDateTime in OBR-7 ---
        'OBR', '1', `${placerOrderNum.id}^${placerOrderNum.namespace}`, `${fillerOrderNum.id}^${fillerOrderNum.namespace}`, `${exam.code}^${exam.name}^C4`, 'S', hl7Date(scheduledDateTime), '', '', '', `${technician.id}^${technician.lastName}^${technician.firstName}`, 'O', 'INFECT^Infectious Material', 'Patient c/o shortness of breath.', '', '', `${orderingProvider.id}^${orderingProvider.lastName}^${orderingProvider.firstName}`, '', '', '', 'Scheduled AE Title: CHEST_MOD', '', '', '', exam.modality, 'S'
    ].join('|');

    const zds = [
        'ZDS', '1', `1.2.840.10008.5.1.4.1.1.2.${faker.string.numeric(10)}.${faker.string.numeric(3)}.${person.mrn}.${fillerOrderNum.id}`, `${exam.modality}_MOD^1.2.3.4.5.6.7^AETITLE`, 'WHEELCHAIR'
    ].join('|');

    return `// ORM^O01: General Order Message (New Order)
${[msh, pid, pv1, orc, obr, zds].join('\r')}
`;
};

const createORM_O01_Cancel = () => {
    const now = new Date();
    const person = createPerson();
    const orderingProvider = createPhysician();
    const referringDoctor = createPhysician();

    // These numbers should match the order being cancelled
    const placerOrderNum = { id: faker.string.numeric(8), namespace: 'ORD_APP' };
    const fillerOrderNum = { id: faker.string.numeric(8), namespace: 'RAD_SYS' };

    const sendingApp = faker.helpers.arrayElement(sendingApps);
    const sendingFacility = faker.helpers.arrayElement(sendingFacilities);
    const receivingApp = faker.helpers.arrayElement(receivingApps);
    const receivingFacility = faker.helpers.arrayElement(receivingFacilities);

    const msh = [
        'MSH', '^~\\&', sendingApp, sendingFacility, receivingApp, receivingFacility, hl7Date(now), '', 'ORM^O01^ORM_O01', `MSG${faker.string.numeric(7)}`, 'P', '2.5.1'
    ].join('|');

    const pid = [
        'PID', '1', '', `${person.mrn}^^^${sendingFacility}^MR`, '', `${person.lastName}^${person.firstName}^${person.middleInitial}`, '', person.dob, person.sex
    ].join('|');

    const pv1 = [
        'PV1', '1', 'O', 'RAD^R101^1^RADIOLOGY', '', '', '', `${referringDoctor.id}^${referringDoctor.lastName}^${referringDoctor.firstName}`, `${orderingProvider.id}^${orderingProvider.lastName}^${orderingProvider.firstName}`
    ].join('|');

    const orc = [
        'ORC', 'CA', `${placerOrderNum.id}^${placerOrderNum.namespace}`, `${fillerOrderNum.id}^${fillerOrderNum.namespace}`, '', 'CA', '', '', hl7Date(now), `U${faker.string.numeric(4)}^USER^TEST`, '', `${orderingProvider.id}^${orderingProvider.lastName}^${orderingProvider.firstName}`, '', '', '', 'DUP^Duplicate Order Created in Error^HL70459'
    ].join('|');

    return `// ORM^O01: General Order Message (Cancel Order)
${[msh, pid, pv1, orc].join('\r')}
`;
};


export const fakerTemplates = [
    { id: 'faker-adt', name: 'ADT-A01 (Admission)', messageType: 'ADT', generator: createADT_A01, isStatic: true },
    { id: 'faker-oru', name: 'ORU-R01 (Lab Result)', messageType: 'ORU', generator: createORU_R01, isStatic: true },
    { id: 'faker-siu', name: 'SIU-S12 (Appointment)', messageType: 'SIU', generator: createSIU_S12, isStatic: true },
    { id: 'faker-orm-new', name: 'ORM-O01 (New Radiology Order)', messageType: 'ORM', generator: createORM_O01, isStatic: true },
    { id: 'faker-orm-cancel', name: 'ORM-O01 (Cancel Order)', messageType: 'ORM', generator: createORM_O01_Cancel, isStatic: true },
    { id: 'faker-mdm', name: 'MDM-T02 (Doc Notification)', messageType: 'MDM', generator: createMDM_T02, isStatic: true },
];