import json
import socket
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from hl7apy.parser import parse_message, ParserError
from hl7apy.exceptions import HL7apyException
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'

_hl7_definitions_cache = None

def load_hl7_definitions_from_json():
    global _hl7_definitions_cache
    if _hl7_definitions_cache is not None:
        return _hl7_definitions_cache

    try:
        logging.info("Loading hl7_field_defs.json for the first time...")
        with open('hl7_field_defs.json', 'r') as f:
            _hl7_definitions_cache = json.load(f)
        logging.info("HL7 definitions loaded and cached successfully.")
    except FileNotFoundError:
        logging.error("CRITICAL: hl7_field_defs.json not found! The parser will be hobbled.")
        _hl7_definitions_cache = {}
    except json.JSONDecodeError:
        logging.error("CRITICAL: hl7_field_defs.json is not valid JSON! The parser will be hobbled.")
        _hl7_definitions_cache = {}

    return _hl7_definitions_cache

@app.route('/')
def index():
    return "Backend is running. The real party is on the React frontend."

@app.route('/parse_hl7', methods=['POST'])
def parse_hl7_api():
    definitions = load_hl7_definitions_from_json()
    data = request.get_json()
    hl7_message = data.get('message', '')

    if not hl7_message:
        return jsonify({"status": "error", "message": "No message to parse, you muppet."}), 400

    # --- NEW HOTNESS: SANITIZE THE INPUT BEFORE PARSING ---
    # Define our comment prefixes
    comment_prefixes = ('#', '//', '---')
    
    # Split the message into lines, and filter out the bullshit
    valid_lines = []
    for line in hl7_message.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            # It's a blank line, fuck it
            continue
        if stripped_line.startswith(comment_prefixes):
            # It's a comment, fuck it
            continue
        # If it survives, it's probably a real HL7 segment
        valid_lines.append(stripped_line)

    # Rejoin the valid lines into a pure HL7 message string
    # The standard delimiter is a carriage return
    cleaned_message = '\r'.join(valid_lines)

    logging.info("Cleaned HL7 message for parsing:\n%s\n----END----", cleaned_message)
    # --- END OF THE NEW SHIT ---

    if not cleaned_message:
        return jsonify({"status": "success", "data": []}) # Return empty if it was all comments

    try:
        # We now parse the CLEANED message, not the raw one
        parsed_msg = parse_message(cleaned_message, find_groups=False)
        logging.warning("PARSED SEGMENT NAMES: %s", [c.name for c in parsed_msg.children])

        structured_data = []

        for segment in parsed_msg.children:
            segment_name = segment.name.upper()
            segment_def = definitions.get(segment_name, {})

            segment_data = {"name": segment_name, "fields": []}

            for field in segment.children:
                field_index_str = str(field.name).split('_')[-1]
                field_def = segment_def.get(field_index_str, {})
                segment_data["fields"].append({
                    "index": int(field_index_str) if field_index_str.isdigit() else 0,
                    "value": str(field.value),
                    "name": field_def.get("name", field.long_name or f"Unknown Field"),
                    "description": field_def.get("description", "No fancy description for this one, sorry."),
                    "field_id": f"{segment_name}.{field_index_str}",
                    "length": field_def.get("length", len(str(field.value))),
                    "data_type": field_def.get("data_type", "Unknown")
                })
            
            defined_indexes = set(segment_def.keys())
            parsed_indexes = {str(field.name).split('_')[-1] for field in segment.children}
            missing_indexes = defined_indexes - parsed_indexes
            for missing_index in sorted([i for i in missing_indexes if i.isdigit()], key=int):
                field_def = segment_def.get(missing_index, {})
                segment_data["fields"].append({
                    "index": int(missing_index),
                    "value": "",
                    "name": field_def.get("name", f"Unknown Field {missing_index}"),
                    "description": field_def.get("description", "No description available."),
                    "field_id": field_def.get("field_id", f"{segment_name}.{missing_index}"),
                    "length": field_def.get("length", "N/A"),
                    "data_type": field_def.get("data_type", "Unknown")
                })

            segment_data["fields"].sort(key=lambda f: f["index"])
            structured_data.append(segment_data)

        return jsonify({"status": "success", "data": structured_data})

    except (ParserError, HL7apyException) as e:
        logging.warning(f"HL7 parsing failed: {str(e)}")
        return jsonify({"status": "error", "message": f"HL7APY parsing failed on the cleaned message: {str(e)}"}), 400
    except Exception as e:
        logging.error("An unhandled exception occurred in /parse_hl7", exc_info=True)
        return jsonify({"status": "error", "message": f"An unexpected server error occurred: {str(e)}"}), 500

@app.route('/send_hl7', methods=['POST'])
def send_hl7():
    data = request.get_json()
    host = data.get('host')
    port = int(data.get('port'))
    hl7_message = data.get('message')
    if not all([host, port, hl7_message]):
        return jsonify({"status": "error", "message": "Host, Port, and Message are required."}), 400
    
    # --- We should also clean the message before sending it! ---
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
            ack_buffer = b''
            while True:
                chunk = s.recv(1024)
                if not chunk: break
                ack_buffer += chunk
                if FS + CR in ack_buffer: break
            ack_start = ack_buffer.find(VT)
            if ack_start != -1:
                ack_message = ack_buffer[ack_start+1:].decode('utf-8', errors='ignore').split(FS.decode())[0]
            else:
                ack_message = "No valid MLLP ACK received. Got this garbage instead: " + ack_buffer.decode('utf-8', errors='ignore')
            return jsonify({"status": "success", "message": "Cleaned HL7 message sent successfully. Probably.", "ack": ack_message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)