# --- STEP 1: MONKEY PATCHING MUST BE THE VERY FIRST THING ---
import eventlet
eventlet.monkey_patch()

# --- STEP 2: NOW, IMPORT EVERYTHING ELSE ---
import os
import json
import socket
import logging
import threading
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import sqlite3

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBALS ---
listener_thread = None
stop_listener_event = threading.Event()
# This cache will now hold dictionaries keyed by version, e.g., {'v2.5.1': {...}, 'v2.8': {...}}
_hl7_definitions_cache = {}
DEFINITIONS_DIRECTORY = 'segment-dictionary'

# --- EXISTING CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    logging.warning("CRITICAL: GOOGLE_API_KEY not found. The AI Analyzer will not work.")
else:
    genai.configure(api_key=GEMINI_API_KEY) # type: ignore

ALLOWED_MODELS = {
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-2.5-flash',
    'gemini-2.5-pro'
}
DATABASE_FILE = 'yeeter_usage.db'
VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'

# --- DATABASE INITIALIZATION (UNCHANGED) ---
def init_db():
    try:
        logging.info("Initializing database...")
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER
            )
        ''')
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"FATAL: Could not initialize database: {e}")

# --- NEW DICTIONARY LOADING LOGIC ---
def load_hl7_definitions_for_version(version):
    """
    Loads all segment definitions for a specific HL7 version from the directory structure.
    Caches the result to avoid repeated file I/O.
    """
    global _hl7_definitions_cache
    if version in _hl7_definitions_cache:
        return _hl7_definitions_cache[version]

    version_path = os.path.join(DEFINITIONS_DIRECTORY, version)
    if not os.path.isdir(version_path):
        logging.error(f"Definitions directory not found for version: {version}")
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
        logging.info(f"Successfully loaded and cached {len(version_definitions)} segment definitions for HL7 version {version}.")
        return version_definitions
    except Exception as e:
        logging.error(f"Error loading definitions for version {version}: {e}")
        return {}

# --- PARSER HELPER (UPDATED FOR NEW DICTIONARY STRUCTURE) ---
def _parse_hl7_string(hl7_message, definitions):
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
        if not line: continue
        parts = line.split(field_sep)
        segment_name = parts[0]
        
        segment_def_obj = definitions.get(segment_name, {})
        segment_desc = segment_def_obj.get('description', f'{segment_name} - No description provided.')
        segment_fields_def = segment_def_obj.get('fields', {})

        segment_data = {"name": segment_name, "description": segment_desc, "fields": []}

        if segment_name == 'MSH':
            msh1_def = segment_fields_def.get("1", {})
            segment_data["fields"].append({ "index": 1, "value": field_sep, "name": msh1_def.get("name", "Field Separator"), "description": msh1_def.get("description", "The separator character."), "field_id": "MSH.1", "length": msh1_def.get("length", "N/A"), "data_type": msh1_def.get("data_type", "Unknown") })
            msh_field_values = parts[1:]
            for i, field_value in enumerate(msh_field_values, start=2):
                field_index_str = str(i)
                field_def = segment_fields_def.get(field_index_str, {})
                segment_data["fields"].append({ "index": i, "value": field_value, "name": field_def.get("name", "Unknown Field"), "description": field_def.get("description", "No description available."), "field_id": f"{segment_name}.{i}", "length": field_def.get("length", "N/A"), "data_type": field_def.get("data_type", "Unknown") })
        else:
            field_values = parts[1:]
            for i, field_value in enumerate(field_values, start=1):
                field_index_str = str(i)
                field_def = segment_fields_def.get(field_index_str, {})
                segment_data["fields"].append({ "index": i, "value": field_value, "name": field_def.get("name", "Unknown Field"), "description": field_def.get("description", "No description available."), "field_id": f"{segment_name}.{i}", "length": field_def.get("length", "N/A"), "data_type": field_def.get("data_type", "Unknown") })
        
        defined_indexes = {int(k) for k in segment_fields_def.keys() if k.isdigit()}
        parsed_indexes = {f['index'] for f in segment_data['fields']}
        missing_indexes = defined_indexes - parsed_indexes
        for missing_index in sorted(list(missing_indexes)):
            field_def = segment_fields_def.get(str(missing_index), {})
            segment_data["fields"].append({ "index": missing_index, "value": "", "name": field_def.get("name", f"Unknown Field {missing_index}"), "description": field_def.get("description", "No description available."), "field_id": f"{segment_name}.{missing_index}", "length": field_def.get("length", "N/A"), "data_type": field_def.get("data_type", "Unknown") })
        
        segment_data["fields"].sort(key=lambda f: f["index"])
        structured_data.append(segment_data)

    return structured_data

# --- MLLP LISTENER (UNCHANGED) ---
def mllp_server_worker(port):
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', port))
        server_socket.listen(1)
        server_socket.settimeout(1.0)
        logging.info(f"MLLP Listener started on port {port}. Waiting for connections.")
        with app.app_context():
            socketio.emit('listener_status', {'status': 'listening', 'port': port})
        while not stop_listener_event.is_set():
            try:
                conn, addr = server_socket.accept()
                with conn:
                    logging.info(f"Connection from {addr}")
                    buffer = b''
                    while FS not in buffer or CR not in buffer:
                        data = conn.recv(1024)
                        if not data: break
                        buffer += data
                    start_index = buffer.find(VT)
                    end_index = buffer.find(FS + CR)
                    if start_index != -1 and end_index != -1:
                        hl7_message_bytes = buffer[start_index + 1:end_index]
                        hl7_message_str = hl7_message_bytes.decode('utf-8', errors='ignore')
                        logging.info(f"Received message from {addr}")
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        with app.app_context():
                            socketio.emit('incoming_message', { 'message': hl7_message_str, 'timestamp': timestamp, 'from': f"{addr[0]}:{addr[1]}" })
                        msh_segments = [s for s in hl7_message_str.split('\r') if s.startswith('MSH')]
                        control_id = "UNKNOWN"
                        if msh_segments:
                            fields = msh_segments[0].split('|')
                            if len(fields) > 9:
                                control_id = fields[9]
                        ack_msg = f"MSH|^~\\&|HL7_YEETER|LISTENER|REMOTE_APP|REMOTE_FACILITY|{datetime.now().strftime('%Y%m%d%H%M%S')}||ACK|{control_id}|P|2.5.1\rMSA|AA|{control_id}"
                        mllp_ack = VT + ack_msg.encode('utf-8') + FS + CR
                        conn.sendall(mllp_ack)
                        logging.info(f"Sent ACK for message {control_id}")
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Error in listener connection loop: {e}")
                with app.app_context():
                    socketio.emit('listener_status', {'status': 'error', 'message': str(e)})
    except Exception as e:
        logging.error(f"Could not start MLLP listener on port {port}: {e}")
        with app.app_context():
            socketio.emit('listener_status', {'status': 'error', 'message': f"Failed to bind to port {port}. Is it already in use?"})
    finally:
        if server_socket:
            server_socket.close()
        logging.info(f"MLLP Listener on port {port} has stopped.")
        with app.app_context():
            socketio.emit('listener_status', {'status': 'idle'})

# --- API ENDPOINTS ---
@app.route('/')
def index():
    return "Backend is running. The real party is on the React frontend."

# --- NEW ENDPOINT to discover available HL7 versions ---
@app.route('/get_supported_versions', methods=['GET'])
def get_supported_versions():
    try:
        versions = [d for d in os.listdir(DEFINITIONS_DIRECTORY) if os.path.isdir(os.path.join(DEFINITIONS_DIRECTORY, d))]
        return jsonify(sorted(versions, reverse=True))
    except FileNotFoundError:
        logging.error(f"Definitions directory '{DEFINITIONS_DIRECTORY}' not found.")
        return jsonify([])
    except Exception as e:
        logging.error(f"Error reading versions from definitions directory: {e}")
        return jsonify({"error": "Could not retrieve supported versions"}), 500

@app.route('/listener/start', methods=['POST'])
def start_listener_api():
    global listener_thread
    data = request.get_json()
    port = data.get('port')
    if not port: return jsonify({"error": "Port is required"}), 400
    if listener_thread and listener_thread.is_alive():
        stop_listener_event.set()
        listener_thread.join()
    stop_listener_event.clear()
    listener_thread = threading.Thread(target=mllp_server_worker, args=(int(port),), daemon=True)
    listener_thread.start()
    return jsonify({"message": f"Listener starting on port {port}"})

@app.route('/listener/stop', methods=['POST'])
def stop_listener_api():
    global listener_thread
    if listener_thread and listener_thread.is_alive():
        stop_listener_event.set()
        listener_thread.join()
        return jsonify({"message": "Listener stopping."})
    return jsonify({"message": "Listener was not running."})

@app.route('/parse_hl7', methods=['POST'])
def parse_hl7_api():
    data = request.get_json()
    hl7_message = data.get('message', '')
    hl7_version = data.get('version', 'v2.5.1') # Default to v2.5.1
    
    definitions = load_hl7_definitions_for_version(hl7_version)
    if not definitions:
        return jsonify({"status": "error", "message": f"Could not load definitions for HL7 version {hl7_version}. Check server logs."}), 500

    try:
        structured_data = _parse_hl7_string(hl7_message, definitions)
        return jsonify({"status": "success", "data": structured_data})
    except Exception as e:
        logging.error("PARSING FAILED. I AM A MONSTER:", exc_info=True)
        return jsonify({"status": "error", "message": f"A server error occurred during parsing: {str(e)}"}), 500

@app.route('/analyze_hl7', methods=['POST'])
def analyze_hl7_api():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Google AI API key is not configured on the server."}), 500
    
    data = request.get_json()
    hl7_message = data.get('message', '')
    hl7_version = data.get('version', 'v2.5.1')
    model_name = data.get('model', 'gemini-1.5-flash') 

    if not hl7_message: return jsonify({"error": "No message provided for analysis."}), 400
    if model_name not in ALLOWED_MODELS:
        return jsonify({"error": f"Invalid or unsupported model specified: {model_name}"}), 400
    
    logging.info(f"Analyzing message with model: {model_name} and HL7 version: {hl7_version}")
    
    definitions = load_hl7_definitions_for_version(hl7_version)
    if not definitions:
        return jsonify({"error": f"Could not load definitions for HL7 version {hl7_version}"}), 500

    parsed_data = _parse_hl7_string(hl7_message, definitions)
    breakdown_lines = []
    for segment in parsed_data:
        breakdown_lines.append(f"{segment['name']}:")
        for field in segment['fields']:
            breakdown_lines.append(f"- {field['field_id']}: {field['value'].strip()}")
    breakdown_string = "\n".join(breakdown_lines)

    try:
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json") # type: ignore
        model = genai.GenerativeModel(model_name, generation_config=generation_config) # type: ignore
        prompt = f"""
Analyze the following HL7 {hl7_version} message. I have provided the raw message and a pre-parsed, unambiguous breakdown of its segments and fields. 
**You MUST use the Segment-Field Breakdown as the source of truth for field locations and values.** Do not misidentify field positions.

--- HL7 Message ---
{hl7_message}

--- Segment-Field Breakdown ({hl7_version}) ---
{breakdown_string}
---

Your response will be a JSON object with two keys: "explanation" and "fixed_message".
- "explanation": A concise, markdown-formatted string explaining any issues found. Reference the HL7 version {hl7_version} in your analysis.
- "fixed_message": The corrected HL7 message. If no corrections are needed, return the original message.

Your response should ensure that there is a line break between each message segment, and that the message is formatted correctly for HL7 transmission.
"""
        response = model.generate_content(prompt)
        usage = response.usage_metadata
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO token_usage (model, input_tokens, output_tokens, total_tokens)
                VALUES (?, ?, ?, ?)
            ''', (model_name, usage.prompt_token_count, usage.candidates_token_count, usage.total_token_count))
            conn.commit()
            conn.close()
        except Exception as db_e:
            logging.error(f"Could not write to database: {db_e}")
        analysis_result = json.loads(response.text)
        analysis_result['usage'] = { 'input_tokens': usage.prompt_token_count, 'output_tokens': usage.candidates_token_count, 'total_tokens': usage.total_token_count }
        return jsonify(analysis_result)
    except Exception as e:
        logging.error(f"Gemini analysis with model {model_name} failed:", exc_info=True)
        return jsonify({ "explanation": f"**Analysis Error:** The AI ({model_name}) had a meltdown. \n\n```\n{str(e)}\n```", "fixed_message": hl7_message }), 500

@app.route('/get_total_token_usage', methods=['GET'])
def get_total_token_usage():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(total_tokens) FROM token_usage')
        row = cursor.fetchone()
        conn.close()
        total_usage = row[0] if row and row[0] is not None else 0
        return jsonify({"total_usage": total_usage})
    except Exception as e:
        logging.error(f"Could not retrieve total token usage: {e}")
        return jsonify({"error": "Failed to retrieve total token usage from database."}), 500

@app.route('/get_usage_by_model', methods=['GET'])
def get_usage_by_model():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT model, SUM(total_tokens) FROM token_usage GROUP BY model')
        rows = cursor.fetchall()
        conn.close()
        usage_data = {row[0]: row[1] for row in rows}
        return jsonify(usage_data)
    except Exception as e:
        logging.error(f"Could not retrieve usage by model: {e}")
        return jsonify({"error": "Failed to retrieve per-model usage from database."}), 500

@app.route('/send_hl7', methods=['POST'])
def send_hl7():
    data = request.get_json()
    host = data.get('host')
    port = int(data.get('port'))
    hl7_message = data.get('message')
    if not all([host, port, hl7_message]):
        return jsonify({"status": "error", "message": "Host, Port, and Message are required."}), 400
    comment_prefixes = ('#', '//', '---')
    valid_lines = [line.strip() for line in hl7_message.splitlines() if line.strip() and not line.strip().startswith(comment_prefixes)]
    cleaned_message_to_send = '\r'.join(valid_lines)
    if not cleaned_message_to_send:
        return jsonify({"status": "error", "message": "Cannot send an empty message or a message with only comments."}), 400
    mllp_message = VT + cleaned_message_to_send.encode('utf-8') + FS + CR
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((host, port))
            s.sendall(mllp_message)
            ack_buffer = s.recv(4096)
            ack_message_to_send = ""
            if not ack_buffer:
                ack_message_to_send = "Error: No response received from the remote system."
            else:
                start_index = ack_buffer.find(VT) + 1 if VT in ack_buffer else 0
                end_index = ack_buffer.find(FS) if FS in ack_buffer else len(ack_buffer)
                payload_bytes = ack_buffer[start_index:end_index]
                decoded_string = payload_bytes.decode('utf-8', errors='ignore').strip()
                if decoded_string.startswith("MSH"):
                    ack_message_to_send = decoded_string
                else:
                    ack_message_to_send = "Received a non-HL7 response: " + decoded_string
            return jsonify({ "status": "success", "message": "Response processed by backend.", "ack": ack_message_to_send })
    except Exception as e:
        logging.error(f"An exception occurred in send_hl7: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    init_db()
    logging.info("Starting Flask-SocketIO server with eventlet...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)