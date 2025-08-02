// --- START OF FILE src/components/SimulationStepEditor.jsx ---
import React from 'react';
import { TrashIcon, ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/outline';

const SimulationStepEditor = ({ step, index, onUpdate, onDelete, onMove, isFirst, isLast, generatorTemplates, endpoints }) => {
    
    const handleParamChange = (e) => {
        const { name, value, type, checked } = e.target;
        const newParams = {
            ...step.parameters,
            [name]: type === 'checkbox' ? checked : (type === 'number' ? parseInt(value, 10) : value)
        };
        onUpdate(index, { ...step, parameters: newParams });
    };
    
    const handleTypeChange = (e) => {
        // When type changes, reset parameters to avoid carrying over old settings
        onUpdate(index, { ...step, step_type: e.target.value, parameters: {} });
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
                            <input type="text" name="modality" value={step.parameters.modality || 'CT'} onChange={handleParamChange} className="bg-gray-700 p-2 rounded border border-gray-600" />
                        </div>
                        <div className="flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Image Count</label>
                            <input type="number" name="count" value={step.parameters.count || 10} onChange={handleParamChange} className="bg-gray-700 p-2 rounded border border-gray-600" />
                        </div>
                        <div className="col-span-2 flex flex-col gap-2">
                            <label className="text-xs text-gray-400">Study Description</label>
                            <input type="text" name="study_description" value={step.parameters.study_description || ''} onChange={handleParamChange} placeholder="e.g., CT CHEST W/O CONTRAST" className="bg-gray-700 p-2 rounded border border-gray-600" />
                        </div>
                         <p className="text-xs text-gray-500 col-span-2">Note: Modality and Study Description will be overridden by values from HL7 ORM context if available.</p>
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
                        <input type="number" name="duration_seconds" value={step.parameters.duration_seconds || 1} onChange={handleParamChange} className="bg-gray-700 p-2 rounded border border-gray-600" />
                    </div>
                );
            default:
                return <p className="text-gray-500">Select a step type to configure parameters.</p>;
        }
    };

    return (
        <div className="bg-gray-800/50 p-4 rounded-lg border border-gray-700 flex gap-4">
            <div className="flex flex-col items-center gap-2 text-gray-400">
                <span className="font-bold text-lg">{index + 1}</span>
                <button onClick={() => onMove(index, 'up')} disabled={isFirst} className="disabled:opacity-20"><ArrowUpIcon className="h-5 w-5"/></button>
                <button onClick={() => onMove(index, 'down')} disabled={isLast} className="disabled:opacity-20"><ArrowDownIcon className="h-5 w-5"/></button>
            </div>
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
                    <button onClick={() => onDelete(index)} className="mt-5 p-2 text-red-400 hover:bg-gray-700 rounded"><TrashIcon className="h-5 w-5"/></button>
                </div>
                <div>
                    <h5 className="font-semibold text-sm mb-2 text-gray-300">Parameters</h5>
                    <div className="p-3 bg-gray-900/50 rounded-md min-h-[5rem]">
                        {renderParameters()}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SimulationStepEditor;
// --- END OF FILE src/components/SimulationStepEditor.jsx ---