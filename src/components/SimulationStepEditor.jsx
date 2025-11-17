// --- REPLACE src/components/SimulationStepEditor.jsx ---
import React, { useEffect, useState } from 'react';
import { InformationCircleIcon } from '@heroicons/react/24/outline';

const STEP_GUIDANCE = {
    GENERATE_HL7: {
        title: 'Generates order context',
        body: 'Select an HL7 generator template. The resulting ORM message seeds patient, procedure, and accession values used by downstream DICOM steps. Choose which HL7 field should be treated as the accession number and optionally queue the order for asynchronous workers.'
    },
    SEND_MLLP: {
        title: 'Sends HL7 message via MLLP',
        body: 'Pick the destination MLLP endpoint. The message produced earlier in the run is delivered as-is. Use this to feed RIS/PACS systems once context is ready.'
    },
    DMWL_FIND: {
        title: 'Queries the modality worklist',
        body: 'Executes a C-FIND using the accession number from context. Store the returned worklist item so later steps can populate DICOM headers and MPPS.'
    },
    MPPS_UPDATE: {
        title: 'Updates Modality Performed Procedure Step',
        body: 'Send MPPS status transitions to the selected endpoint. IN PROGRESS issues an N-CREATE and yields a Procedure Step UID for subsequent COMPLETED or DISCONTINUED updates.'
    },
    GENERATE_DICOM: {
        title: 'Builds synthetic DICOM series',
        body: 'Creates images using context from HL7 or worklist results. Leave modality or description blank to auto-populate. Toggle pixel generation, burn-in, or structured report output as needed.'
    },
    SEND_DICOM: {
        title: 'Sends generated DICOM files',
        body: 'Push the study generated earlier to a DICOM Storage SCP. Make sure GENERATE_DICOM ran first so files are available.'
    },
    WAIT: {
        title: 'Pauses the workflow',
        body: 'Delay execution for the given number of seconds. Helpful when waiting for external systems to ingest prior steps.'
    }
};

const StepGuidanceCallout = ({ stepType }) => {
    if (!stepType || !STEP_GUIDANCE[stepType]) {
        return null;
    }

    const { title, body } = STEP_GUIDANCE[stepType];
    return (
        <div className="mb-3 flex items-start gap-3 rounded-md border border-sky-700/60 bg-sky-900/20 p-3 text-sky-100">
            <InformationCircleIcon className="mt-0.5 h-5 w-5 flex-shrink-0 text-sky-300" aria-hidden="true" />
            <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-sky-200">{title}</p>
                <p className="mt-1 text-xs leading-relaxed text-sky-100/90">{body}</p>
            </div>
        </div>
    );
};

const SimulationStepEditor = ({ step, index, onUpdate, generatorTemplates, endpoints }) => {
    const [metadataDraft, setMetadataDraft] = useState('');
    const [metadataError, setMetadataError] = useState(null);

    useEffect(() => {
        const metadata = step.parameters?.queue_metadata;
        if (metadata && Object.keys(metadata).length > 0) {
            setMetadataDraft(JSON.stringify(metadata, null, 2));
        } else {
            setMetadataDraft('');
        }
        setMetadataError(null);
    }, [step.parameters?.queue_metadata]);

    const updateParameters = (mutator) => {
        const current = step.parameters || {};
        const nextParams = typeof mutator === 'function' ? mutator(current) : mutator;
        onUpdate(index, { ...step, parameters: nextParams });
    };

    const handleParamChange = (e) => {
        const { name, value, type, checked } = e.target;

        let finalValue;
        if (name === 'generator_template_id' || name === 'endpoint_id') {
            const parsed = parseInt(value, 10);
            finalValue = isNaN(parsed) ? '' : parsed;
        } else if (type === 'number') {
            const parsed = parseInt(value, 10);
            finalValue = isNaN(parsed) ? 0 : parsed;
        } else if (type === 'checkbox') {
            finalValue = checked;
        } else {
            finalValue = value;
        }
        
        updateParameters(prev => {
            const next = {
                ...prev,
                [name]: finalValue
            };

            if (name === 'queue_async' && !finalValue) {
                delete next.queue_name;
                delete next.queue_retry_limit;
                delete next.queue_retry_delay_ms;
                delete next.queue_metadata;
            }

            return next;
        });
    };

    const handleMetadataBlur = () => {
        if (!step.parameters.queue_async) {
            return;
        }

        if (!metadataDraft.trim()) {
            setMetadataError(null);
            updateParameters(prev => {
                const next = { ...prev };
                delete next.queue_metadata;
                return next;
            });
            return;
        }

        try {
            const parsed = JSON.parse(metadataDraft);
            if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
                throw new Error('Metadata must be a JSON object.');
            }
            setMetadataError(null);
            updateParameters(prev => ({
                ...prev,
                queue_metadata: parsed
            }));
        } catch (err) {
            setMetadataError(err.message || 'Invalid JSON.');
        }
    };
    
    const handleTypeChange = (e) => {
        const newType = e.target.value;
        let defaultParams = {};

        switch (newType) {
            case 'GENERATE_DICOM':
                // Set blank defaults to encourage using context
                defaultParams = { count: 10, modality: '', study_description: '', generate_pixels: true, burn_patient_info: false, generate_report: false };
                break;
            case 'WAIT':
                defaultParams = { duration_seconds: 5 };
                break;
            case 'MPPS_UPDATE':
                defaultParams = { mpps_status: 'IN PROGRESS' };
                break;
            default:
                defaultParams = {};
                break;
        }
        
        onUpdate(index, { ...step, step_type: newType, parameters: defaultParams });
    };

    const renderParameters = () => {
        switch (step.step_type) {
            case 'GENERATE_HL7':
                return (
                    <div className="flex flex-col gap-2">
                        <label className="text-xs text-gray-400">HL7 Generator Template</label>
                        <select
                            name="generator_template_id"
                            value={step.parameters.generator_template_id || ''}
                            onChange={handleParamChange}
                            className="bg-gray-700 p-2 rounded border border-gray-600"
                        >
                            <option value="">-- Select a Generator --</option>
                            {generatorTemplates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                        
                        <label className="text-xs text-gray-400 mt-3">Accession Number Field</label>
                        <div className="flex flex-col gap-1">
                            <select
                                name="accession_field"
                                value={step.parameters.accession_field || 'OBR.3'}
                                onChange={handleParamChange}
                                className="bg-gray-700 p-2 rounded border border-gray-600"
                            >
                                <option value="OBR.3">OBR-3 (Filler Order Number) - Standard</option>
                                <option value="OBR.2">OBR-2 (Placer Order Number)</option>
                                <option value="ORC.3">ORC-3 (Filler Order Number)</option>
                                <option value="ORC.2">ORC-2 (Placer Order Number)</option>
                                <option value="CUSTOM">Custom Field...</option>
                            </select>
                            {step.parameters.accession_field === 'CUSTOM' && (
                                <input
                                    type="text"
                                    name="custom_accession_field"
                                    value={step.parameters.custom_accession_field || ''}
                                    onChange={handleParamChange}
                                    placeholder="e.g., MSH.10, PID.2"
                                    className="bg-gray-700 p-2 rounded border border-gray-600 text-sm"
                                />
                            )}
                            <p className="text-xs text-gray-500">Choose which HL7 field contains the accession number for DMWL queries</p>
                        </div>

                        <div className="mt-4 rounded-md border border-indigo-700/40 bg-indigo-950/20 p-3">
                            <div className="flex items-center justify-between">
                                <label htmlFor={`queue-async-${index}`} className="text-sm font-medium text-indigo-200">
                                    Queue order for async workers
                                </label>
                                <input
                                    id={`queue-async-${index}`}
                                    type="checkbox"
                                    name="queue_async"
                                    checked={step.parameters.queue_async ?? false}
                                    onChange={handleParamChange}
                                    className="h-4 w-4 border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-400"
                                />
                            </div>
                            <p className="mt-1 text-xs text-indigo-100/80">
                                When enabled the run publishes this order to RabbitMQ and waits for worker pods to finish the remaining steps.
                            </p>

                            {step.parameters.queue_async && (
                                <div className="mt-3 grid grid-cols-1 gap-3">
                                    <div className="grid gap-1">
                                        <label className="text-xs text-indigo-100">Order Queue Override (optional)</label>
                                        <input
                                            type="text"
                                            name="queue_name"
                                            value={step.parameters.queue_name || ''}
                                            onChange={handleParamChange}
                                            placeholder="Defaults to yeeter.simulation.orders"
                                            className="w-full rounded border border-indigo-800/60 bg-gray-900/70 p-2 text-sm text-gray-200 placeholder:text-gray-500"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <label className="flex flex-col gap-1 text-xs text-indigo-100">
                                            Max Attempts
                                            <input
                                                type="number"
                                                name="queue_retry_limit"
                                                value={step.parameters.queue_retry_limit ?? ''}
                                                min="1"
                                                onChange={handleParamChange}
                                                className="rounded border border-indigo-800/60 bg-gray-900/70 p-2 text-sm text-gray-200"
                                                placeholder="3"
                                            />
                                        </label>
                                        <label className="flex flex-col gap-1 text-xs text-indigo-100">
                                            Retry Delay (ms)
                                            <input
                                                type="number"
                                                name="queue_retry_delay_ms"
                                                value={step.parameters.queue_retry_delay_ms ?? ''}
                                                min="0"
                                                onChange={handleParamChange}
                                                className="rounded border border-indigo-800/60 bg-gray-900/70 p-2 text-sm text-gray-200"
                                                placeholder="5000"
                                            />
                                        </label>
                                    </div>
                                    <div className="grid gap-1">
                                        <label className="text-xs text-indigo-100">Metadata (JSON object, optional)</label>
                                        <textarea
                                            rows={4}
                                            value={metadataDraft}
                                            onChange={(e) => setMetadataDraft(e.target.value)}
                                            onBlur={handleMetadataBlur}
                                            placeholder='e.g. {"priority": "STAT"}'
                                            className="w-full rounded border border-indigo-800/60 bg-gray-900/70 p-2 text-sm text-gray-200 placeholder:text-gray-500"
                                        />
                                        {metadataError && (
                                            <span className="text-xs text-red-300">{metadataError}</span>
                                        )}
                                        {!metadataError && metadataDraft && (
                                            <span className="text-xs text-indigo-200/80">Saved when the field loses focus.</span>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                );
            case 'SEND_MLLP':
                 return (
                    <div className="flex flex-col gap-2">
                        <label className="text-xs text-gray-400">Destination MLLP Endpoint</label>
                        <select
                            name="endpoint_id"
                            value={step.parameters.endpoint_id || ''}
                            onChange={handleParamChange}
                            className="bg-gray-700 p-2 rounded border border-gray-600"
                        >
                            <option value="">-- Select an Endpoint --</option>
                            {endpoints.filter(e => e.endpoint_type === 'MLLP').map(ep => <option key={ep.id} value={ep.id}>{ep.name}</option>)}
                        </select>
                    </div>
                );
            case 'DMWL_FIND':
                return (
                    <div className="flex flex-col gap-2">
                        <label className="text-xs text-gray-400">Query Target (DICOM SCP)</label>
                        <select
                            name="endpoint_id"
                            value={step.parameters.endpoint_id || ''}
                            onChange={handleParamChange}
                            className="bg-gray-700 p-2 rounded border border-gray-600"
                        >
                            <option value="">-- Select an Endpoint --</option>
                            {endpoints.filter(e => e.endpoint_type === 'DICOM_SCP').map(ep => <option key={ep.id} value={ep.id}>{ep.name}</option>)}
                        </select>
                         <p className="text-xs text-gray-500 mt-1">Queries using the Accession Number from the current context.</p>
                    </div>
                );
            case 'MPPS_UPDATE':
                 return (
                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Destination (DICOM SCP)</label>
                            <select
                                name="endpoint_id"
                                value={step.parameters.endpoint_id || ''}
                                onChange={handleParamChange}
                                className="bg-gray-700 p-2 rounded border border-gray-600"
                            >
                                <option value="">-- Select --</option>
                                {endpoints.filter(e => e.endpoint_type === 'DICOM_SCP').map(ep => <option key={ep.id} value={ep.id}>{ep.name}</option>)}
                            </select>
                        </div>
                        <div className="flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Set Status To</label>
                             <select
                                name="mpps_status"
                                value={step.parameters.mpps_status || ''}
                                onChange={handleParamChange}
                                className="bg-gray-700 p-2 rounded border border-gray-600"
                            >
                                <option value="">-- Select Status --</option>
                                <option value="IN PROGRESS">IN PROGRESS (N-CREATE)</option>
                                <option value="COMPLETED">COMPLETED (N-SET)</option>
                                <option value="DISCONTINUED">DISCONTINUED (N-SET)</option>
                            </select>
                        </div>
                    </div>
                );
            case 'GENERATE_DICOM':
                return (
                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Modality</label>
                            <input type="text" name="modality" value={step.parameters.modality || ''} onChange={handleParamChange} placeholder="(Uses context if blank)" className="bg-gray-700 p-2 rounded border border-gray-600 placeholder:text-gray-500" />
                        </div>
                        <div className="flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Image Count</label>
                            <input type="number" name="count" value={step.parameters.count ?? 10} onChange={handleParamChange} className="bg-gray-700 p-2 rounded border border-gray-600" />
                        </div>
                        <div className="col-span-2 flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Study Description</label>
                            <input type="text" name="study_description" value={step.parameters.study_description || ''} onChange={handleParamChange} placeholder="(Uses context if blank)" className="bg-gray-700 p-2 rounded border border-gray-600 placeholder:text-gray-500" />
                        </div>
                        {/* --- PIXEL GENERATION CHECKBOX --- */}
                        <div className="col-span-2 flex items-center gap-2 mt-2">
                             <input 
                                type="checkbox" 
                                id={`gen-pixels-${index}`}
                                name="generate_pixels"
                                checked={step.parameters.generate_pixels ?? true}
                                onChange={handleParamChange}
                                className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label htmlFor={`gen-pixels-${index}`} className="text-sm text-gray-300">Generate realistic pixel data</label>
                        </div>
                        
                        {/* --- PATIENT INFO BURNING CHECKBOX --- */}
                        <div className="col-span-2 flex items-center gap-2">
                             <input 
                                type="checkbox" 
                                id={`burn-patient-${index}`}
                                name="burn_patient_info"
                                checked={step.parameters.burn_patient_info ?? false}
                                onChange={handleParamChange}
                                className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label htmlFor={`burn-patient-${index}`} className="text-sm text-gray-300">Burn patient information into images</label>
                        </div>
                        
                        {/* --- GENERATE REPORT CHECKBOX --- */}
                        <div className="col-span-2 flex items-center gap-2">
                             <input 
                                type="checkbox" 
                                id={`gen-report-${index}`}
                                name="generate_report"
                                checked={step.parameters.generate_report ?? false}
                                onChange={handleParamChange}
                                className="h-4 w-4 rounded bg-gray-700 border-gray-600 text-indigo-600 focus:ring-indigo-500"
                            />
                            <label htmlFor={`gen-report-${index}`} className="text-sm text-gray-300">Generate SR (Structured Report) with modality-appropriate findings</label>
                        </div>
                        
                         <p className="text-xs text-gray-500 col-span-2">Values from an HL7 Order or DMWL query will be used if fields are left blank.</p>
                    </div>
                );
            case 'SEND_DICOM':
                 return (
                    <div className="flex flex-col gap-2">
                        <label className="text-xs text-gray-400">Destination DICOM SCP</label>
                        <select
                            name="endpoint_id"
                            value={step.parameters.endpoint_id || ''}
                            onChange={handleParamChange}
                            className="bg-gray-700 p-2 rounded border border-gray-600"
                        >
                            <option value="">-- Select an Endpoint --</option>
                            {endpoints.filter(e => e.endpoint_type === 'DICOM_SCP').map(ep => <option key={ep.id} value={ep.id}>{ep.name}</option>)}
                        </select>
                    </div>
                );
            case 'WAIT':
                return (
                    <div className="flex flex-col gap-2">
                        <label className="text-xs text-gray-400">Duration (seconds)</label>
                        <input type="number" name="duration_seconds" value={step.parameters.duration_seconds || 5} onChange={handleParamChange} className="bg-gray-700 p-2 rounded border border-gray-600" />
                    </div>
                );
            default:
                return null;
        }
    };

    const parametersContent = renderParameters();

    return (
        <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700 flex gap-4">
             <div className="flex-grow space-y-4">
                <div className="flex gap-4 items-start">
                    <div className="flex-grow">
                        <label className="text-xs text-gray-400">Step Type</label>
                        <select value={step.step_type} onChange={handleTypeChange} className="w-full bg-gray-700 p-2 rounded border border-gray-600">
                            <option value="">-- Select Type --</option>
                            <optgroup label="HL7">
                                <option value="GENERATE_HL7">Generate HL7 Message</option>
                                <option value="SEND_MLLP">Send HL7 (MLLP)</option>
                            </optgroup>
                            <optgroup label="DICOM">
                                <option value="DMWL_FIND">Query Modality Worklist (DMWL)</option>
                                <option value="MPPS_UPDATE">Update Procedure Step (MPPS)</option>
                                <option value="GENERATE_DICOM">Generate DICOM Series</option>
                                <option value="SEND_DICOM">Send DICOM (C-STORE)</option>
                            </optgroup>
                            <optgroup label="Utility">
                                <option value="WAIT">Wait</option>
                            </optgroup>
                        </select>
                    </div>
                </div>
                <div>
                    <h5 className="font-semibold text-sm mb-2 text-gray-300">Parameters</h5>
                    <div className="p-3 bg-gray-900/50 rounded-md min-h-[5rem]">
                        {step.step_type ? (
                            <>
                                <StepGuidanceCallout stepType={step.step_type} />
                                {parametersContent || <p className="text-gray-500">No parameters required for this step.</p>}
                            </>
                        ) : (
                            <p className="text-gray-500">Select a step type to configure parameters.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SimulationStepEditor;