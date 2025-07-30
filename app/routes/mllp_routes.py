# --- START OF FILE app/routes/mllp_routes.py ---

import os
import json
import socket
import logging
import threading
import re
import google.generativeai as genai
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from .. import schemas, crud
from ..extensions import db, socketio
from ..models import Hl7TableDefinition
from ..util.hl7_parser import _parse_hl7_string, load_hl7_definitions_for_version
from ..util.mllp_listener import mllp_server_worker, stop_listener_event

mllp_bp = Blueprint('mllp', __name__)

listener_thread = None
VT, FS, CR = b'\x0b', b'\x1c', b'\x0d'

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY) # type: ignore
else:
    logging.warning("CRITICAL: GOOGLE_API_KEY not found in environment. The AI Analyzer will not work.")

ALLOWED_MODELS = {'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.5-flash', 'gemini-2.5-pro'}


@mllp_bp.route('/parse_hl7', methods=['POST'])
def parse_hl7_api():
    try:
        data = schemas.ParseRequest.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.errors()}), 422

    definitions = load_hl7_definitions_for_version(data.version)
    if not definitions:
        return jsonify({"status": "error", "message": f"Could not load definitions for HL7 version {data.version}."}), 500
    try:
        structured_data = _parse_hl7_string(data.message, definitions, db)
        return jsonify({"status": "success", "data": structured_data})
    except Exception as e:
        logging.error(f"Error during parsing: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@mllp_bp.route('/send_hl7', methods=['POST'])
@jwt_required()
def send_hl7():
    try:
        data = schemas.MllpSendRequest.model_validate(request.get_json())
    except ValidationError as e:
        logging.error(f"Validation error on /api/send_hl7: {e.errors()}")
        return jsonify({"status": "error", "message": e.errors()}), 422

    mllp_message = VT + data.message.encode('utf-8') + FS + CR
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((data.host, data.port))
            s.sendall(mllp_message)
            ack_buffer = s.recv(4096)
            ack_message = "Error: No response received."
            if ack_buffer:
                start_idx = ack_buffer.find(VT) + 1 if VT in ack_buffer else 0
                end_idx = ack_buffer.find(FS) if FS in ack_buffer else len(ack_buffer)
                ack_message = ack_buffer[start_idx:end_idx].decode('utf-8', errors='ignore').strip()
            return jsonify({"status": "success", "message": "Response processed", "ack": ack_message})
    except Exception as e:
        logging.error(f"Error sending HL7: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@mllp_bp.route('/analyze_hl7', methods=['POST'])
@jwt_required()
def analyze_hl7_api():
    user_id = get_jwt_identity()
    if not GEMINI_API_KEY:
        return jsonify({"error": "Google AI API key is not configured on the server."}), 503

    try:
        data = schemas.AnalyzeRequest.model_validate(request.get_json())
    except ValidationError as e:
        logging.error(f"Validation error on /api/analyze_hl7: {e.errors()}")
        return jsonify({"error": e.errors()}), 422
    
    if data.model not in ALLOWED_MODELS:
        logging.warning(f"Rejected attempt to use unapproved model: {data.model}")
        return jsonify({"error": f"Invalid model: {data.model}"}), 400

    definitions = load_hl7_definitions_for_version(data.version)
    if not definitions:
        return jsonify({"error": f"Could not load definitions for HL7 version {data.version}"}), 500
    
    # --- THIS IS THE FIX. I FORGOT TO ADD `db` TO THIS CALL ---
    parsed_data = _parse_hl7_string(data.message, definitions, db)
    breakdown_string = "\n".join([f"{s['name']}:\n" + "\n".join([f"- {f['field_id']}: {f['value'].strip()}" for f in s['fields']]) for s in parsed_data])

    try:
        model = genai.GenerativeModel(data.model, generation_config=genai.types.GenerationConfig(response_mime_type="application/json")) # type: ignore
        prompt = f"""You are an expert HL7 analyst.  Analyze the following HL7 {data.version} message. Use the Segment-Field Breakdown as the source of truth. Your response must be a JSON object with two keys: "explanation" (markdown string) and "fixed_message".  Your "fixed message" must be a JSON formatted message in segment-field breakdown.  Do not output fields with a single space character in the field, empty fields should be length 0\n\n--- HL7 Message ---\n{data.message}\n\n--- Segment-Field Breakdown ({data.version}) ---\n{breakdown_string}\n---"""
        
        response = model.generate_content(prompt)
        usage_meta = response.usage_metadata
        
        usage_data = {
            'input_tokens': usage_meta.prompt_token_count,
            'output_tokens': usage_meta.candidates_token_count,
            'total_tokens': usage_meta.total_token_count
        }
        crud.record_token_usage(db, user_id, data.model, usage_data)
        
        analysis_result = json.loads(response.text)
        
        if 'fixed_message' in analysis_result and isinstance(analysis_result['fixed_message'], dict):
            analysis_result['fixed_message'] = _reconstruct_hl7_from_json(analysis_result['fixed_message'])

        analysis_result['usage'] = usage_data
        analysis_result['prompt'] = prompt
        
        return jsonify(analysis_result)

    except Exception as e:
        logging.error(f"Error during AI analysis: {e}", exc_info=True)
        return jsonify({ "explanation": f"**Analysis Error:** The AI ({data.model}) had a meltdown. \n\n```\n{str(e)}\n```", "fixed_message": data.message }), 500


@mllp_bp.route('/listener/start', methods=['POST'])
@jwt_required()
def start_listener_api():
    global listener_thread
    try:
        data = schemas.ListenerStartRequest.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422

    if listener_thread and listener_thread.is_alive():
        stop_listener_event.set()
        listener_thread.join()
        
    stop_listener_event.clear()
    
    app = current_app._get_current_object() # type: ignore

    listener_thread = threading.Thread(
        target=mllp_server_worker, 
        args=(data.port, socketio, app), 
        daemon=True
    )
    listener_thread.start()
    return jsonify({"message": f"Listener starting on port {data.port}"})


@mllp_bp.route('/listener/stop', methods=['POST'])
@jwt_required()
def stop_listener_api():
    global listener_thread
    if listener_thread and listener_thread.is_alive():
        stop_listener_event.set()
        listener_thread.join()
        return jsonify({"message": "Listener stopping."})
    return jsonify({"message": "Listener was not running."})


@mllp_bp.route('/ping_mllp', methods=['POST'])
@jwt_required()
def ping_mllp():
    try:
        data = schemas.MllpPingRequest.model_validate(request.get_json())
    except ValidationError as e:
        logging.error(f"Validation error on /api/ping_mllp: {e.errors()}")
        return jsonify({"status": "error", "message": e.errors()}), 422

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    control_id = f"PING-TEST-{timestamp}"
    ping_message = (
        f"MSH|^~\\&|HL7_YEETER|PING_CLIENT|REMOTE_APP|REMOTE_FACILITY|{timestamp}||ADT^A31^ADT_A05|{control_id}|P|2.5.1\r"
        f"EVN|A31|{timestamp}\r"
        f"PID|1||PING-PATIENT-ID"
    )

    mllp_message = VT + ping_message.encode('utf-8') + FS + CR
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((data.host, data.port))
            s.sendall(mllp_message)
            ack_buffer = s.recv(4096)
            
            if not ack_buffer:
                return jsonify({"status": "error", "message": "Connection succeeded but no response received from listener."}), 504
            
            start_idx = ack_buffer.find(VT) + 1 if VT in ack_buffer else 0
            end_idx = ack_buffer.find(FS) if FS in ack_buffer else len(ack_buffer)
            ack_message = ack_buffer[start_idx:end_idx].decode('utf-8', errors='ignore').strip()

            if ack_message.startswith("MSH") and "MSA" in ack_message:
                 return jsonify({"status": "success", "message": "Connection test successful.", "ack": ack_message})
            else:
                 return jsonify({"status": "error", "message": "Received a non-HL7 response.", "ack": ack_message}), 502
            
    except socket.timeout:
        return jsonify({"status": "error", "message": f"Connection to {data.host}:{data.port} timed out."}), 504
    except ConnectionRefusedError:
        return jsonify({"status": "error", "message": f"Connection refused by {data.host}:{data.port}."}), 503
    except Exception as e:
        logging.error(f"Error during MLLP ping: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@mllp_bp.route('/tables/<string:table_id>', methods=['GET'])
@jwt_required()
def get_table_definitions(table_id: str):
    """Fetches all values for a given HL7 table ID from the global table."""
    logging.info(f"--- /tables lookup initiated for CLEAN table ID: '{table_id}' ---")

    definitions = db.session.execute(
        db.select(Hl7TableDefinition).filter_by(table_id=table_id)
    ).scalars().all()

    logging.info(f"Database query found {len(definitions)} definitions for '{table_id}'.")

    if not definitions:
        logging.warning(f"Returning 404 for table '{table_id}'.")
        return jsonify({"error": f"Table '{table_id}' not found."}), 404

    results = [
        {"value": d.value, "description": d.description}
        for d in definitions
    ]
    logging.info(f"--- Successfully returning {len(results)} rows for '{table_id}' ---")
    return jsonify(results)


def _reconstruct_hl7_from_json(fixed_message_json):
    reconstructed_segments = []
    for segment_name, fields in fixed_message_json.items():
        max_field = 0
        for key in fields.keys():
            try:
                num = int(key.split('.')[-1])
                if num > max_field:
                    max_field = num
            except (ValueError, IndexError):
                continue

        field_values = [''] * max_field
        for key, value in fields.items():
            try:
                num = int(key.split('.')[-1])
                if 1 <= num <= max_field:
                    field_values[num - 1] = str(value) if value is not None else ''
            except (ValueError, IndexError):
                continue
        
        if segment_name == 'MSH':
            separator = field_values[0] if field_values else '|'
            reconstructed_segments.append(f"{segment_name}{separator}{separator.join(field_values[1:])}")
        else:
            reconstructed_segments.append(f"{segment_name}|{'|'.join(field_values)}")

    return '\r'.join(reconstructed_segments)
# --- END OF FILE app/routes/mllp_routes.py ---