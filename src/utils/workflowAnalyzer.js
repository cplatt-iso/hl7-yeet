// --- CREATE NEW FILE: src/utils/workflowAnalyzer.js ---
const STEP_IO_METADATA = {
    GENERATE_HL7: {
        outputs: (step, generatorTemplates) => {
            const template = generatorTemplates.find(t => t.id === step.parameters.generator_template_id);
            // Only ORM messages produce order context
            if (template && template.message_type.startsWith('ORM')) {
                return ['Order Context'];
            }
            return [];
        }
    },
    DMWL_FIND: {
        inputs: ['Order Context'],
        outputs: ['Worklist Item']
    },
    MPPS_UPDATE: {
        inputs: ['Worklist Item', 'Order Context'], // Accept either
        outputs: (step) => (step.parameters.mpps_status === 'IN PROGRESS' ? ['MPPS UID'] : [])
    },
    GENERATE_DICOM: {
        inputs: ['Order Context', 'Worklist Item'],
    },
    SEND_DICOM: {
        // This step consumes the DICOM files, but that's an implicit context we don't need to show
        inputs: [],
    },
};

export const getStepIO = (step, generatorTemplates) => {
    const metadata = STEP_IO_METADATA[step.step_type];
    if (!metadata) {
        return { inputs: [], outputs: [] };
    }

    const inputs = typeof metadata.inputs === 'function' 
        ? metadata.inputs(step, generatorTemplates) 
        : metadata.inputs || [];
        
    const outputs = typeof metadata.outputs === 'function' 
        ? metadata.outputs(step, generatorTemplates) 
        : metadata.outputs || [];

    return { inputs, outputs };
};

export const validateWorkflow = (steps, generatorTemplates) => {
    const warnings = [];
    const availableContext = new Set();
    
    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        const { inputs, outputs } = getStepIO(step, generatorTemplates);
        
        // Check if MPPS_UPDATE has sufficient context
        if (step.step_type === 'MPPS_UPDATE') {
            const hasWorklistItem = availableContext.has('Worklist Item');
            const hasOrderContext = availableContext.has('Order Context');
            
            if (!hasWorklistItem && !hasOrderContext) {
                warnings.push({
                    stepIndex: i,
                    type: 'error',
                    message: 'MPPS_UPDATE requires either a Worklist Item (from DMWL_FIND) or Order Context (from GENERATE_HL7)'
                });
            } else if (!hasWorklistItem && hasOrderContext) {
                warnings.push({
                    stepIndex: i,
                    type: 'warning',
                    message: 'MPPS_UPDATE is using HL7 order context. Consider adding DMWL_FIND for IHE compliance.'
                });
            }
        }
        
        // Add outputs to available context
        outputs.forEach(output => availableContext.add(output));
    }
    
    return warnings;
};