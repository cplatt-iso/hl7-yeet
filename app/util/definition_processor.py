# --- START OF FILE app/util/definition_processor.py ---

import os
import json
import logging
import requests
import zipfile
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import current_app

from .. import crud
from ..extensions import db

TERMINOLOGY_BASE_URL = "https://terminology.hl7.org"

# ... process_terminology_refresh is unchanged ...
def process_terminology_refresh(socketio):
    logging.info("Starting HL7 v2 terminology refresh process.")
    socketio.emit('terminology_status', {'status': 'info', 'message': 'Starting terminology refresh...'})
    try:
        index_url = f"{TERMINOLOGY_BASE_URL}/CodeSystem-v2-tables.json"
        socketio.emit('terminology_status', {'status': 'info', 'message': f'Downloading v2 tables index...'})
        index_resp = requests.get(index_url, timeout=30)
        index_resp.raise_for_status()
        index_data = index_resp.json()
        table_concepts = index_data.get("concept", [])
        total_tables = len(table_concepts)
        logging.info(f"Found {total_tables} tables in the master index.")
        socketio.emit('terminology_status', {'status': 'info', 'message': f'Found {total_tables} tables to process.'})
        all_definitions = []
        for i, table_concept in enumerate(table_concepts):
            table_id = table_concept.get("code")
            if not table_id: continue
            progress = int(((i + 1) / total_tables) * 100)
            socketio.emit('terminology_status', {'status': 'progress', 'message': f'Downloading table {table_id} ({i+1}/{total_tables})...', 'progress': progress})
            table_url = f"{TERMINOLOGY_BASE_URL}/CodeSystem-v2-{table_id}.json"
            try:
                table_resp = requests.get(table_url, timeout=10)
                if table_resp.status_code == 200:
                    table_data = table_resp.json()
                    for concept in table_data.get("concept", []):
                        if concept.get("code") and concept.get("display"):
                            all_definitions.append({"table_id": table_id, "value": concept["code"], "description": concept["display"]})
            except requests.RequestException as e:
                logging.error(f"Failed to download or process table {table_id}: {e}")
        if not all_definitions:
            raise Exception("Failed to collect any terminology definitions.")
        socketio.emit('terminology_status', {'status': 'info', 'message': f'Collected {len(all_definitions)} definitions. Clearing database...'})
        crud.clear_hl7_table_definitions(db)
        socketio.emit('terminology_status', {'status': 'info', 'message': 'Bulk-inserting new definitions...'})
        crud.bulk_add_hl7_table_definitions(db, all_definitions)
        crud.set_metadata(db, 'terminology_last_updated', datetime.utcnow().isoformat())
        socketio.emit('terminology_status', {'status': 'success', 'message': 'Terminology refresh completed successfully.'})
        logging.info("Terminology refresh completed successfully.")
        return {"status": "success", "message": f"Successfully loaded {len(all_definitions)} definitions."}
    except Exception as e:
        logging.error(f"An error occurred during terminology refresh: {e}", exc_info=True)
        socketio.emit('terminology_status', {'status': 'error', 'message': f'An error occurred: {e}'})
        return {"status": "error", "message": str(e)}

def process_version_upload(zip_path, version_string, description, user_id):
    ns = {'xsd': 'http://www.w3.org/2001/XMLSchema'}
    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', version_string)
    output_dir = os.path.join(current_app.root_path, '..', 'segment-dictionary', version_string)
    
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    if os.path.exists(output_dir): shutil.rmtree(output_dir)
    os.makedirs(temp_dir)
    os.makedirs(output_dir)

    try:
        logging.info(f"Unzipping '{zip_path}' to '{temp_dir}'")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        fields_path, segments_path = None, None
        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if filename.lower() == 'fields.xsd':
                    fields_path = os.path.join(root, filename)
                if filename.lower() == 'segments.xsd':
                    segments_path = os.path.join(root, filename)
            if fields_path and segments_path:
                break
        
        if not fields_path or not segments_path:
            raise FileNotFoundError("Could not find fields.xsd or segments.xsd in the uploaded zip file.")

        logging.info(f"Parsing fields.xsd from '{fields_path}'...")
        field_defs = _parse_fields_xsd(fields_path, ns)

        logging.info(f"Parsing segments.xsd from '{segments_path}'...")
        segment_structures = _parse_segments_xsd(segments_path, ns)

        if not segment_structures:
             raise ValueError("Parsing segments.xsd yielded no segment definitions.")
        if not field_defs:
             raise ValueError("Parsing fields.xsd yielded no field definitions.")

        logging.info("Combining field and segment data to generate final segment JSONs...")
        for seg_name, seg_data in segment_structures.items():
            final_segment_def = {
                "name": seg_name,
                "description": seg_data['description'],
                "fields": {}
            }
            # --- THIS IS THE NEW LOGIC ---
            for i, field_info in enumerate(seg_data['fields'], 1):
                field_ref = field_info['ref']
                if field_ref and field_ref in field_defs:
                    # Start with the rich data from the field definition
                    full_field_def = field_defs[field_ref]
                    
                    # Add the field_id
                    full_field_def['field_id'] = f"{seg_name}.{i}"
                    
                    # Translate minOccurs/maxOccurs
                    min_occurs = field_info.get('min')
                    max_occurs = field_info.get('max')
                    full_field_def['optionality'] = "Required" if min_occurs == '1' else "Optional"
                    full_field_def['repeatability'] = "Repeatable" if max_occurs != '1' else "Not repeatable"
                    
                    final_segment_def['fields'][str(i)] = full_field_def

            seg_out_path = os.path.join(output_dir, f"{seg_name}.json")
            with open(seg_out_path, 'w') as f:
                json.dump(final_segment_def, f, indent=4) # Use indent 4 for readability

        logging.info(f"Successfully generated {len(segment_structures)} segment definition files.")
        
        new_version = crud.models.Hl7Version( version=version_string, description=description, user_id=user_id, is_active=True )
        db.session.add(new_version)
        db.session.commit()
        logging.info(f"Successfully created database record for version {version_string}")

        return {"status": "success", "message": f"Successfully processed and activated version {version_string}."}

    except Exception as e:
        logging.error(f"An error occurred during version processing for {version_string}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        logging.info(f"Cleaning up temporary directories: {temp_dir}")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        if os.path.exists(zip_path): os.remove(zip_path)


def _parse_fields_xsd(file_path, ns):
    tree = ET.parse(file_path)
    root = tree.getroot()
    field_defs = {}
    
    for element in root.findall('xsd:element', ns):
        field_name = element.get('name')
        type_name = element.get('type')
        if not field_name or not type_name: continue
        
        clean_field_name = field_name.split(':')[-1]
        
        complex_type = root.find(f".//xsd:complexType[@name='{type_name}']", ns)
        if complex_type is None: continue
            
        attr_group_element = complex_type.find('.//xsd:attributeGroup', ns)
        if attr_group_element is None: continue
            
        attr_group_ref = attr_group_element.get('ref')
        if not attr_group_ref: continue
            
        attr_group = root.find(f".//xsd:attributeGroup[@name='{attr_group_ref}']", ns)
        if attr_group is not None:
            # --- FIX: Extract the description from the documentation tag ---
            doc_element = complex_type.find('.//xsd:documentation', ns)
            description = doc_element.text if doc_element is not None else "No description available."

            field_defs[clean_field_name] = {
                'name': next((attr.get('fixed') for attr in attr_group.findall('xsd:attribute[@name="LongName"]', ns)), 'Unknown'),
                'description': description, # Add the description
                'data_type': next((attr.get('fixed') for attr in attr_group.findall('xsd:attribute[@name="Type"]', ns)), 'Unknown'),
                'table': next((attr.get('fixed') for attr in attr_group.findall('xsd:attribute[@name="Table"]', ns)), None),
                'length': next((attr.get('fixed') for attr in attr_group.findall('xsd:attribute[@name="maxLength"]', ns)), 'N/A')
            }
            
    return field_defs

def _parse_segments_xsd(file_path, ns):
    tree = ET.parse(file_path)
    root = tree.getroot()
    segment_defs = {}
    for element in root.findall('xsd:element', ns):
        seg_name = element.get('name')
        if not seg_name or len(seg_name) != 3 or not seg_name.isalnum():
            continue
        type_name = element.get('type')
        if not type_name:
            continue
        complex_type = root.find(f"xsd:complexType[@name='{type_name}']", ns)
        if complex_type is None:
            logging.warning(f"Could not find complexType definition for segment '{seg_name}'")
            continue
        
        # We'll get the segment's long name/description from the element's own annotation
        seg_doc_element = element.find('xsd:annotation/xsd:documentation', ns)
        description = seg_doc_element.text if seg_doc_element is not None else 'No description available.'
        
        fields = complex_type.findall('xsd:sequence/xsd:element', ns)
        
        # --- FIX: Create a list of dictionaries with all necessary info ---
        field_info_list = []
        for field in fields:
            ref = field.get('ref')
            if ref:
                field_info_list.append({
                    "ref": ref.split(':')[-1],
                    "min": field.get('minOccurs', '0'), # Default to 0 if not present
                    "max": field.get('maxOccurs', '1')  # Default to 1 if not present
                })

        segment_defs[seg_name] = {
            'description': description,
            'fields': field_info_list
        }
    return segment_defs

# --- END OF FILE app/util/definition_processor.py ---