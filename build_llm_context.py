#!/usr/bin/env python3
"""
Script: build_llm_context.py
Purpose: Build a context file for LLMs to understand the full scope of the HL7 Yeeter project.

- Lists all project files (excluding cache, node_modules, etc)
- Provides a prompt for LLMs describing the project
- Concatenates critical backend and frontend files
- Outputs a single .txt file for upload
"""
import os
import fnmatch

# Directories to scan
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '.'))
OUTPUT_FILE = os.path.join(BASE_DIR, 'llm_project_context.txt')

# Ignore patterns
IGNORE_PATTERNS = [
    'node_modules', 'db-data', 'old_segment_dictionary', 'static', '__pycache__', '*.pyc', '*.pyo', '*.pyd', '*.egg-info', 'dist', 'build', '.eggs', '*.egg', '*.log', '*.sqlite3', '*.db', '.env', '.venv', 'venv', 'ENV', 'env', 'npm-debug.log*', '*old-segment-dictionary*', '.git', '.gitignore', '*.tgz', 'llm_project_context.txt'
]

# --- THIS IS THE MEAT OF THE UPDATE ---
# These are the files that define the simulator and its dependencies.
CRITICAL_BACKEND = [
    'app/models.py',                    # The single source of truth for our database schema.
    'app/schemas.py',                   # The Pydantic schemas defining our API contracts.
    'app/crud.py',                      # The database interaction layer.
    'app/__init__.py',                  # The app factory, shows how all blueprints are wired.
    'app/routes/simulator_routes.py',   # The API endpoints for the simulator.
    'app/routes/endpoint_routes.py',    # The API for managing MLLP/DICOM destinations.
    'app/util/simulation_runner.py',    # The absolute heart of the engine.
    'app/util/faker_parser.py',         # The brains of the dynamic HL7 generation.
    'app/util/dicom_generator.py',      # Logic for creating DICOM files.
    'app/util/dicom_actions.py',        # Logic for sending DICOM (C-STORE, and soon, MPPS).
]

CRITICAL_FRONTEND = [
    'src/components/HL7Parser.jsx',             # The main component, our tabbed shell.
    'src/components/Simulator.jsx',             # The container for all simulator UI.
    'src/components/SimulationWorkflowManager.jsx', # The UI for building workflow recipes.
    'src/components/SimulationStepEditor.jsx',  # The UI for editing a single workflow step.
    'src/components/SimulationRunDashboard.jsx',# The UI for launching and monitoring runs.
    'src/components/SimulationRunLog.jsx',      # The real-time log viewer.
    'src/components/EndpointManager.jsx',       # The admin UI for managing destinations.
    'src/api/simulator.js',                     # The API client for the simulator backend.
    'src/api/endpoints.js',                     # The API client for the endpoint backend.
]
# --- END OF UPDATE ---

PROMPT = """
You are an expert in HL7, DICOM, Python, and modern web development (Flask/React). You are being provided with the full context of the HL7 Yeeter project. This project is a hybrid backend/frontend system for simulating, generating, and transmitting HL7 and DICOM messages, with a focus on healthcare interoperability and workflow automation. The backend is primarily Python (Flask, SQLAlchemy, Pydantic), and the frontend is a Vite/React app. The system supports simulation runs, patient context generation, HL7 message generation, MLLP transmission, DICOM file creation and C-STORE, and event logging. Please use the following file list and critical code to understand the architecture, data models, and main workflows.
"""

def should_ignore(path):
    # Make ignore relative to project root for sub-directories
    rel_path = os.path.relpath(path, PROJECT_ROOT)
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(os.path.basename(rel_path), pattern) or fnmatch.fnmatch(rel_path, pattern):
            return True
    return False

def list_files(root):
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Filter dirnames in-place to prevent descending into them
        dirnames[:] = [d for d in dirnames if not should_ignore(os.path.join(dirpath, d))]
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if not should_ignore(file_path):
                file_list.append(os.path.relpath(file_path, root))
    return sorted(file_list)

def concat_files(file_paths):
    contents = []
    for rel_path in file_paths:
        abs_path = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    contents.append(f"\n--- START OF FILE {rel_path} ---\n\n" + f.read() + f"\n\n--- END OF FILE {rel_path} ---\n")
            except Exception as e:
                contents.append(f"\n--- FAILED TO READ {rel_path}: {e} ---\n")
    return '\n'.join(contents)

def main():
    print("Building LLM context file...")
    file_list = list_files(PROJECT_ROOT)
    print(f"Found {len(file_list)} project files.")
    
    critical_files = CRITICAL_BACKEND + CRITICAL_FRONTEND
    print(f"Concatenating {len(critical_files)} critical files...")
    critical_code = concat_files(critical_files)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out:
        out.write(PROMPT + '\n\n')
        out.write('--- PROJECT FILE LIST ---\n')
        for f in file_list:
            out.write(f + '\n')
        out.write('\n--- CRITICAL FILES CONTENT ---\n')
        out.write(critical_code)
    
    print(f"LLM context file written to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()