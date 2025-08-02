# --- START OF FILE app/util/dicom_actions.py ---
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
# Manually defining these UIDs to avoid import ambiguity hell. This is robust.
ModalityWorklistInformationModelFind = "1.2.840.10008.5.1.4.31"
ModalityPerformedProcedureStepSOPClass = "1.2.840.10008.3.1.2.3.3"
ExplicitVRLittleEndian = "1.2.840.10008.1.2.1" # Transfer syntax for the SR


def perform_c_store(file_paths: list[str], endpoint: dict) -> dict:
    """
    Sends a list of DICOM files to a remote SCP using C-STORE.
    """
    results = {'success': [], 'failure': []}
    # Use the endpoint's configured 'Our AE Title' or a default
    our_aet = endpoint.get('aet_title') or 'YEETER_SCU'
    # Ensure our_aet is always a string and not None
    if not isinstance(our_aet, str):
        our_aet = 'YEETER_SCU'
    ae = AE(ae_title=our_aet)

    # Add a presentation context for each abstract syntax in the files
    # This is a bit naive; a real SCU might group them, but this is fine for simulation.
    for fpath in file_paths:
        try:
            ds = dcmread(fpath, stop_before_pixels=True)
            # Use the UID from the file, not a hardcoded one
            ae.add_requested_context(ds.SOPClassUID)
        except Exception as e:
            logging.error(f"Could not read SOP Class from {fpath}: {e}")
            results['failure'].append({'path': fpath, 'reason': f"File read error: {e}"})
    
    # If, after all that, we have no contexts, there's no point in connecting.
    if not ae.requested_contexts:
        logging.error("C-STORE failed: No valid DICOM files could be read to create presentation contexts.")
        return {"error": "No valid DICOM files with SOPClassUID found to create contexts."}

    logging.info(f"Associating with {endpoint['name']} ({endpoint['hostname']}:{endpoint['port']}) as '{our_aet}' to AET '{endpoint.get('ae_title', 'ANY_SCP')}' for C-STORE.")
    assoc = ae.associate(
        endpoint['hostname'],
        endpoint['port'],
        ae_title=endpoint.get('ae_title', 'ANY_SCP') # This is the remote AE Title
    )

    if not assoc.is_established:
        logging.error(f"C-STORE association with {endpoint['name']} failed.")
        return {"error": f"C-STORE association failed for {endpoint['name']}"}

    try:
        # Loop through the files and send them
        for fpath in file_paths:
            try:
                # The send_c_store call will find the matching presentation context
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
        assoc.release()
        logging.info("C-STORE association released.")
    
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
    
    # Add specific query keys, e.g., AccessionNumber
    if 'AccessionNumber' in query_params:
        sps_item.AccessionNumber = query_params['AccessionNumber']
        
    query_ds.SpecificCharacterSet = "ISO_IR 100"

    logging.info(f"Associating with {endpoint['name']} for DMWL C-FIND...")
    # --- FIX: Provide a default value for the remote AE Title ---
    remote_aet = endpoint.get('ae_title') or 'ANY_SCP'
    assoc = ae.associate(endpoint['hostname'], endpoint['port'], ae_title=remote_aet)
    if not assoc.is_established:
        logging.error(f"DMWL Association with {endpoint['name']} failed.")
        raise ConnectionError(f"DMWL Association with {endpoint['name']} failed.")

    try:
        responses = assoc.send_c_find(query_ds, ModalityWorklistInformationModelFind)
        for status, identifier in responses:
            if status and status.Status == 0xFF00:  # Pending
                results.append(identifier)
            elif status and status.Status != 0x0000:
                logging.warning(f"DMWL query received non-success status: {code_to_category(status.Status)}")
    finally:
        assoc.release()

    logging.info(f"Found {len(results)} item(s) on the worklist.")
    return results


def perform_mpps_action(endpoint: dict, worklist_item: Dataset, mpps_status: str, mpps_uid_from_context: Optional[str] = None) -> Dict:
    """Builds and sends an MPPS N-CREATE or N-SET message."""
    our_aet = endpoint.get('aet_title') or 'YEETER_MPPS'
    ae = AE(ae_title=our_aet)
    ae.add_requested_context(ModalityPerformedProcedureStepSOPClass)
    
    # --- EXTRACT DATA FROM THE DMWL RESPONSE ---
    accession_number = worklist_item.AccessionNumber

    # --- HANDLE UIDS AND LENGTH COMPLIANCE (ported from interactive_mpps_tool.py) ---
    study_instance_uid = worklist_item.get("StudyInstanceUID")
    if not study_instance_uid or len(study_instance_uid.strip()) < 5:
        uid_prefix = "1.2.826.0.1.3680043.2.205."
        timestamp_component = str(int(time.time() * 1000))
        study_instance_uid = uid_prefix + timestamp_component
        logging.warning(f"Worklist item missing valid Study UID. Generated new one: {study_instance_uid}")

    if mpps_uid_from_context:
        mpps_sop_instance_uid = mpps_uid_from_context
    else:
        # We must append a suffix to the Study UID to get the MPPS UID. Check for length limit.
        mpps_sop_instance_uid = f"{study_instance_uid}.1"
        if len(mpps_sop_instance_uid) > 64:
            logging.warning(f"Original Study UID '{study_instance_uid}' is too long. Truncating for MPPS UID.")
            study_instance_uid = study_instance_uid[:62]
            mpps_sop_instance_uid = f"{study_instance_uid}.1"

    sps = worklist_item.ScheduledProcedureStepSequence[0]
    
    # --- TRUNCATE LONG SH FIELDS (ported from interactive_mpps_tool.py) ---
    scheduled_step_id = (sps.get("ScheduledProcedureStepID", "") or "")[:16]
    requested_procedure_id = (worklist_item.get("RequestedProcedureID", "") or "")[:16]
    performed_procedure_step_id = (f"MPPS-{accession_number}" or "")[:16]

    # --- BUILD THE MPPS DATASET ---
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
        series_ds.SeriesInstanceUID = generate_uid()
        series_ds.ReferencedImageSequence = [Dataset()]
        series_ds.ReferencedImageSequence[0].ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.1" # CT Image Storage
        series_ds.ReferencedImageSequence[0].ReferencedSOPInstanceUID = generate_uid()
        ds.PerformedSeriesSequence = [series_ds]

    # --- SEND THE MPPS MESSAGE ---
    logging.info(f"Associating with {endpoint['name']} for MPPS {mpps_status}...")
    # --- FIX: Provide a default value for the remote AE Title ---
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
        else: # COMPLETED or DISCONTINUED
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
# --- END OF FILE app/util/dicom_actions.py ---