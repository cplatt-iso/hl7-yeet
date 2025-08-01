// --- START OF FILE src/components/Simulator.jsx ---
import React, { useState } from 'react';

import GeneratorTemplateManager from './GeneratorTemplateManager';
import SimulationWorkflowManager from './SimulationWorkflowManager';
import SimulationRunDashboard from './SimulationRunDashboard'; // <-- IMPORT IT

const Simulator = () => {
    const [activeSubTab, setActiveSubTab] = useState('workflows');

    const SubTabButton = ({ name, label }) => (
        <button
            onClick={() => setActiveSubTab(name)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeSubTab === name 
                ? 'bg-indigo-600 text-white' 
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
        >
            {label}
        </button>
    );

    return (
        <div className="p-6 bg-gray-800 rounded-lg shadow-xl">
            <h2 className="text-2xl font-bold mb-4 text-white">Clinical Workflow Simulator</h2>
            <div className="flex items-center gap-4 mb-6 border-b border-gray-700 pb-4">
                <SubTabButton name="workflows" label="Workflow Templates" />
                <SubTabButton name="runs" label="Run Dashboard" />
                <SubTabButton name="generators" label="HL7 Generators" />
            </div>

            <div>
                {activeSubTab === 'workflows' && <SimulationWorkflowManager />}
                {activeSubTab === 'runs' && <SimulationRunDashboard />} {/* <-- RENDER IT */}
                {activeSubTab === 'generators' && <GeneratorTemplateManager />}
            </div>
        </div>
    );
};

export default Simulator;
// --- END OF FILE: src/components/Simulator.jsx ---