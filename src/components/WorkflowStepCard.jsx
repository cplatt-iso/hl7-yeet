// --- REPLACE src/components/WorkflowStepCard.jsx ---
import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { getStepIO } from '../utils/workflowAnalyzer'; // <-- IMPORT THE ANALYZER
import {
    DocumentTextIcon, CubeIcon, PaperAirplaneIcon, ClockIcon,
    ArrowRightCircleIcon, CogIcon, TrashIcon, PencilIcon, Bars3Icon,
    ArrowDownTrayIcon, ArrowUpTrayIcon
} from '@heroicons/react/24/outline';

// ... (getStepInfo function remains the same as the Phase 1 fix) ...
const getStepInfo = (step, generatorTemplates, endpoints) => {
    const defaultInfo = {
        icon: CogIcon,
        color: 'gray',
        title: 'Unknown Step',
        summary: 'Not configured'
    };

    switch (step.step_type) {
        case 'GENERATE_HL7': {
            const template = generatorTemplates.find(t => t.id === step.parameters.generator_template_id);
            return { icon: DocumentTextIcon, color: 'green', title: 'Generate HL7', summary: template ? template.name : 'No template selected' };
        }
        case 'SEND_MLLP': {
            const endpoint = endpoints.find(e => e.id === step.parameters.endpoint_id);
            return { icon: PaperAirplaneIcon, color: 'green', title: 'Send HL7 (MLLP)', summary: `To: ${endpoint ? endpoint.name : 'N/A'}` };
        }
        case 'DMWL_FIND': {
            const endpoint = endpoints.find(e => e.id === step.parameters.endpoint_id);
            return { icon: ArrowRightCircleIcon, color: 'indigo', title: 'Query Worklist', summary: `At: ${endpoint ? endpoint.name : 'N/A'}` };
        }
        case 'MPPS_UPDATE': {
            const endpoint = endpoints.find(e => e.id === step.parameters.endpoint_id);
            return { icon: CogIcon, color: 'indigo', title: 'Update MPPS', summary: `${step.parameters.mpps_status || '...'} at ${endpoint ? endpoint.name : 'N/A'}` };
        }
        case 'GENERATE_DICOM': {
            const count = step.parameters.count ?? 10;
            const modalityText = step.parameters.modality || '(From Context)';
            const pixelText = (step.parameters.generate_pixels ?? true) ? "with pixels" : "headers only";
            return { icon: CubeIcon, color: 'purple', title: 'Generate DICOM', summary: `${count} ${modalityText} images, ${pixelText}` };
        }
        case 'SEND_DICOM': {
            const endpoint = endpoints.find(e => e.id === step.parameters.endpoint_id);
            return { icon: PaperAirplaneIcon, color: 'purple', title: 'Send DICOM', summary: `To: ${endpoint ? endpoint.name : 'N/A'}` };
        }
        case 'WAIT':
            return { icon: ClockIcon, color: 'gray', title: 'Wait', summary: `${step.parameters.duration_seconds || 0} seconds` };
        default:
            return defaultInfo;
    }
};


const ContextBadge = ({ type, label }) => {
    const isInput = type === 'input';
    const color = isInput ? 'bg-sky-900/50 text-sky-300' : 'bg-amber-900/50 text-amber-300';
    const Icon = isInput ? ArrowDownTrayIcon : ArrowUpTrayIcon;

    return (
        <span className={`flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
            <Icon className="h-3 w-3" />
            {label}
        </span>
    );
};

const WorkflowStepCard = ({ step, index, onEdit, onDelete, generatorTemplates, endpoints }) => {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 10 : 'auto',
        opacity: isDragging ? 0.8 : 1,
    };

    const { icon: Icon, color, title, summary } = getStepInfo(step, generatorTemplates, endpoints);
    const { inputs, outputs } = getStepIO(step, generatorTemplates); // <-- GET IO DATA

    const colorClasses = {
        green: 'border-green-600/50 hover:border-green-500',
        purple: 'border-purple-600/50 hover:border-purple-500',
        indigo: 'border-indigo-600/50 hover:border-indigo-500',
        gray: 'border-gray-600/50 hover:border-gray-500',
    };

    return (
        <div ref={setNodeRef} style={style} className={`bg-gray-800/80 rounded-lg border p-3 flex flex-col gap-2 shadow-md ${colorClasses[color]}`}>
            <div className="flex items-center gap-4 w-full">
                <div {...attributes} {...listeners} className="cursor-grab p-2 text-gray-500 hover:text-white">
                    <Bars3Icon className="h-6 w-6" />
                </div>
                <div className="flex-shrink-0">
                    <Icon className={`h-8 w-8 text-${color}-400`} />
                </div>
                <div className="flex-grow">
                    <p className="font-bold text-white">{index + 1}. {title}</p>
                    <p className="text-sm text-gray-400">{summary}</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={() => onEdit(index)} className="p-2 text-gray-400 hover:text-indigo-400 rounded-full hover:bg-gray-700">
                        <PencilIcon className="h-5 w-5" />
                    </button>
                    <button onClick={() => onDelete(index)} className="p-2 text-gray-400 hover:text-red-400 rounded-full hover:bg-gray-700">
                        <TrashIcon className="h-5 w-5" />
                    </button>
                </div>
            </div>
            {/* --- NEW BADGE SECTION --- */}
            {(inputs.length > 0 || outputs.length > 0) && (
                 <div className="pl-12 flex items-center gap-2 flex-wrap">
                    {inputs.map(label => <ContextBadge key={label} type="input" label={label} />)}
                    {outputs.map(label => <ContextBadge key={label} type="output" label={label} />)}
                 </div>
            )}
        </div>
    );
};

export default WorkflowStepCard;