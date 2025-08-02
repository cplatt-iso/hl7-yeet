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
from .dicom_actions import perform_c_store, perform_dmwl_find, perform_mpps_action

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
    'DMWL_FIND': 'handle_dmwl_find',
    'MPPS_UPDATE': 'handle_mpps_update',
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
            
            # Emit to client room
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
            }, to=f'run-{self.run_id}')
            logging.info(f"[SimRun-{self.run_id}] Patient {patient_iter}, Step {step_order}, Repeat {repeat_iter}: {status} - {details}")
            
    def _emit_status_update(self, status: str):
        """Emits a general status update for the run."""
        socketio.emit('sim_run_status_update', {'run_id': self.run_id, 'status': status}, to=f'run-{self.run_id}')
        logging.info(f"Emitted status update for Run {self.run_id}: {status}")

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
                self._emit_status_update(run.status)
                
                patient_count = run.patient_count or 1
                self._log_event(0, 0, 0, 'INFO', f"Simulation run starting for template '{run.template.name}' with {patient_count} patient iteration(s).")
            
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

            with self.app_context():
                run = crud.get_simulation_run_by_id(db, self.run_id) # Re-fetch to be safe
                if run:
                    run.status = 'COMPLETED'
                    db.session.commit()
                    self._emit_status_update(run.status)
            self._log_event(999, patient_count, 1, 'SUCCESS', "Simulation run completed successfully.")

        except Exception as e:
            logging.error(f"SimulationRun-{self.run_id} failed: {e}", exc_info=True)
            with self.app_context():
                run = crud.get_simulation_run_by_id(db, self.run_id)
                if run:
                    run.status = 'ERROR'
                    db.session.commit()
                    self._emit_status_update(run.status)
            self._log_event(999, 0, 0, 'FAILURE', f"Critical error: {e}")
        
        finally:
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
        
        accession_extracted = False
        try:
            clean_message = generated_message.replace('\n', '\r').strip()
            msg = parse_message(clean_message)

            msh = getattr(msg, 'MSH', None)
            is_orm = msh and hasattr(msh, 'msh_9') and msh.msh_9.message_code.value == 'ORM'

            if is_orm:
                self.run_context.setdefault('order', {})
                
                # --- THIS IS THE FIX: Access segments through the ORDER group ---
                order_groups = getattr(msg, 'ORM_O01_ORDER', [])
                if not order_groups:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "Message is ORM but has no ORDER group.")
                else:
                    first_order_group = order_groups[0]
                    orc_segment = getattr(first_order_group, 'ORC', None)
                    obr_segment = getattr(first_order_group, 'OBR', None)

                    if orc_segment:
                        try:
                            acc = str(orc_segment.orc_3.entity_identifier.value)
                            if acc and acc.strip():
                                self.run_context['order']['accession_number'] = acc
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Accession: '{acc}'")
                                accession_extracted = True
                        except (AttributeError, TypeError):
                            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "Could not extract Accession from ORC-3.")
                    else:
                        self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "ORDER group found, but it has no ORC segment.")

                    if obr_segment:
                        try:
                            modality = str(obr_segment.obr_24.value)
                            if modality and modality.strip():
                                self.run_context['order']['modality'] = modality
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Modality: '{modality}'")
                        except (AttributeError, TypeError):
                            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Modality (OBR-24) not found.")

                        try:
                            desc = str(obr_segment.obr_4.text.value)
                            if desc and desc.strip():
                                self.run_context['order']['study_description'] = desc
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Study Desc: '{desc}'")
                        except (AttributeError, TypeError):
                            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Study Description (OBR-4) not found.")
        
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"HL7 parsing failed: {e}")

        if accession_extracted:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {gen_template.message_type} message and extracted context.")
        else:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {gen_template.message_type}, but FAILED to extract a valid Accession Number.")

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
        order_context = self.run_context.get('order', {})

        overrides = {
            "PatientName": f"{self.run_context['patient']['last_name']}^{self.run_context['patient']['first_name']}",
            "PatientID": self.run_context['patient']['mrn'],
            "PatientBirthDate": self.run_context['patient']['dob'],
            "PatientSex": self.run_context['patient']['sex'],
            "AccessionNumber": order_context.get('accession_number', f'ACC{self.faker.random_number(digits=8)}'),
            "Modality": order_context.get('modality') or params.get('modality', 'CT'),
            "StudyDescription": order_context.get('study_description') or params.get('study_description', 'Generated Study'),
        }

        file_paths = create_study_files(
            output_dir=output_dir,
            num_images=params.get('count', 10),
            overrides=overrides,
            generate_pixels=params.get('generate_pixels', True)
        )
        
        self.run_context['last_dicom_files'] = file_paths
        self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {len(file_paths)} DICOM files using modality '{overrides['Modality']}'.")
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

    def handle_dmwl_find(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: DMWL_FIND")
        endpoint_id = step.parameters.get('endpoint_id')
        accession = self.run_context.get('order', {}).get('accession_number')
        if not endpoint_id or not accession:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', "DMWL_FIND requires an endpoint and an accession number in context.")
            return False
            
        with self.app_context():
            endpoint = crud.get_endpoint_by_id(db, endpoint_id)
            if not endpoint or endpoint.endpoint_type != 'DICOM_SCP':
                raise ValueError(f"Endpoint ID {endpoint_id} is not a valid DICOM_SCP endpoint.")

        try:
            query_params = {"AccessionNumber": accession, "ScheduledProcedureStepStatus": ""}
            results = perform_dmwl_find(endpoint.to_dict(), query_params)
            if len(results) == 1:
                self.run_context['worklist_item'] = results[0]
                self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Found 1 worklist item for accession '{accession}'.")
                return True
            else:
                details = f"Expected 1 worklist item for accession '{accession}', but found {len(results)}."
                self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', details)
                return False
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', f"DMWL C-FIND query failed: {e}")
            return False

    def handle_mpps_update(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: MPPS_UPDATE")
        endpoint_id = step.parameters.get('endpoint_id')
        mpps_status = step.parameters.get('mpps_status')
        worklist_item = self.run_context.get('worklist_item')

        if not endpoint_id or not mpps_status or not worklist_item:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', "MPPS_UPDATE requires an endpoint, status, and a worklist item in context.")
            return False

        with self.app_context():
            endpoint = crud.get_endpoint_by_id(db, endpoint_id)
            if not endpoint or endpoint.endpoint_type != 'DICOM_SCP':
                raise ValueError(f"Endpoint ID {endpoint_id} is not a valid DICOM_SCP endpoint.")
        
        mpps_uid_from_context = self.run_context.get('mpps_sop_instance_uid') if mpps_status != "IN PROGRESS" else None

        try:
            result = perform_mpps_action(endpoint.to_dict(), worklist_item, mpps_status, mpps_uid_from_context)
            if result['status'] == 'SUCCESS':
                if mpps_status == 'IN PROGRESS':
                    self.run_context['mpps_sop_instance_uid'] = result['mpps_uid']
                self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"MPPS {mpps_status} action successful. {result['details']}")
                return True
            else:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', f"MPPS {mpps_status} action failed. {result['details']}")
                return False
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', f"MPPS action threw an exception: {e}")
            return False

def run_simulation_task(run_id, app_context):
    """The entry point for the background task."""
    logging.info(f"Starting background simulation task for Run ID: {run_id}")
    runner = SimulationRunner(run_id, app_context)
    runner.execute()
    logging.info(f"Background simulation task for Run ID: {run_id} has finished.")
# --- END OF FILE app/util/simulation_runner.py ---