import json
import socket
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS # <--- IMPORT THIS
from hl7apy.parser import parse_message, ParserError
from hl7apy.exceptions import HL7apyException
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app) # <--- ADD THIS LINE

# ... the rest of your app.py stays exactly the same ...
# No, seriously, don't change anything else in here.
# The part that rendered index.html is now irrelevant but harmless.
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
    # This route is now effectively dead, as index.html is served by Vite.
    # But we'll leave it here as a monument to our simpler past.
    return "Backend is running. The real party is on the React frontend."

@app.route('/parse_hl7', methods=['POST'])
def parse_hl7_api():
    definitions = load_hl7_definitions_from_json()
    data = request.get_json()
    hl7_message = data.get('message', '')

    if not hl7_message:
        return jsonify({"status": "error", "message": "No message to parse, you muppet."}), 400

    logging.warning("GOT HL7 MESSAGE TO PARSE:\n%s\n----END----", hl7_message)

    try:
        parsed_msg = parse_message(hl7_message.replace('\n', '\r'), find_groups=False)
        if parsed_msg.children is not None:
            logging.warning("PARSED SEGMENT NAMES: %s", [c.name for c in parsed_msg.children])
        else:
            logging.warning("PARSED SEGMENT NAMES: None (no children found)")

        structured_data = []

        # Only iterate over what is actually parsed (never the full definition)
        if parsed_msg.children is not None:
            for segment in parsed_msg.children:
                segment_name = segment.name.upper()
                segment_def = definitions.get(segment_name, {})

                segment_data = {"name": segment_name, "fields": []}

                for field in segment.children:
                    # Field name is usually like 'PID_5' or 'MSH_2'
                    field_index_str = str(field.name).split('_')[-1]

                    # Get definition info if available
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

                # (Optional) Pad with blank fields for fields defined in the JSON but not in the message
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

                # Sort fields by index for pretty output
                segment_data["fields"].sort(key=lambda f: f["index"])
                structured_data.append(segment_data)

        return jsonify({"status": "success", "data": structured_data})

    except (ParserError, HL7apyException) as e:
        logging.warning(f"HL7 parsing failed: {str(e)}")
        return jsonify({"status": "error", "message": f"HL7APY parsing failed: {str(e)}"}), 400
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
    if not hl7_message.endswith('\r'):
        hl7_message += '\r'
    mllp_message = VT + hl7_message.encode('utf-8') + FS + CR
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
            return jsonify({"status": "success", "message": "HL7 sent successfully. Probably.", "ack": ack_message})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)