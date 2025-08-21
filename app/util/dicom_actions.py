# --- REPLACE app/util/dicom_actions.py ---
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict

from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
from pynetdicom import AE
from pynetdicom.status import code_to_category

# --- SOP CLASS CONSTANTS ---
ModalityWorklistInformationModelFind = "1.2.840.10008.5.1.4.31"
ModalityPerformedProcedureStepSOPClass = "1.2.840.10008.3.1.2.3.3"
ExplicitVRLittleEndian = "1.2.840.10008.1.2.1"


def perform_c_store(file_paths: list[str], endpoint: dict) -> dict:
    """Sends a list of DICOM files to a remote SCP using C-STORE.
    Creates separate associations for each study/exam to ensure proper cleanup."""
    results = {'success': [], 'failure': []}
    our_aet = endpoint.get('aet_title') or 'YEETER_SCU'
    if not isinstance(our_aet, str):
        our_aet = 'YEETER_SCU'

    # Group files by StudyInstanceUID to send each exam separately
    studies = {}
    for fpath in file_paths:
        try:
            ds = dcmread(fpath, stop_before_pixels=True)
            study_uid = ds.StudyInstanceUID
            if study_uid not in studies:
                studies[study_uid] = {'files': [], 'sop_classes': set()}
            studies[study_uid]['files'].append(fpath)
            studies[study_uid]['sop_classes'].add(ds.SOPClassUID)
        except Exception as e:
            logging.error(f"Could not read DICOM file {fpath}: {e}")
            results['failure'].append({'path': fpath, 'reason': f"File read error: {e}"})
    
    if not studies:
        logging.error("C-STORE failed: No valid DICOM files could be read.")
        return {"error": "No valid DICOM files found."}

    # Send each study with its own association
    for study_uid, study_data in studies.items():
        logging.info(f"Opening new association for study {study_uid}")
        
        ae = AE(ae_title=our_aet)
        # Add presentation contexts for all SOP classes in this study
        for sop_class in study_data['sop_classes']:
            ae.add_requested_context(sop_class)

        logging.info(f"Associating with {endpoint['name']} ({endpoint['hostname']}:{endpoint['port']}) as '{our_aet}' to AET '{endpoint.get('ae_title', 'ANY_SCP')}' for study {study_uid}")
        assoc = ae.associate(
            endpoint['hostname'],
            endpoint['port'],
            ae_title=endpoint.get('ae_title', 'ANY_SCP')
        )

        if not assoc.is_established:
            logging.error(f"C-STORE association with {endpoint['name']} failed for study {study_uid}")
            for fpath in study_data['files']:
                results['failure'].append({'path': fpath, 'reason': f"Association failed for study {study_uid}"})
            continue

        try:
            logging.info(f"Association established for study {study_uid}, sending {len(study_data['files'])} files")
            for fpath in study_data['files']:
                try:
                    status = assoc.send_c_store(fpath)
                    if status and status.Status == 0x0000:
                        logging.info(f"Successfully stored: {fpath}")
                        results['success'].append({'path': fpath})
                    else:
                        reason = code_to_category(status.Status) if status else "Unknown Status"
                        logging.warning(f"C-STORE for {fpath} failed with status: {reason}")
                        results['failure'].append({'path': fpath, 'reason': reason})
                except Exception as e:
                    logging.error(f"An exception occurred during C-STORE for {fpath}: {e}")
                    results['failure'].append({'path': fpath, 'reason': f"Send error: {e}"})
        finally:
            # Release association after each study/exam
            assoc.release()
            logging.info(f"C-STORE association released for study {study_uid}")
    
    return results


def perform_dmwl_find(endpoint: dict, query_params: dict) -> List[Dataset]:
    """Sends a C-FIND to the DMWL and returns the results."""
    our_aet = endpoint.get('aet_title') or 'YEETER_SCU'
    ae = AE(ae_title=our_aet)
    ae.add_requested_context(ModalityWorklistInformationModelFind)
    
    results = []
    query_ds = Dataset()
    query_ds.PatientName = '*'
    query_ds.PatientID = ''
    query_ds.ScheduledProcedureStepSequence = [Dataset()]
    sps_item = query_ds.ScheduledProcedureStepSequence[0]
    sps_item.Modality = ''
    sps_item.ScheduledProcedureStepStatus = query_params.get("ScheduledProcedureStepStatus", "SCHEDULED")
    
    if 'AccessionNumber' in query_params:
        query_ds.AccessionNumber = query_params['AccessionNumber']
        
    query_ds.SpecificCharacterSet = "ISO_IR 100"

    # Debug logging to show what DICOM query is being sent
    logging.info(f"DMWL Query Dataset being sent:")
    logging.info(f"  AccessionNumber: {query_ds.get('AccessionNumber', 'Not set')}")
    logging.info(f"  PatientName: {query_ds.PatientName}")
    logging.info(f"  PatientID: {query_ds.PatientID}")
    logging.info(f"  SPS Status: {sps_item.ScheduledProcedureStepStatus}")
    logging.info(f"  SPS Modality: {sps_item.Modality}")

    logging.info(f"Associating with {endpoint['name']} for DMWL C-FIND...")
    remote_aet = endpoint.get('ae_title') or 'ANY_SCP'
    assoc = ae.associate(endpoint['hostname'], endpoint['port'], ae_title=remote_aet)
    if not assoc.is_established:
        logging.error(f"DMWL Association with {endpoint['name']} failed.")
        raise ConnectionError(f"DMWL Association with {endpoint['name']} failed.")

    try:
        responses = assoc.send_c_find(query_ds, ModalityWorklistInformationModelFind)
        for status, identifier in responses:
            if status and status.Status == 0xFF00 and identifier is not None:
                results.append(identifier)
                # Debug logging for each result
                acc_num = identifier.get('AccessionNumber', 'N/A')
                pat_name = identifier.get('PatientName', 'N/A')
                logging.info(f"DMWL result: Patient={pat_name}, Accession={acc_num}")
            elif status and status.Status != 0x0000:
                logging.warning(f"DMWL query received non-success status: {code_to_category(status.Status)}")
    finally:
        assoc.release()

    logging.info(f"Found {len(results)} item(s) on the worklist.")
    return results


def perform_mpps_action(endpoint: dict, worklist_item: Optional[Dataset], mpps_status: str, mpps_uid_from_context: Optional[str] = None) -> Dict:
    """Builds and sends an MPPS N-CREATE or N-SET message."""
    
    if worklist_item is None:
        return {
            'status': 'FAILURE',
            'details': 'No worklist item provided for MPPS action. Cannot proceed without patient and procedure information.'
        }
    
    our_aet = endpoint.get('aet_title') or 'YEETER_MPPS'
    ae = AE(ae_title=our_aet)
    ae.add_requested_context(ModalityPerformedProcedureStepSOPClass)
    
    accession_number = worklist_item.AccessionNumber

    # --- UID COMPLIANCE AND GENERATION LOGIC ---
    study_instance_uid = worklist_item.get("StudyInstanceUID")
    if not study_instance_uid or len(study_instance_uid.strip()) < 5:
        # Generate a new, compliant UID using your prefix
        uid_prefix = "2.16.840.1.114107.1.1.50."
        timestamp_component = str(int(time.time() * 10000)) # finer timestamp
        study_instance_uid = uid_prefix + timestamp_component
        logging.warning(f"Worklist item missing valid Study UID. Generated new one: {study_instance_uid}")

    if mpps_uid_from_context:
        mpps_sop_instance_uid = mpps_uid_from_context
    else:
        # --- THIS IS THE HARDENED FIX ---
        # Ensure the base UID is not too long before appending. Max length is 64.
        # We append ".1", which is 2 chars. So the base can be at most 62 chars.
        base_uid = str(study_instance_uid)
        if len(base_uid) > 62:
            logging.warning(f"Original Study UID '{base_uid}' is too long. Truncating for MPPS UID.")
            base_uid = base_uid[:62]
        
        mpps_sop_instance_uid = f"{base_uid}.1"

    sps = worklist_item.ScheduledProcedureStepSequence[0]
    
    scheduled_step_id = (sps.get("ScheduledProcedureStepID", "") or "")[:16]
    requested_procedure_id = (worklist_item.get("RequestedProcedureID", "") or "")[:16]
    performed_procedure_step_id = (f"MPPS-{accession_number}" or "")[:16]

    ds = Dataset()
    ds.SOPClassUID = ModalityPerformedProcedureStepSOPClass
    ds.SOPInstanceUID = mpps_sop_instance_uid
    ds.PerformedProcedureStepStatus = mpps_status

    ds.ScheduledStepAttributesSequence = [Dataset()]
    ds.ScheduledStepAttributesSequence[0].StudyInstanceUID = study_instance_uid
    ds.ScheduledStepAttributesSequence[0].AccessionNumber = accession_number
    ds.ScheduledStepAttributesSequence[0].RequestedProcedureID = requested_procedure_id
    ds.ScheduledStepAttributesSequence[0].ScheduledProcedureStepID = scheduled_step_id

    now = datetime.now()
    ds.PerformedProcedureStepID = performed_procedure_step_id
    ds.PerformedStationAETitle = our_aet
    ds.PerformedProcedureStepStartDate = now.strftime('%Y%m%d')
    ds.PerformedProcedureStepStartTime = now.strftime('%H%M%S')
    ds.Modality = sps.Modality
    ds.PatientName = worklist_item.PatientName
    ds.PatientID = worklist_item.PatientID
    ds.PatientBirthDate = worklist_item.PatientBirthDate
    ds.PatientSex = worklist_item.PatientSex

    if mpps_status == "COMPLETED":
        ds.PerformedProcedureStepEndDate = now.strftime('%Y%m%d')
        ds.PerformedProcedureStepEndTime = now.strftime('%H%M%S')
        ds.PerformedProcedureStepDescription = "Procedure completed via HL7 Yeeter"
        series_ds = Dataset()
        series_ds.SeriesInstanceUID = generate_uid(prefix="2.16.840.1.114107.1.1.50.")
        series_ds.ReferencedImageSequence = [Dataset()]
        # Using a generic image storage class
        series_ds.ReferencedImageSequence[0].ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
        series_ds.ReferencedImageSequence[0].ReferencedSOPInstanceUID = generate_uid(prefix="2.16.840.1.114107.1.1.50.")
        ds.PerformedSeriesSequence = [series_ds]

    logging.info(f"Associating with {endpoint['name']} for MPPS {mpps_status}...")
    remote_aet = endpoint.get('ae_title') or 'ANY_SCP'
    assoc = ae.associate(endpoint['hostname'], endpoint['port'], ae_title=remote_aet)
    if not assoc.is_established:
        logging.error(f"MPPS Association with {endpoint['name']} failed.")
        raise ConnectionError(f"MPPS Association with {endpoint['name']} failed.")

    response_status = None
    try:
        if mpps_status == "IN PROGRESS":
            logging.info(f"Sending N-CREATE for MPPS UID: {mpps_sop_instance_uid}")
            response_status, _ = assoc.send_n_create(ds, ModalityPerformedProcedureStepSOPClass, mpps_sop_instance_uid)
        else:
            logging.info(f"Sending N-SET for MPPS UID: {mpps_sop_instance_uid}")
            response_status, _ = assoc.send_n_set(ds, ModalityPerformedProcedureStepSOPClass, mpps_sop_instance_uid)

        if response_status:
            status_text = code_to_category(response_status.Status)
            logging.info(f"MPPS Response Status: {status_text} (0x{response_status.Status:04x})")
            if response_status.Status != 0x0000:
                error_comment = response_status.get('ErrorComment', 'No comment')
                logging.error(f"MPPS SCP Error: {error_comment}")
                return {"status": "FAILURE", "details": f"{status_text}: {error_comment}", "mpps_uid": mpps_sop_instance_uid}
            else:
                return {"status": "SUCCESS", "details": f"Status: {status_text}", "mpps_uid": mpps_sop_instance_uid}
        else:
            logging.error("No response status from SCP for MPPS action.")
            return {"status": "FAILURE", "details": "No response from SCP.", "mpps_uid": mpps_sop_instance_uid}
    finally:
        assoc.release()