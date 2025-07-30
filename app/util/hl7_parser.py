# --- START OF FILE app/util/hl7_parser.py ---

import os
import json
import logging
import re
from typing import Any, Dict, List
from flask_sqlalchemy import SQLAlchemy 
from ..models import Hl7TableDefinition 

DEFINITIONS_DIRECTORY = 'segment-dictionary'
_hl7_definitions_cache: Dict[str, Dict] = {}

def _validate_data_type(data_type: str | None, value: str) -> str | None:
    if not value: return None
    dt = (data_type or "").upper()
    if dt == 'NM' and not value.replace('.', '', 1).isdigit():
        return f"Data type mismatch: Expected Numeric (NM), got '{value}'."
    if dt == 'DT' and not re.match(r'^\d{8}$', value):
        return f"Data type mismatch: Expected Date (DT) in YYYYMMDD format, got '{value}'."
    if dt == 'TM' and not re.match(r'^\d{4,6}(\.\d+)?$', value):
        return f"Data type mismatch: Expected Time (TM) in HHMMSS format, got '{value}'."
    return None

def _validate_length(max_len_def: str | None, value: str) -> str | None:
    if not value or not max_len_def: return None
    try:
        max_len = int(max_len_def)
        if len(value) > max_len:
            return f"Length error: Value '{value}' ({len(value)} chars) exceeds max length of {max_len}."
    except (ValueError, TypeError):
        return None
    return None

def _validate_required(optionality: str | None, value: str) -> str | None:
    if (optionality or "").upper() == 'R' and not value:
        return "Required field is missing."
    return None

def load_hl7_definitions_for_version(version: str) -> Dict[str, Any]:
    global _hl7_definitions_cache
    if version in _hl7_definitions_cache:
        return _hl7_definitions_cache[version]

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    version_path = os.path.join(base_dir, DEFINITIONS_DIRECTORY, version)
    
    if not os.path.isdir(version_path):
        logging.error(f"Definitions directory not found for version {version} at {version_path}")
        return {}

    version_definitions = {}
    try:
        for filename in os.listdir(version_path):
            if filename.endswith('.json'):
                segment_id = filename.split('.')[0].upper()
                filepath = os.path.join(version_path, filename)
                with open(filepath, 'r') as f:
                    version_definitions[segment_id] = json.load(f)
        _hl7_definitions_cache[version] = version_definitions
        logging.info(f"Loaded {len(version_definitions)} segment definitions for HL7 version {version}.")
        return version_definitions
    except Exception as e:
        logging.error(f"Error loading definitions for version {version}: {e}")
        return {}

def _parse_hl7_string(hl7_message: str, definitions: Dict[str, Any], db: SQLAlchemy) -> List[Dict[str, Any]]:
    comment_prefixes = ('#', '//', '---')
    valid_lines = [line.strip() for line in hl7_message.splitlines() if line.strip() and not line.strip().startswith(comment_prefixes)]
    cleaned_message = '\r'.join(valid_lines)
    if not cleaned_message:
        return []

    field_sep = '|'
    if cleaned_message.strip().startswith('MSH'):
        field_sep = cleaned_message.strip()[3]

    structured_data = []
    for line in cleaned_message.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split(field_sep)
        segment_name = parts[0]
        segment_def_obj = definitions.get(segment_name, {})
        segment_desc = segment_def_obj.get('description', f'{segment_name} - No description provided.')
        segment_fields_def = segment_def_obj.get('fields', {})

        segment_data: Dict[str, Any] = {"name": segment_name, "description": segment_desc, "fields": []}

        def process_field(index: int, value: str, field_def: Dict[str, Any]) -> Dict[str, Any]:
            errors = []
            if err := _validate_data_type(field_def.get("data_type"), value): errors.append(err)
            if err := _validate_length(field_def.get("length"), value): errors.append(err)
            if err := _validate_required(field_def.get("optionality"), value): errors.append(err)
            
            final_table_id = None
            original_table_id = field_def.get("table")
            if original_table_id:
                match = re.search(r'\d{4}$', original_table_id)
                if match:
                    cleaned_id = match.group(0)
                    # --- THE CHECK-THE-DATABASE FIX ---
                    # We do a quick, efficient check to see if at least ONE row
                    # exists for this table ID in our database.
                    table_exists = db.session.query(Hl7TableDefinition.id).filter_by(table_id=cleaned_id).first()
                    if table_exists:
                        # Only if it exists do we pass the ID to the frontend.
                        final_table_id = cleaned_id

            return {
                "index": index,
                "value": value,
                "name": field_def.get("name", "Unknown Field"),
                "description": field_def.get("description", "No description available."),
                "field_id": f"{segment_name}.{index}",
                "table": final_table_id, # <-- THIS IS NOW GUARANTEED TO BE VALID OR NULL
                "length": field_def.get("length", "N/A"),
                "data_type": field_def.get("data_type", "Unknown"),
                "errors": errors,
                "optionality": field_def.get("optionality", "N/A"),
                "repeatable": field_def.get("repeatable", "N/A"),
            }

        if segment_name == 'MSH':
            segment_data["fields"].append(process_field(1, field_sep, segment_fields_def.get("1", {})))
            msh_field_values = parts[1:]
            for i, field_value in enumerate(msh_field_values, start=2):
                segment_data["fields"].append(process_field(i, field_value, segment_fields_def.get(str(i), {})))
        else:
            field_values = parts[1:]
            for i, field_value in enumerate(field_values, start=1):
                segment_data["fields"].append(process_field(i, field_value, segment_fields_def.get(str(i), {})))

        defined_indexes = {int(k) for k in segment_fields_def.keys() if k.isdigit()}
        parsed_indexes = {f['index'] for f in segment_data['fields']}
        missing_indexes = defined_indexes - parsed_indexes
        for missing_index in sorted(list(missing_indexes)):
            segment_data["fields"].append(process_field(missing_index, "", segment_fields_def.get(str(missing_index), {})))
        
        segment_data["fields"].sort(key=lambda f: f["index"])
        structured_data.append(segment_data)

    return structured_data

# --- END OF FILE app/util/hl7_parser.py ---