# --- START OF FILE app/routes/mllp_routes.py ---
# This blueprint handles core MLLP and HL7 processing tasks.
import os
import json
import socket
import logging
import threading
import google.generativeai as genai
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from .. import schemas, crud
from ..extensions import db, socketio # <-- db and socketio are imported correctly
from ..util.hl7_parser import _parse_hl7_string, load_hl7_definitions_for_version
from ..util.mllp_listener import mllp_server_worker, stop_listener_event

# NO IMPORT FROM .config HERE

mllp_bp = Blueprint('mllp', __name__)

# --- Yes, a global is still the simplest way to manage this thread. Don't @ me. ---
listener_thread = None
VT, FS, CR = b'\x0b', b'\x1c', b'\x0d'

# Configure GenAI here if the key exists
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY) # type: ignore
else:
    logging.warning("CRITICAL: GOOGLE_API_KEY not found in environment. The AI Analyzer will not work.")

ALLOWED_MODELS = {'gemini-1.5-flash', 'gemini-1.5-pro'}


@mllp_bp.route('/parse_hl7', methods=['POST'])
def parse_hl7_api():
    try:
        data = schemas.ParseRequest.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.errors()}), 400

    definitions = load_hl7_definitions_for_version(data.version)
    if not definitions:
        return jsonify({"status": "error", "message": f"Could not load definitions for HL7 version {data.version}."}), 500
    try:
        structured_data = _parse_hl7_string(data.message, definitions)
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
        return jsonify({"status": "error", "message": e.errors()}), 400

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
        return jsonify({"error": e.errors()}), 400
    
    if data.model not in ALLOWED_MODELS:
        return jsonify({"error": f"Invalid model: {data.model}"}), 400

    definitions = load_hl7_definitions_for_version(data.version)
    if not definitions:
        return jsonify({"error": f"Could not load definitions for HL7 version {data.version}"}), 500
    
    parsed_data = _parse_hl7_string(data.message, definitions)
    breakdown_string = "\n".join([f"{s['name']}:\n" + "\n".join([f"- {f['field_id']}: {f['value'].strip()}" for f in s['fields']]) for s in parsed_data])

    try:
        model = genai.GenerativeModel(data.model, generation_config=genai.types.GenerationConfig(response_mime_type="application/json")) # type: ignore
        prompt = f"""Analyze the following HL7 {data.version} message. Use the Segment-Field Breakdown as the source of truth. Your response must be a JSON object with two keys: "explanation" (markdown string) and "fixed_message".\n\n--- HL7 Message ---\n{data.message}\n\n--- Segment-Field Breakdown ({data.version}) ---\n{breakdown_string}\n---"""
        
        response = model.generate_content(prompt)
        usage_meta = response.usage_metadata
        
        usage_data = {
            'input_tokens': usage_meta.prompt_token_count,
            'output_tokens': usage_meta.candidates_token_count,
            'total_tokens': usage_meta.total_token_count
        }
        crud.record_token_usage(db, user_id, data.model, usage_data)
        
        analysis_result = json.loads(response.text)
        analysis_result['usage'] = usage_data
        
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
        return jsonify({"error": e.errors()}), 400

    if listener_thread and listener_thread.is_alive():
        stop_listener_event.set()
        listener_thread.join()
        
    stop_listener_event.clear()
    listener_thread = threading.Thread(target=mllp_server_worker, args=(data.port, socketio), daemon=True)
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

# --- END OF FILE app/routes/mllp_routes.py ---