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
            patient_details = ", ".join([f"{key}: {value}" for key, value in self.run_context['patient'].items()])
            self._log_event(0, patient_iter, 0, 'INFO', f"Patient Context: {patient_details}")

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
        
        # Get accession number field configuration from step parameters
        accession_field = step.parameters.get('accession_field', 'OBR.3')  # Default to OBR-3
        
        accession_extracted = False
        try:
            clean_message = generated_message.replace('\n', '\r').strip()
            msg = parse_message(clean_message)

            msh = getattr(msg, 'MSH', None)
            is_orm = msh and hasattr(msh, 'msh_9') and msh.msh_9.message_code.value == 'ORM'

            if is_orm:
                self.run_context.setdefault('order', {})
                
                # Extract accession number based on configured field
                accession_extracted = self._extract_accession_from_field(msg, accession_field, step, patient_iter, repeat_iter)
                
                order_groups = getattr(msg, 'ORM_O01_ORDER', [])
                if not order_groups:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "No ORDER groups found in ORM message.")
                else:
                    # Extract other order context (modality, study description, etc.)
                    self._extract_order_context(order_groups[0], step, patient_iter, repeat_iter)

        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"HL7 parsing failed: {e}")

        if accession_extracted:
            acc_in_context = self.run_context.get('order', {}).get('accession_number', 'NOT_FOUND')
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Accession in context after extraction: '{acc_in_context}'")
            self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {gen_template.message_type} message and extracted context.")
        else:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Generated {gen_template.message_type}, but FAILED to extract a valid Accession Number.")

        return True


    def handle_send_mllp(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: SEND_MLLP")
        
        message_to_send = self.run_context.get('last_hl7_message')
        if not message_to_send:
             raise ValueError("SEND_MLLP step called but no 'last_hl7_message' in context.")
        
        # Fix: Ensure consistent line endings - MLLP expects \r as segment separators
        message_normalized = message_to_send.replace('\n', '\r').replace('\r\r', '\r').strip()
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Sending HL7 message:\n{message_normalized}")
             
        endpoint_id = step.parameters.get('endpoint_id')
        if not endpoint_id:
            raise ValueError("SEND_MLLP step is missing 'endpoint_id' parameter.")
            
        with self.app_context():
            endpoint = crud.get_endpoint_by_id(db, endpoint_id)
            if not endpoint or endpoint.endpoint_type != 'MLLP':
                raise ValueError(f"Endpoint ID {endpoint_id} is not a valid MLLP endpoint.")
    
        # Use normalized message for MLLP framing
        mllp_message = VT + message_normalized.encode('utf-8') + FS + CR
        
        # Debug: Log the exact bytes being sent
        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"MLLP frame length: {len(mllp_message)} bytes")
        
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
            
            # Check for rejection codes
            if "AE" in ack_message or "AR" in ack_message or "AccessionNumber Missing" in ack_message:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', f"HL7 to '{endpoint.name}' was rejected. ACK:\n{ack_message}")
                return False
            else:
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
        
        user_modality = params.get('modality', '').strip()
        worklist_item = self.run_context.get('worklist_item')
        order_context = self.run_context.get('order', {})
        
        final_modality = ''
        if user_modality:
            final_modality = user_modality
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using Modality ('{final_modality}') from user-defined step parameter.")
        elif worklist_item and hasattr(worklist_item, 'ScheduledProcedureStepSequence') and worklist_item.ScheduledProcedureStepSequence[0].Modality:
            final_modality = worklist_item.ScheduledProcedureStepSequence[0].Modality
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using Modality ('{final_modality}') from DMWL context.")
        elif order_context.get('modality'):
            final_modality = order_context['modality']
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using Modality ('{final_modality}') from HL7 Order context.")
        
        if not final_modality:
            # Enhanced fallback logic - try to infer modality from study description if available
            fallback_modality = None
            order_context = self.run_context.get('order', {})
            study_desc = order_context.get('study_description', '')
            
            if study_desc:
                fallback_modality = self._infer_modality_from_description(study_desc, step, patient_iter, repeat_iter)
                if fallback_modality:
                    final_modality = fallback_modality
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using fallback modality '{final_modality}' inferred from study description.")
            
            if not final_modality:
                # Enhanced fallback with variety - use weighted random selection
                # Based on real-world medical imaging frequency
                modality_weights = [
                    ('DX', 35),    # Digital Radiography - most common
                    ('CT', 25),    # CT scans - very common  
                    ('MR', 20),    # MRI - common for soft tissue
                    ('US', 10),    # Ultrasound - common and portable
                    ('CR', 5),     # Computed Radiography - older but still used
                    ('NM', 3),     # Nuclear Medicine - specialized
                    ('MG', 2),     # Mammography - specialized
                ]
                
                # Create weighted list
                weighted_modalities = []
                for modality, weight in modality_weights:
                    weighted_modalities.extend([modality] * weight)
                
                # Use deterministic randomness based on run_id and patient iteration for consistency
                import random
                random.seed(self.run_id * 1000 + patient_iter)  # Deterministic but varies per patient
                final_modality = random.choice(weighted_modalities)
                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"No modality found in any context. Using randomly selected modality '{final_modality}' for variety.")
                
                # Generate appropriate study description based on selected modality
                modality_descriptions = {
                    'DX': ['Chest X-Ray PA/LAT', 'Abdomen X-Ray', 'Spine X-Ray AP/LAT', 'Extremity X-Ray', 'Pelvis X-Ray AP'],
                    'CT': ['CT Chest W/O Contrast', 'CT Abdomen/Pelvis W Contrast', 'CT Head W/O Contrast', 'CT Spine W/O Contrast', 'CT Neck W Contrast'],
                    'MR': ['MRI Brain W/O Contrast', 'MRI Lumbar Spine W/O Contrast', 'MRI Knee W/O Contrast', 'MRI Shoulder W/O Contrast', 'MRI Cervical Spine W/O Contrast'],
                    'US': ['Ultrasound Abdomen Complete', 'Ultrasound Pelvis', 'Ultrasound Carotid Duplex', 'Echocardiogram', 'Ultrasound Renal'],
                    'CR': ['CR Chest PA', 'CR Abdomen Supine', 'CR Pelvis AP', 'CR Spine Lateral'],
                    'NM': ['Nuclear Medicine Bone Scan', 'Nuclear Medicine Cardiac Stress', 'Nuclear Medicine Thyroid Scan', 'Nuclear Medicine Lung Scan'],
                    'MG': ['Mammogram Bilateral Screening', 'Mammogram Diagnostic Bilateral', 'Mammogram Bilateral Diagnostic'],
                }
                
                # If no study description exists, generate one that matches the modality
                if not order_context.get('study_description'):
                    suggested_desc = random.choice(modality_descriptions.get(final_modality, ['Generated Study']))
                    self.run_context.setdefault('order', {})['study_description'] = suggested_desc
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Generated matching study description: '{suggested_desc}'")

        user_desc = params.get('study_description', '').strip()
        final_desc = ''
        if user_desc:
            final_desc = user_desc
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using Study Description ('{final_desc}') from user-defined step parameter.")
        elif worklist_item and hasattr(worklist_item, 'RequestedProcedureDescription') and worklist_item.RequestedProcedureDescription:
            final_desc = worklist_item.RequestedProcedureDescription
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using Study Description ('{final_desc}') from DMWL context.")
        elif order_context.get('study_description'):
            final_desc = order_context['study_description']
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Using Study Description ('{final_desc}') from HL7 Order context.")
        else:
            # Try to generate a more specific description based on the modality
            if final_modality in ['DX', 'CR']:
                final_desc = f"{final_modality} Chest PA/LAT"
            elif final_modality == 'CT':
                final_desc = f"CT Chest W/O Contrast"
            elif final_modality == 'MR':
                final_desc = f"MRI Brain W/O Contrast"
            elif final_modality == 'US':
                final_desc = f"Ultrasound Abdomen Complete"
            elif final_modality == 'NM':
                final_desc = f"Nuclear Medicine Bone Scan"
            elif final_modality == 'MG':
                final_desc = f"Mammogram Bilateral Screening"
            else:
                final_desc = f"Generated {final_modality} Study"
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Study Description not found in context; using modality-specific default: '{final_desc}'.")


        # Infer body part from study description for better DICOM generation
        from .dicom_generator import _infer_body_part_from_description
        inferred_body_part = _infer_body_part_from_description(final_desc)
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Inferred body part for DICOM generation: '{inferred_body_part}' from description: '{final_desc}'")

        overrides = {
            "PatientName": f"{self.run_context['patient']['last_name']}^{self.run_context['patient']['first_name']}",
            "PatientID": self.run_context['patient']['mrn'],
            "PatientBirthDate": self.run_context['patient']['dob'],
            "PatientSex": self.run_context['patient']['sex'],
            "AccessionNumber": order_context.get('accession_number', f'ACC{self.faker.random_number(digits=8)}'),
            "Modality": final_modality,
            "StudyDescription": final_desc,
            "BodyPartExamined": inferred_body_part,
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
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Performing DMWL query with params: {query_params}")
            results = perform_dmwl_find(endpoint.to_dict(), query_params)
            
            # Log summary of response data
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"DMWL query returned {len(results)} result(s).")
            
            if len(results) == 1:
                self.run_context['worklist_item'] = results[0]
                self._log_event(step.step_order, patient_iter, repeat_iter, 'SUCCESS', f"Found 1 worklist item for accession '{accession}'.")
                return True
            else:
                failure_msg = f"Expected 1 worklist item for accession '{accession}', but found {len(results)}."
                self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', failure_msg)
                # Log the details of what was found to help debugging
                if results:
                    details = "Found items:\n"
                    for i, ds in enumerate(results):
                        patient_name = ds.get("PatientName", "N/A")
                        accession_num = ds.get("AccessionNumber", "N/A")
                        sps_seq = ds.get("ScheduledProcedureStepSequence", [])
                        modality = sps_seq[0].get("Modality", "N/A") if sps_seq else "N/A"
                        sps_id = sps_seq[0].get("ScheduledProcedureStepID", "N/A") if sps_seq else "N/A"
                        details += f"  {i+1}: Patient: {patient_name}, Accession: {accession_num}, Modality: {modality}, SPS ID: {sps_id}\n"
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', details.rstrip())
                return False
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', f"DMWL C-FIND query failed: {e}")
            return False

    def handle_mpps_update(self, step: models.SimulationStep, patient_iter: int, repeat_iter: int) -> bool:
        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Executing step: MPPS_UPDATE")
        endpoint_id = step.parameters.get('endpoint_id')
        mpps_status = step.parameters.get('mpps_status')
        worklist_item = self.run_context.get('worklist_item')
        order_context = self.run_context.get('order', {})
        patient_context = self.run_context.get('patient', {})

        if not endpoint_id or not mpps_status:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', "MPPS_UPDATE requires an endpoint and status.")
            return False

        # Check if we have sufficient context for MPPS
        if not worklist_item:
            # Try to use HL7 order context instead
            if not order_context.get('accession_number') or not patient_context.get('mrn'):
                self._log_event(step.step_order, patient_iter, repeat_iter, 'FAILURE', "MPPS_UPDATE requires either a worklist item OR sufficient order context (accession number + patient info).")
                return False
            else:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Using HL7 order context for MPPS (no worklist item available).")
        else:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', "Using DMWL worklist item for MPPS.")

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

    # --- HELPER METHODS FOR CONFIGURABLE ACCESSION EXTRACTION ---
    
    def _extract_accession_from_field(self, msg, accession_field: str, step, patient_iter: int, repeat_iter: int) -> bool:
        """
        Extract accession number from a specified HL7 field.
        
        Args:
            msg: Parsed HL7 message
            accession_field: Field specification like 'OBR.3', 'OBR.2', 'ORC.3', 'ORC.2', 'CUSTOM', or custom
            step: The simulation step
            patient_iter: Patient iteration number
            repeat_iter: Repeat iteration number
            
        Returns:
            bool: True if accession was successfully extracted, False otherwise
        """
        accession_field = accession_field.upper().strip()
        
        # Handle CUSTOM field type
        if accession_field == 'CUSTOM':
            custom_field = step.parameters.get('custom_accession_field', '').strip()
            if not custom_field:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "Custom accession field specified but custom_accession_field parameter is empty")
                return False
            accession_field = custom_field.upper().strip()
        
        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Extracting accession from field: {accession_field}")
        
        # Get order groups
        order_groups = getattr(msg, 'ORM_O01_ORDER', [])
        if not order_groups:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "No ORDER groups found in message")
            return False
            
        first_order_group = order_groups[0]
        
        # Handle predefined field mappings
        if accession_field in ['OBR.2', 'OBR.3']:
            return self._extract_from_obr_field(first_order_group, accession_field, step, patient_iter, repeat_iter)
        elif accession_field in ['ORC.2', 'ORC.3']:
            return self._extract_from_orc_field(first_order_group, accession_field, step, patient_iter, repeat_iter)
        else:
            # Handle custom field specification
            return self._extract_from_custom_field(msg, accession_field, step, patient_iter, repeat_iter)
    
    def _extract_from_obr_field(self, order_group, field_spec: str, step, patient_iter: int, repeat_iter: int) -> bool:
        """Extract accession from OBR field (OBR.2 or OBR.3)"""
        # Try to get OBR from the order detail group first
        obr_segment = None
        order_detail = getattr(order_group, 'ORM_O01_ORDER_DETAIL', None)
        if order_detail:
            obr_segment = getattr(order_detail, 'OBR', None)
        else:
            # Fallback: try to get OBR directly from the order group
            obr_segment = getattr(order_group, 'OBR', None)
            
        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"OBR segment found: {obr_segment is not None}")
        
        if not obr_segment:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"No OBR segment found for {field_spec}")
            return False
            
        try:
            # Debug: Show the raw OBR segment
            obr_str = str(obr_segment)
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"OBR segment content: {obr_str}")
            
            # Parse using string method for reliability
            obr_fields = obr_str.split('|')
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"OBR has {len(obr_fields)} fields")
            
            field_index = 2 if field_spec == 'OBR.2' else 3  # OBR.2 = index 2, OBR.3 = index 3
            
            if len(obr_fields) > field_index and obr_fields[field_index].strip():
                full_field = obr_fields[field_index]
                self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"{field_spec} raw content: '{full_field}'")
                
                # Extract the ID part before any ^ component separator
                acc_candidate = full_field.split('^')[0].strip()
                if acc_candidate and not acc_candidate.isspace():
                    self.run_context['order']['accession_number'] = acc_candidate
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Accession from {field_spec}: '{acc_candidate}'")
                    return True
                    
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"No valid accession found in {field_spec}")
            return False
            
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Error extracting from {field_spec}: {e}")
            return False
    
    def _extract_from_orc_field(self, order_group, field_spec: str, step, patient_iter: int, repeat_iter: int) -> bool:
        """Extract accession from ORC field (ORC.2 or ORC.3)"""
        orc_segment = getattr(order_group, 'ORC', None)
        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"ORC segment found: {orc_segment is not None}")
        
        if not orc_segment:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"No ORC segment found for {field_spec}")
            return False
            
        try:
            # Debug: Show the raw ORC segment
            orc_str = str(orc_segment)
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"ORC segment content: {orc_str}")
            
            # Handle case where ORC segment is wrapped in a list representation
            if orc_str.startswith('[<Segment ORC>]') or '<Segment ORC>' in orc_str:
                # Try to get the actual segment content using HL7apy methods
                try:
                    # Try to access the segment content directly
                    if hasattr(orc_segment, 'to_er7'):
                        orc_str = orc_segment.to_er7()
                    elif hasattr(orc_segment, 'value'):
                        orc_str = str(orc_segment.value)
                    else:
                        # Fallback: reconstruct from the original message
                        original_msg = self.run_context.get('last_hl7_message', '')
                        orc_lines = [line for line in original_msg.split('\r') if line.startswith('ORC|')]
                        if orc_lines:
                            orc_str = orc_lines[0]
                        else:
                            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Could not extract ORC content from segment object")
                            return False
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"ORC segment extracted content: {orc_str}")
                except Exception as inner_e:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Failed to extract ORC content: {inner_e}")
                    return False
            
            # Parse using string method for reliability
            orc_fields = orc_str.split('|')
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"ORC has {len(orc_fields)} fields")
            
            field_index = 2 if field_spec == 'ORC.2' else 3  # ORC.2 = index 2, ORC.3 = index 3
            
            if len(orc_fields) > field_index and orc_fields[field_index].strip():
                full_field = orc_fields[field_index]
                self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"{field_spec} raw content: '{full_field}'")
                
                # Extract the ID part before any ^ component separator
                acc_candidate = full_field.split('^')[0].strip()
                if acc_candidate and not acc_candidate.isspace():
                    self.run_context['order']['accession_number'] = acc_candidate
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Accession from {field_spec}: '{acc_candidate}'")
                    return True
            else:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Field {field_spec} not found or empty. ORC fields: {orc_fields[:5] if len(orc_fields) > 5 else orc_fields}")
                    
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"No valid accession found in {field_spec}")
            return False
            
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Error extracting from {field_spec}: {e}")
            return False
    
    def _extract_from_custom_field(self, msg, field_spec: str, step, patient_iter: int, repeat_iter: int) -> bool:
        """Extract accession from custom field specification like 'MSH.10' or 'PID.2'"""
        try:
            # Parse field specification like 'SEGMENT.FIELD'
            if '.' not in field_spec:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Invalid field specification: {field_spec}. Expected format: SEGMENT.FIELD")
                return False
                
            segment_name, field_num = field_spec.split('.', 1)
            field_index = int(field_num)
            
            # Get the segment
            segment = getattr(msg, segment_name, None)
            if not segment:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Segment {segment_name} not found in message")
                return False
                
            # Parse using string method
            segment_str = str(segment)
            fields = segment_str.split('|')
            
            if len(fields) > field_index and fields[field_index].strip():
                full_field = fields[field_index]
                # Extract the ID part before any ^ component separator
                acc_candidate = full_field.split('^')[0].strip()
                if acc_candidate and not acc_candidate.isspace():
                    self.run_context['order']['accession_number'] = acc_candidate
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Accession from {field_spec}: '{acc_candidate}'")
                    return True
                    
            self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"No valid accession found in {field_spec}")
            return False
            
        except (ValueError, IndexError) as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Invalid field specification {field_spec}: {e}")
            return False
        except Exception as e:
            self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Error extracting from {field_spec}: {e}")
            return False
    
    def _extract_order_context(self, order_group, step, patient_iter: int, repeat_iter: int):
        """Extract modality, study description, and other order context from OBR segment"""
        # Try to get OBR from the order detail group first
        obr_segment = None
        order_detail = getattr(order_group, 'ORM_O01_ORDER_DETAIL', None)
        if order_detail:
            obr_segment = getattr(order_detail, 'OBR', None)
        else:
            # Fallback: try to get OBR directly from the order group
            obr_segment = getattr(order_group, 'OBR', None)

        if obr_segment:
            try:
                # Get OBR segment content using string parsing for reliability
                obr_str = str(obr_segment)
                self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"OBR segment content for context extraction: {obr_str}")
                
                # Handle case where OBR segment is wrapped in a list representation
                if obr_str.startswith('[<Segment OBR>]') or '<Segment OBR>' in obr_str:
                    # Try to get the actual segment content
                    try:
                        if hasattr(obr_segment, 'to_er7'):
                            obr_str = obr_segment.to_er7()
                        elif hasattr(obr_segment, 'value'):
                            obr_str = str(obr_segment.value)
                        else:
                            # Fallback: reconstruct from the original message
                            original_msg = self.run_context.get('last_hl7_message', '')
                            obr_lines = [line for line in original_msg.split('\r') if line.startswith('OBR|')]
                            if obr_lines:
                                obr_str = obr_lines[0]
                            else:
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', "Could not extract OBR content for context extraction")
                                return
                        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"OBR extracted content for context: {obr_str}")
                    except Exception as inner_e:
                        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Failed to extract OBR content for context: {inner_e}")
                        return
                
                # Parse using string method for reliability
                obr_fields = obr_str.split('|')
                self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"OBR has {len(obr_fields)} fields for context extraction")
                
                # Extract study description first (OBR-4, field index 4)
                study_description = None
                if len(obr_fields) > 4 and obr_fields[4].strip():
                    # OBR-4 format is usually "code^description^coding_system"
                    desc_field = obr_fields[4]
                    desc_parts = desc_field.split('^')
                    if len(desc_parts) > 1:
                        study_description = desc_parts[1].strip()  # Get the description part
                    else:
                        study_description = desc_parts[0].strip()  # Fallback to the whole field
                    
                    if study_description and not study_description.isspace():
                        self.run_context['order']['study_description'] = study_description
                        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Extracted Study Description from OBR-4: '{study_description}'")
                else:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', "Study Description (OBR-4) not found or empty.")
                
                # Extract modality - try multiple sources and fields
                extracted_modality = None
                
                # First, try OBR-24 (explicit modality field)
                if len(obr_fields) > 24 and obr_fields[24].strip():
                    modality = obr_fields[24].split('^')[0].strip()
                    if modality and not modality.isspace():
                        extracted_modality = modality
                        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Found explicit modality in OBR-24: '{modality}'")
                
                # Second, try OBR-4 procedure code (sometimes contains modality hints)
                if not extracted_modality and len(obr_fields) > 4 and obr_fields[4].strip():
                    procedure_field = obr_fields[4].upper()
                    # Check if procedure code starts with common modality prefixes
                    modality_prefixes = {
                        '7': 'DX',      # 7xxxx codes often X-ray
                        '8': 'CT',      # 8xxxx codes often CT  
                        '9': 'MR',      # 9xxxx codes often MR
                        '76': 'US',     # 76xxx codes often Ultrasound
                        '78': 'NM',     # 78xxx codes often Nuclear Medicine
                        '77': 'MG',     # 77xxx codes often Mammography
                    }
                    
                    procedure_code = obr_fields[4].split('^')[0].strip()
                    for prefix, modality in modality_prefixes.items():
                        if procedure_code.startswith(prefix):
                            extracted_modality = modality
                            self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Inferred modality '{modality}' from procedure code prefix '{prefix}' in OBR-4: '{procedure_code}'")
                            break
                
                # Third, try ZDS segment (custom segment that sometimes contains modality info)
                if not extracted_modality:
                    original_msg = self.run_context.get('last_hl7_message', '')
                    zds_lines = [line for line in original_msg.split('\r') if line.startswith('ZDS|')]
                    if zds_lines:
                        zds_fields = zds_lines[0].split('|')
                        if len(zds_fields) > 3:
                            # ZDS-3 sometimes contains AE Title with modality hint
                            ae_title = zds_fields[3].upper()
                            if 'CT_' in ae_title or '_CT' in ae_title:
                                extracted_modality = 'CT'
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Inferred modality 'CT' from ZDS AE Title: '{ae_title}'")
                            elif 'MR_' in ae_title or '_MR' in ae_title:
                                extracted_modality = 'MR'
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Inferred modality 'MR' from ZDS AE Title: '{ae_title}'")
                            elif 'US_' in ae_title or '_US' in ae_title:
                                extracted_modality = 'US'
                                self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Inferred modality 'US' from ZDS AE Title: '{ae_title}'")
                
                # Fourth, try to infer from study description
                if not extracted_modality and study_description:
                    inferred_modality = self._infer_modality_from_description(study_description, step, patient_iter, repeat_iter)
                    if inferred_modality:
                        extracted_modality = inferred_modality
                        self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Inferred modality from study description: '{inferred_modality}'")
                
                # Store the final modality
                if extracted_modality:
                    self.run_context['order']['modality'] = extracted_modality
                else:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', "No modality could be extracted or inferred.")
                    
            except Exception as e:
                self._log_event(step.step_order, patient_iter, repeat_iter, 'WARN', f"Error extracting order context from OBR: {e}")

    def _infer_modality_from_description(self, description: str, step, patient_iter: int, repeat_iter: int) -> str:
        """
        Intelligently infer DICOM modality from study description text.
        Maps common procedure names/keywords to appropriate DICOM modality codes.
        """
        if not description:
            return None
            
        # Convert to uppercase for case-insensitive matching
        desc_upper = description.upper()
        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Inferring modality from description: '{description}'")
        
        # Define modality mapping patterns - order matters (most specific first)
        modality_patterns = [
            # PET/CT hybrid (must come before CT and PET)
            (['PET/CT', 'PET-CT', 'PETCT'], 'PT'),
            
            # MRI patterns - fix the space issue and add comprehensive patterns
            (['MRI', 'MAGNETIC RESONANCE', 'MR LUMBAR', 'MR CERVICAL', 'MR THORACIC', 'MR BRAIN', 'MR HEAD', 'MR SPINE', 
              'MR CHEST', 'MR ABDOMEN', 'MR PELVIS', 'MR SHOULDER', 'MR KNEE', 'MR ANKLE', 'MR WRIST',
              'T1', 'T2', 'FLAIR', 'DWI', 'DIFFUSION'], 'MR'),
            
            # CT patterns  
            (['CT SCAN', 'CT HEAD', 'CT CHEST', 'CT ABDOMEN', 'CT PELVIS', 'CT SPINE', 'CT ', 
              'COMPUTED TOMOGRAPHY', 'CAT SCAN', 'CONTRAST CT', 'NON-CONTRAST CT'], 'CT'),
            
            # Nuclear Medicine patterns
            (['PET SCAN', 'PET', 'SPECT', 'NUCLEAR MED', 'SCINTIGRAPHY', 'BONE SCAN', 'THYROID SCAN',
              'GALLIUM', 'INDIUM', 'TECHNETIUM', 'FDG'], 'NM'),
            
            # Ultrasound patterns
            (['ULTRASOUND', 'ECHO', 'DOPPLER', 'US ABDOMEN', 'US PELVIS', 'US CARDIAC', 'SONOGRAPHY',
              'ECHOCARDIOGRAM', 'CAROTID US', 'RENAL US'], 'US'),
            
            # Digital Radiography patterns
            (['X-RAY', 'XRAY', 'RADIOGRAPH', 'CHEST PA', 'CHEST AP', 'BONE SURVEY', 'PLAIN FILM',
              'CHEST XRAY', 'SKULL XRAY', 'SPINE XRAY'], 'DX'),
            
            # Computed Radiography patterns
            (['CR CHEST', 'COMPUTED RADIOGRAPHY'], 'CR'),
            
            # Mammography patterns
            (['MAMMOGRAM', 'MAMMO', 'BREAST IMAGING', 'BILATERAL MAMMO', 'SCREENING MAMMO'], 'MG'),
            
            # Angiography patterns
            (['ANGIOGRAM', 'ANGIO', 'ARTERIOGRAM', 'DSA', 'CATHETER', 'CORONARY ANGIO'], 'XA'),
            
            # Fluoroscopy patterns
            (['FLUORO', 'BARIUM', 'UPPER GI', 'LOWER GI', 'BARIUM SWALLOW', 'BARIUM ENEMA'], 'RF'),
            
            # Endoscopy patterns
            (['ENDOSCOPY', 'COLONOSCOPY', 'EGD', 'BRONCHOSCOPY', 'ARTHROSCOPY'], 'ES'),
            
            # OCT patterns
            (['OCT', 'OPTICAL COHERENCE'], 'OCT'),
        ]
        
        # Check each pattern
        for keywords, modality in modality_patterns:
            for keyword in keywords:
                if keyword in desc_upper:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'INFO', f"Modality inference: '{keyword}' in '{description}' -> '{modality}'")
                    return modality
        
        # Special case: if description contains anatomical regions combined with common modality hints
        anatomy_modality_patterns = [
            # Spine studies with MRI keywords
            (['SPINE W/O', 'SPINE WITHOUT', 'LUMBAR W/O', 'CERVICAL W/O', 'THORACIC W/O'], 'MR'),
            # Spine studies often MRI (but not always)
            (['LUMBAR SPINE', 'CERVICAL SPINE', 'THORACIC SPINE'], 'MR'),  
            # Brain studies often MRI
            (['BRAIN', 'HEAD MR', 'HEAD MRI'], 'MR'),  
            # Specific chest CT patterns
            (['CHEST W CONTRAST', 'CHEST W/CONTRAST', 'CHEST WITH CONTRAST'], 'CT'),
            # Abdominal studies often CT
            (['ABDOMEN W CONTRAST', 'ABDOMEN WITH CONTRAST', 'PELVIS W CONTRAST'], 'CT'),
        ]
        
        for keywords, modality in anatomy_modality_patterns:
            for keyword in keywords:
                if keyword in desc_upper:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Anatomical inference: '{keyword}' in '{description}' -> modality '{modality}'")
                    return modality
        
        # Broader anatomical patterns (lower priority, more general)
        # Only used if no specific modality keywords were found
        general_anatomy_patterns = [
            (['SPINE', 'VERTEBRA'], 'MR'),  # Default spine to MR
            (['HEAD', 'SKULL'], 'CT'),      # Default head to CT (unless MRI specified)
            (['CHEST', 'LUNG', 'PULMONARY'], 'DX'),  # Default chest to X-ray
            (['ABDOMEN', 'PELVIS'], 'CT'),  # Default abdominal to CT
        ]
        
        # Only apply general patterns if no specific modality was detected
        for keywords, modality in general_anatomy_patterns:
            for keyword in keywords:
                if keyword in desc_upper:
                    self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"General anatomical inference: '{keyword}' in '{description}' -> modality '{modality}'")
                    return modality
        
        # No match found
        self._log_event(step.step_order, patient_iter, repeat_iter, 'DEBUG', f"Could not infer modality from description: '{description}'")
        return None

def run_simulation_task(run_id, app_context):
    """The entry point for the background task."""
    logging.info(f"Starting background simulation task for Run ID: {run_id}")
    runner = SimulationRunner(run_id, app_context)
    runner.execute()
    logging.info(f"Background simulation task for Run ID: {run_id} has finished.")
# --- END OF FILE app/util/simulation_runner.py ---