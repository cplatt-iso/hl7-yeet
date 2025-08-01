# --- START OF FILE app/util/dicom_actions.py ---
import logging
from pydicom import dcmread
from pydicom.dataset import Dataset
from pynetdicom import AE
from pynetdicom.status import code_to_category

# --- SOP CLASS CONSTANTS ---
# Manually defining these UIDs to avoid import ambiguity hell. This is robust.
ModalityWorklistInformationModelFind = "1.2.840.10008.5.1.4.31"
ModalityPerformedProcedureStepSOPClass = "1.2.840.10008.3.1.2.3.3"


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

# TODO: Add functions for DMWL/MPPS actions here.
# Example skeletons:
# def perform_dmwl_find(endpoint: dict, query_params: dict) -> list[Dataset]:
#     pass
#
# def perform_mpps_n_create(endpoint: dict, mpps_dataset: Dataset) -> dict:
#     pass
#
# def perform_mpps_n_set(endpoint: dict, mpps_dataset: Dataset) -> dict:
#     pass

# --- END OF FILE app/util/dicom_actions.py ---