# --- START OF FILE app/util/simulation_runner.py ---

import time
import logging
import socket
from datetime import datetime
from faker import Faker
from hl7apy.parser import parse_message

from ..extensions import db, socketio
from .. import crud, models
from .faker_parser import process_faker_string
from .dicom_generator import create_study_files
from .dicom_actions import perform_c_store

# MLLP Constants
VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'

# Step Dispatcher: A map of step_type to the function that handles it.
STEP_HANDLERS = {
    'GENERATE_HL7': 'handle_generate_hl7',
    'GENERATE_DICOM': 'handle_generate_dicom',
    'SEND_MLLP': 'handle_send_mllp',
    'SEND_DICOM': 'handle_send_dicom',
    'WAIT': 'handle_wait',
}

class SimulationRunner:
    def __init__(self, run_id: int, app_context):
        self.run_id = run_id
        self.app_context = app_context
        self.run_context = {}  # This holds the state for a single patient workflow
        self.faker = Faker()

    def _log_event(self, step_order: int, patient_iter: int, repeat_iter: int, status: str, details: str):
        """Helper to log events to the database and emit them via socket."""
        with self.app_context():
            # Persist to DB
            event = models.SimulationRunEvent(
                run_id=self.run_id,
                step_order=step_order,
                iteration=patient_iter,
                status=status.upper(),
                details=details
            )
            db.session.add(event)
            db.session.commit()
            
            # Emit to client
            socketio.emit('sim_log_update', {
                'run_id': self.run_id,
                'event': {
                    'id': event.id,
                    'timestamp': event.timestamp.isoformat(),
                    'step_order': step_order,
                    'iteration': patient_iter,
                    'status': status.upper(),
                    'details': details
                }
            })
            logging.info(f"[SimRun-{self.run_id}] Patient {patient_iter}, Step {step_order}, Repeat {repeat_iter}: {status} - {details}")

    def _get_or_create_patient(self, patient_iter: int):
        """Ensures a patient exists in the context for the current iteration."""
        if 'patient' not in self.run_context:
            self._log_event(0, patient_iter, 0, 'INFO', "New patient context created for this iteration.")
            self.run_context['patient'] = {
                "last_name": self.faker.last_name().upper(),
                "first_name": self.faker.first_name().upper(),
                "mrn": str(self.faker.random_number(digits=8, fix_len=True)),
                "dob": self.faker.date_of_birth(minimum_age=1, maximum_age=90).strftime('%Y%m%d'),
                "sex": self.faker.random_element(elements=('M', 'F', 'O')),
            }

    def execute(self):
        """The main execution method for the entire simulation run."""
        run = None # Define run outside the try block
        try:
            with self.app_context():
                run = crud.get_simulation_run_by_id(db, self.run_id)
                if not run:
                    logging.error(f"FATAL: SimulationRun with ID {self.run_id} not found.")
                    return

                run.status = 'RUNNING'
                run.started_at = datetime.utcnow()
                db.session.commit()
                
                patient_count = run.patient_count or 1
                self._log_event(0, 0, 0, 'INFO', f"Simulation run starting for template '{run.template.name}' with {patient_count} patient iteration(s).")
            
            # --- THE REST OF THE TRY BLOCK IS THE SAME ---
            for i in range(1, patient_count + 1):
                self.run_context = {} 
                self._log_event(0, i, 0, 'INFO', f"--- Starting Iteration {i} of {patient_count} ---")
                
                for step in run.template.steps:
                    repeat_count = step.parameters.get('repeat', {}).get('count', 1)
                    delay_ms = step.parameters.get('repeat', {}).get('delay_ms', 0)

                    for j in range(1, repeat_count + 1):
                        handler_name = STEP_HANDLERS.get(step.step_type)
                        if not handler_name:
                            raise NotImplementedError(f"No handler for step type '{step.step_type}'")
                        
                        handler_func = getattr(self, handler_name)
                        success = handler_func(step, patient_iter=i, repeat_iter=j)
                        
                        if not success:
                            raise Exception(f"Step {step.step_order} failed on repeat {j}. Halting workflow.")
                        
                        if j < repeat_count and delay_ms > 0:
                            self._log_event(step.step_order, i, j, 'INFO', f"Delaying for {delay_ms}ms...")
                            time.sleep(delay_ms / 1000.0)

            # This code will only be reached if the try block completes without error
            with self.app_context():
                run = crud.get_simulation_run_by_id(db, self.run_id) # Re-fetch to be safe
                if run:
                    run.status = 'COMPLETED'
                    db.session.commit()
            self._log_event(999, patient_count, 1, 'SUCCESS', "Simulation run completed successfully.")

        except Exception as e:
            logging.error(f"SimulationRun-{self.run_id} failed: {e}", exc_info=True)
            # THIS IS THE CRITICAL PART. UPDATE THE STATUS *INSIDE* THE EXCEPT BLOCK
            with self.app_context():
                run = crud.get_simulation_run_by_id(db, self.run_id)
                if run:
                    run.status = 'ERROR'
                    db.session.commit()
            self._log_event(999, 0, 0, 'FAILURE', f"Critical error: {e}")
        
        finally:
            # --- THE FINAL, GUARANTEED UPDATE ---
            with self.app_context():
                run = crud.get_simulation_run_by_id(db, self.run_id)
                if run:
                    run.completed_at = datetime.utcnow()
                    db.session.commit()
                    logging.info(f"Final status for Run ID {self.run_id} is '{run.status}'.")

    # --- STEP HANDLER IMPLEMENTATIONS ---
    
    def handle_generate_hl7(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: GENERATE_HL7")
        self._get_or_create_patient(patient_iter)

        template_id = step.parameters.get('generator_template_id')
        if not template_id:
            raise ValueError("GENERATE_HL7 step is missing 'generator_template_id' parameter.")
        
        with self.app_context():
            gen_template = crud.get_generator_template_by_id(db, template_id)
            if not gen_template:
                raise FileNotFoundError(f"GeneratorTemplate with ID {template_id} not found.")

        generated_message = process_faker_string(gen_template.content, self.run_context)
        self.run_context['last_hl7_message'] = generated_message
        
        # --- THIS IS THE NEW LOGGING LINE ---
        logging.info(f"--- Generated HL7 for Context Extraction ---\n{generated_message}\n--------------------------------------------")

        # --- Context Extraction Example (Optional) ---
        try:
            # hl7apy expects \r, not \n. Let's be sure.
            # Also, some parsers are picky about trailing newlines.
            clean_message = generated_message.replace('\n', '\r').strip()
            msg = parse_message(clean_message)

            # Try to extract useful context, but don't fail if it doesn't work
            try:
                # hl7apy has dynamic attributes that pylance can't analyze
                if msg.msh.msh_9.message_code.value == 'ORM':  # type: ignore
                    # Use the correct method to get ORC segment - hl7apy uses callable syntax
                    orc_segment = msg('ORC')  # type: ignore
                    if orc_segment and orc_segment.orc_3.placer_group_number:  # type: ignore
                        accession = orc_segment.orc_3.placer_group_number.value  # type: ignore
                        if accession:
                            self.run_context.setdefault('order', {})['accession_number'] = accession
                            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Accession Number '{accession}' into context.")
            except Exception:
                # Context extraction failed, but that's OK - just continue without it
                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Context extraction skipped - message structure not as expected.")

        except Exception as e:
            # Even if parsing fails completely, we should continue - context extraction is optional
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"HL7 parsing for context extraction failed: {e}")

        self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {gen_template.message_type} message.")
        return True


    def handle_send_mllp(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: SEND_MLLP")
        
        message_to_send = self.run_context.get('last_hl7_message')
        if not message_to_send:
             raise ValueError("SEND_MLLP step called but no 'last_hl7_message' in context.")
             
        endpoint_id = step.parameters.get('endpoint_id')
        if not endpoint_id:
            raise ValueError("SEND_MLLP step is missing 'endpoint_id' parameter.")
            
        with self.app_context():
            endpoint = crud.get_endpoint_by_id(db, endpoint_id)
            if not endpoint or endpoint.endpoint_type != 'MLLP':
                raise ValueError(f"Endpoint ID {endpoint_id} is not a valid MLLP endpoint.")
        
        mllp_message = VT + message_to_send.encode('utf-8') + FS + CR
        ack_message = "ERROR: No response"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((endpoint.hostname, endpoint.port))
                s.sendall(mllp_message)
                ack_buffer = s.recv(4096)
                if ack_buffer:
                    start_idx = ack_buffer.find(VT) + 1 if VT in ack_buffer else 0
                    end_idx = ack_buffer.find(FS) if FS in ack_buffer else len(ack_buffer)
                    ack_message = ack_buffer[start_idx:end_idx].decode('utf-8', errors='ignore').strip()
            self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Sent HL7 to '{endpoint.name}'. ACK received:\n{ack_message}")
            return True
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', f"Failed to send HL7 to '{endpoint.name}': {e}")
            return False

    def handle_generate_dicom(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: GENERATE_DICOM")
        self._get_or_create_patient(patient_iter)

        params = step.parameters
        output_dir = f"/data/sim_runs/{self.run_id}/patient_{patient_iter}"

        overrides = {
            "PatientName": f"{self.run_context['patient']['last_name']}^{self.run_context['patient']['first_name']}",
            "PatientID": self.run_context['patient']['mrn'],
            "PatientBirthDate": self.run_context['patient']['dob'],
            "PatientSex": self.run_context['patient']['sex'],
            "AccessionNumber": self.run_context.get('order', {}).get('accession_number', f'ACC{self.faker.random_number(digits=8)}'),
            "Modality": params.get('modality', 'CT'),
            "StudyDescription": params.get('study_description', 'Generated Study'),
        }

        file_paths = create_study_files(
            output_dir=output_dir,
            num_images=params.get('count', 10),
            overrides=overrides,
            generate_pixels=params.get('generate_pixels', True)
        )
        
        self.run_context['last_dicom_files'] = file_paths
        self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {len(file_paths)} DICOM files.")
        return True
        
    def handle_send_dicom(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: SEND_DICOM (C-STORE)")
        
        file_paths = self.run_context.get('last_dicom_files')
        if not file_paths:
            raise ValueError("SEND_DICOM step called but no 'last_dicom_files' in context.")
        
        endpoint_id = step.parameters.get('endpoint_id')
        if not endpoint_id:
            raise ValueError("SEND_DICOM step is missing 'endpoint_id' parameter.")
        
        with self.app_context():
            endpoint = crud.get_endpoint_by_id(db, endpoint_id)
            if not endpoint or endpoint.endpoint_type != 'DICOM_SCP':
                raise ValueError(f"Endpoint ID {endpoint_id} is not a valid DICOM_SCP endpoint.")
        
        results = perform_c_store(file_paths, endpoint.to_dict())

        success_count = len(results.get('success', []))
        failure_count = len(results.get('failure', []))
        
        if failure_count > 0:
            details = f"C-STORE to '{endpoint.name}' partially failed. Success: {success_count}, Failure: {failure_count}."
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', details)
            return False
        else:
            details = f"C-STORE of {success_count} instances to '{endpoint.name}' successful."
            self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', details)
            return True

    def handle_wait(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        duration_s = step.parameters.get('duration_seconds', 1)
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Executing step: WAIT for {duration_s} seconds.")
        time.sleep(duration_s)
        self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', "Wait completed.")
        return True


def run_simulation_task(run_id, app_context):
    """The entry point for the background task."""
    logging.info(f"Starting background simulation task for Run ID: {run_id}")
    runner = SimulationRunner(run_id, app_context)
    runner.execute()
    logging.info(f"Background simulation task for Run ID: {run_id} has finished.")

# --- END OF FILE app/util/simulation_runner.py ---