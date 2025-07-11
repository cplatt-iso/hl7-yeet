# --- START OF FILE app.py ---

# --- STEP 1: MONKEY PATCHING MUST BE THE VERY FIRST THING ---
import eventlet
eventlet.monkey_patch()

# --- STEP 2: NOW, IMPORT EVERYTHING ELSE ---
import os
import json
import socket
import logging
import threading
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import google.generativeai as genai
import sqlite3

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
# --- NEW IMPORTS FOR AUTH ---
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager


load_dotenv()
logging.basicConfig(level=logging.INFO)

logging.info(f"[HL7 Yeeter Backend] Google Client ID loaded: {os.getenv('GOOGLE_CLIENT_ID')}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 

# --- NEW: CONFIGURE EXTENSIONS ---
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "default-super-secret-key-for-dev") # CHANGE THIS IN PRODUCTION
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- GLOBALS (UNCHANGED) ---
listener_thread = None
stop_listener_event = threading.Event()
_hl7_definitions_cache = {}
DEFINITIONS_DIRECTORY = 'segment-dictionary'

# --- EXISTING CONFIGURATION (UNCHANGED) ---
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    logging.warning("CRITICAL: GOOGLE_API_KEY not found. The AI Analyzer will not work.")
else:
    genai.configure(api_key=GEMINI_API_KEY) # type: ignore

ALLOWED_MODELS = { 'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.5-flash', 'gemini-2.5-pro' }
DATABASE_FILE = '/data/yeeter_usage.db'
VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'

# --- MODIFIED: DATABASE INITIALIZATION WITH USERS TABLE ---
def init_db():
    try:
        logging.info("Initializing database...")
        logging.info("verion dingleberry")
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Token usage table (unchanged)
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
        # --- NEW: Users table ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                google_id TEXT UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"FATAL: Could not initialize database: {e}")


# --- All helper functions (_validate_data_type, _validate_length, _validate_required, _parse_hl7_string, load_hl7_definitions_for_version) are UNCHANGED ---
# I'm omitting them for brevity, but you know they are still here.
def _validate_data_type(data_type, value):
    if not value: return None
    dt = (data_type or "").upper()
    if dt == 'NM' and not value.replace('.', '', 1).isdigit(): return f"Data type mismatch: Expected Numeric (NM), got '{value}'."
    if dt == 'DT' and not re.match(r'^\d{8}$', value): return f"Data type mismatch: Expected Date (DT) in YYYYMMDD format, got '{value}'."
    if dt == 'TM' and not re.match(r'^\d{4,6}(\.\d+)?$', value): return f"Data type mismatch: Expected Time (TM) in HHMMSS format, got '{value}'."
    return None
def _validate_length(max_len_def, value):
    if not value or not max_len_def: return None
    try:
        max_len = int(max_len_def)
        if len(value) > max_len: return f"Length error: Value '{value}' ({len(value)} chars) exceeds max length of {max_len}."
    except (ValueError, TypeError): return None
    return None
def _validate_required(optionality, value):
    if (optionality or "").upper() == 'R' and not value: return "Required field is missing."
    return None
def load_hl7_definitions_for_version(version):
    global _hl7_definitions_cache
    if version in _hl7_definitions_cache: return _hl7_definitions_cache[version]
    version_path = os.path.join(DEFINITIONS_DIRECTORY, version)
    if not os.path.isdir(version_path): return {}
    version_definitions = {}
    try:
        for filename in os.listdir(version_path):
            if filename.endswith('.json'):
                segment_id = filename.split('.')[0].upper()
                filepath = os.path.join(version_path, filename)
                with open(filepath, 'r') as f: version_definitions[segment_id] = json.load(f)
        _hl7_definitions_cache[version] = version_definitions
        logging.info(f"Loaded {len(version_definitions)} segment definitions for HL7 version {version}.")
        return version_definitions
    except Exception as e:
        logging.error(f"Error loading definitions for version {version}: {e}")
        return {}
def _parse_hl7_string(hl7_message, definitions):
    comment_prefixes = ('#', '//', '---')
    valid_lines = [line.strip() for line in hl7_message.splitlines() if line.strip() and not line.strip().startswith(comment_prefixes)]
    cleaned_message = '\r'.join(valid_lines)
    if not cleaned_message: return []
    field_sep = '|'
    if cleaned_message.strip().startswith('MSH'): field_sep = cleaned_message.strip()[3]
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
        def process_field(index, value, field_def):
            errors = []
            if err := _validate_data_type(field_def.get("data_type"), value): errors.append(err)
            if err := _validate_length(field_def.get("length"), value): errors.append(err)
            if err := _validate_required(field_def.get("optionality"), value): errors.append(err)
            return {"index": index, "value": value, "name": field_def.get("name", "Unknown Field"), "description": field_def.get("description", "No description available."), "field_id": f"{segment_name}.{index}", "length": field_def.get("length", "N/A"), "data_type": field_def.get("data_type", "Unknown"), "errors": errors, "optionality": field_def.get("optionality", "N/A"), "repeatable": field_def.get("repeatable", "N/A")}
        if segment_name == 'MSH':
            segment_data["fields"].append(process_field(1, field_sep, segment_fields_def.get("1", {})))
            msh_field_values = parts[1:]
            for i, field_value in enumerate(msh_field_values, start=2): segment_data["fields"].append(process_field(i, field_value, segment_fields_def.get(str(i), {})))
        else:
            field_values = parts[1:]
            for i, field_value in enumerate(field_values, start=1): segment_data["fields"].append(process_field(i, field_value, segment_fields_def.get(str(i), {})))
        defined_indexes = {int(k) for k in segment_fields_def.keys() if k.isdigit()}
        parsed_indexes = {f['index'] for f in segment_data['fields']}
        missing_indexes = defined_indexes - parsed_indexes
        for missing_index in sorted(list(missing_indexes)): segment_data["fields"].append(process_field(missing_index, "", segment_fields_def.get(str(missing_index), {})))
        segment_data["fields"].sort(key=lambda f: f["index"])
        structured_data.append(segment_data)
    return structured_data
# --- MLLP LISTENER WORKER (UNCHANGED) ---
def mllp_server_worker(port):
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', port))
        server_socket.listen(1)
        server_socket.settimeout(1.0)
        logging.info(f"MLLP Listener started on port {port}. Waiting for connections.")
        with app.app_context(): socketio.emit('listener_status', {'status': 'listening', 'port': port})
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
                    start_index, end_index = buffer.find(VT), buffer.find(FS + CR)
                    if start_index != -1 and end_index != -1:
                        hl7_message_bytes = buffer[start_index + 1:end_index]
                        hl7_message_str = hl7_message_bytes.decode('utf-8', errors='ignore')
                        logging.info(f"Received message from {addr}")
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        with app.app_context(): socketio.emit('incoming_message', { 'message': hl7_message_str, 'timestamp': timestamp, 'from': f"{addr[0]}:{addr[1]}" })
                        msh_segments = [s for s in hl7_message_str.split('\r') if s.startswith('MSH')]
                        control_id = "UNKNOWN"
                        if msh_segments:
                            fields = msh_segments[0].split('|')
                            if len(fields) > 9: control_id = fields[9]
                        ack_msg = f"MSH|^~\\&|HL7_YEETER|LISTENER|REMOTE_APP|REMOTE_FACILITY|{datetime.now().strftime('%Y%m%d%H%M%S')}||ACK|{control_id}|P|2.5.1\rMSA|AA|{control_id}"
                        mllp_ack = VT + ack_msg.encode('utf-8') + FS + CR
                        conn.sendall(mllp_ack)
                        logging.info(f"Sent ACK for message {control_id}")
            except socket.timeout: continue
            except Exception as e: logging.error(f"Error in listener connection loop: {e}")
    except Exception as e:
        logging.error(f"Could not start MLLP listener on port {port}: {e}")
        with app.app_context(): socketio.emit('listener_status', {'status': 'error', 'message': f"Failed to bind to port {port}. Is it already in use?"})
    finally:
        if server_socket: server_socket.close()
        logging.info(f"MLLP Listener on port {port} has stopped.")
        with app.app_context(): socketio.emit('listener_status', {'status': 'idle'})


# --- API ENDPOINTS ---
@app.route('/')
def index():
    return "Backend is running. Please use the frontend."

# --- NEW: AUTHENTICATION ENDPOINTS ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({"error": "Username, email, and password are required"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username or email already exists"}), 409 # 409 Conflict

    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                   (username, email, password_hash))
    conn.commit()
    conn.close()
    
    return jsonify({"message": f"User {username} created successfully"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user['password_hash'], password):
        # Identity can be anything that is JSON serializable, like user's ID
        access_token = create_access_token(identity=str(user['id'])) 
        return jsonify(access_token=access_token, username=user['username'])

    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({"error": "Google token is missing"}), 400

    google_client_id = os.getenv('GOOGLE_CLIENT_ID')
    if not google_client_id:
        logging.error("FATAL: GOOGLE_CLIENT_ID is not configured on the server.")
        return jsonify({"error": "Server is not configured for Google login."}), 500

    try:
        # We will manually perform the audience check because the library's wrapper is being stupid.
        # First, decode the token WITHOUT checking the audience. This checks signature and expiration.
        id_info = id_token.verify_oauth2_token(token, google_requests.Request())

        # Now, perform the audience check ourselves.
        token_audience = id_info.get('aud')
        
        logging.info("================== AUDIENCE DEBUG ==================")
        logging.info(f"  FROM TOKEN: >{token_audience}< (Length: {len(token_audience)})")
        logging.info(f"FROM .env FILE: >{google_client_id}< (Length: {len(google_client_id)})")
        logging.info(f"   ARE THEY EQUAL? {token_audience == google_client_id}")
        logging.info("====================================================")

        if token_audience != google_client_id:
            raise ValueError(f"Token audience '{token_audience}' did not match expected client ID.")
        
        if token_audience.strip() != google_client_id.strip():
            raise ValueError(f"Token audience did not match expected client ID after stripping whitespace.")

        # If we get here, the token is valid AND for our client.
        google_user_id = id_info['sub']
        email = id_info['email']
        username = id_info.get('name', email.split('@')[0])

        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Check if user exists by their Google ID
        cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_user_id,))
        user = cursor.fetchone()

        if not user:
            placeholder_hash = bcrypt.generate_password_hash(os.urandom(24)).decode('utf-8')
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({"error": "This email is already registered with a username/password. Please log in normally."}), 409
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, google_id) VALUES (?, ?, ?, ?)",
                (username, email, placeholder_hash, google_user_id)
            )
            user_id = cursor.lastrowid
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
        
        conn.close()

        access_token = create_access_token(identity=str(user['id']))
        return jsonify(access_token=access_token, username=user['username'])

    except ValueError as e:
        logging.exception("Google token verification failed:")
        return jsonify({"error": f"Invalid Google token: {e}"}), 401
    except Exception as e:
        logging.exception(f"An unexpected error occurred during Google auth:")
        return jsonify({"error": "An internal error occurred"}), 500

# --- UNAUTHENTICATED PUBLIC ENDPOINTS ---

@app.route('/api/get_supported_versions', methods=['GET'])
def get_supported_versions():
    # ... same as before
    try:
        versions = [d for d in os.listdir(DEFINITIONS_DIRECTORY) if os.path.isdir(os.path.join(DEFINITIONS_DIRECTORY, d))]
        return jsonify(sorted(versions, reverse=True))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parse_hl7', methods=['POST'])
def parse_hl7_api():
    # ... same as before
    data = request.get_json()
    hl7_message = data.get('message', '')
    hl7_version = data.get('version', 'v2.5.1')
    definitions = load_hl7_definitions_for_version(hl7_version)
    if not definitions: return jsonify({"status": "error", "message": f"Could not load definitions for HL7 version {hl7_version}."}), 500
    try:
        structured_data = _parse_hl7_string(hl7_message, definitions)
        return jsonify({"status": "success", "data": structured_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- AUTHENTICATION-PROTECTED ENDPOINTS ---

@app.route('/api/listener/start', methods=['POST'])
@jwt_required()
def start_listener_api():
    # ... same as before, but now requires a valid JWT
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

@app.route('/api/listener/stop', methods=['POST'])
@jwt_required()
def stop_listener_api():
    # ... same as before, but now requires a valid JWT
    global listener_thread
    if listener_thread and listener_thread.is_alive():
        stop_listener_event.set()
        listener_thread.join()
        return jsonify({"message": "Listener stopping."})
    return jsonify({"message": "Listener was not running."})

@app.route('/api/analyze_hl7', methods=['POST'])
@jwt_required()
def analyze_hl7_api():
    # ... same as before, but now requires a valid JWT
    if not GEMINI_API_KEY: return jsonify({"error": "Google AI API key is not configured."}), 500
    data = request.get_json()
    hl7_message = data.get('message', '')
    hl7_version = data.get('version', 'v2.5.1')
    model_name = data.get('model', 'gemini-1.5-flash')
    if not hl7_message: return jsonify({"error": "No message provided for analysis."}), 400
    if model_name not in ALLOWED_MODELS: return jsonify({"error": f"Invalid model: {model_name}"}), 400
    
    definitions = load_hl7_definitions_for_version(hl7_version)
    if not definitions: return jsonify({"error": f"Could not load definitions for HL7 version {hl7_version}"}), 500
    parsed_data = _parse_hl7_string(hl7_message, definitions)
    breakdown_string = "\n".join([f"{s['name']}:\n" + "\n".join([f"- {f['field_id']}: {f['value'].strip()}" for f in s['fields']]) for s in parsed_data])

    try:
        model = genai.GenerativeModel(model_name, generation_config=genai.types.GenerationConfig(response_mime_type="application/json")) # type: ignore
        prompt = f"""Analyze the following HL7 {hl7_version} message. Use the Segment-Field Breakdown as the source of truth. Your response must be a JSON object with two keys: "explanation" (markdown string) and "fixed_message".\n\n--- HL7 Message ---\n{hl7_message}\n\n--- Segment-Field Breakdown ({hl7_version}) ---\n{breakdown_string}\n---"""
        response = model.generate_content(prompt)
        usage = response.usage_metadata
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO token_usage (model, input_tokens, output_tokens, total_tokens) VALUES (?, ?, ?, ?)', (model_name, usage.prompt_token_count, usage.candidates_token_count, usage.total_token_count))
            conn.commit()
            conn.close()
        except Exception as db_e: logging.error(f"Could not write to database: {db_e}")
        analysis_result = json.loads(response.text)
        analysis_result['usage'] = { 'input_tokens': usage.prompt_token_count, 'output_tokens': usage.candidates_token_count, 'total_tokens': usage.total_token_count }
        return jsonify(analysis_result)
    except Exception as e:
        return jsonify({ "explanation": f"**Analysis Error:** The AI ({model_name}) had a meltdown. \n\n```\n{str(e)}\n```", "fixed_message": hl7_message }), 500

@app.route('/api/send_hl7', methods=['POST'])
@jwt_required()
def send_hl7():
    # ... same as before, but now requires a valid JWT
    data = request.get_json()
    host, port, hl7_message = data.get('host'), int(data.get('port')), data.get('message')
    if not all([host, port, hl7_message]): return jsonify({"status": "error", "message": "Host, Port, and Message are required."}), 400
    valid_lines = [line.strip() for line in hl7_message.splitlines() if line.strip() and not line.strip().startswith(('#', '//', '---'))]
    cleaned_message_to_send = '\r'.join(valid_lines)
    if not cleaned_message_to_send: return jsonify({"status": "error", "message": "Cannot send an empty message."}), 400
    mllp_message = VT + cleaned_message_to_send.encode('utf-8') + FS + CR
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((host, port))
            s.sendall(mllp_message)
            ack_buffer = s.recv(4096)
            ack_message = "Error: No response received."
            if ack_buffer:
                start_index = ack_buffer.find(VT) + 1 if VT in ack_buffer else 0
                end_index = ack_buffer.find(FS) if FS in ack_buffer else len(ack_buffer)
                ack_message = ack_buffer[start_index:end_index].decode('utf-8', errors='ignore').strip()
            return jsonify({ "status": "success", "message": "Response processed by backend.", "ack": ack_message })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- The token usage endpoints can remain public for now, or you could lock them down too ---
@app.route('/api/get_total_token_usage', methods=['GET'])
def get_total_token_usage():
    # ... same as before
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(total_tokens) FROM token_usage')
        total_usage = (row[0] if (row := cursor.fetchone()) and row[0] is not None else 0)
        conn.close()
        return jsonify({"total_usage": total_usage})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_usage_by_model', methods=['GET'])
def get_usage_by_model():
    # ... same as before
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT model, SUM(total_tokens) FROM token_usage GROUP BY model')
        usage_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return jsonify(usage_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates', methods=['GET'])
@jwt_required()
def get_templates():
    user_id = get_jwt_identity()
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, content FROM user_templates WHERE user_id = ? ORDER BY name", (user_id,))
    templates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(templates)

@app.route('/api/templates', methods=['POST'])
@jwt_required()
def save_template():
    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get('name')
    content = data.get('content')

    if not name or not content:
        return jsonify({"error": "Template name and content are required"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Optional: Check if a template with the same name already exists for this user
    cursor.execute("SELECT id FROM user_templates WHERE user_id = ? AND name = ?", (user_id, name))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "A template with this name already exists"}), 409

    cursor.execute("INSERT INTO user_templates (user_id, name, content) VALUES (?, ?, ?)", (user_id, name, content))
    template_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"id": template_id, "name": name, "content": content}), 201

@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
@jwt_required()
def delete_template(template_id):
    user_id = get_jwt_identity()
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Important: Make sure the user can only delete their own templates
    cursor.execute("SELECT id FROM user_templates WHERE id = ? AND user_id = ?", (template_id, user_id))
    template = cursor.fetchone()
    if not template:
        conn.close()
        return jsonify({"error": "Template not found or you do not have permission to delete it"}), 404

    cursor.execute("DELETE FROM user_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Template deleted successfully"}), 200

if __name__ == '__main__':
    init_db()
    logging.info("Starting Flask-SocketIO server with eventlet...")
    # Make sure to use use_reloader=False with eventlet
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)