import os
import json
import socket
from flask import Flask, request, jsonify
from flask_cors import CORS
from hl7apy.parser import parse_message, ParserError
from hl7apy.exceptions import HL7apyException
import logging
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    logging.warning("CRITICAL: GOOGLE_API_KEY not found. The AI Analyzer will not work.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'
_hl7_definitions_cache = None

def load_hl7_definitions_from_json():
    global _hl7_definitions_cache
    if _hl7_definitions_cache is not None:
        return _hl7_definitions_cache
    try:
        with open('hl7_field_defs.json', 'r') as f:
            _hl7_definitions_cache = json.load(f)
    except Exception:
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

    comment_prefixes = ('#', '//', '---')
    valid_lines = [line.strip() for line in hl7_message.splitlines() if line.strip() and not line.strip().startswith(comment_prefixes)]
    cleaned_message = '\r'.join(valid_lines)
    
    if not cleaned_message:
        return jsonify({"status": "success", "data": []})

    try:
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
            segment_def = definitions.get(segment_name, {})
            segment_data = {"name": segment_name, "fields": []}

            if segment_name == 'MSH':
                msh1_def = segment_def.get("1", {})
                segment_data["fields"].append({ 
                    "index": 1, 
                    "value": field_sep, 
                    "name": msh1_def.get("name", "Field Separator"), 
                    "description": msh1_def.get("description", "The separator character to be used for the rest of the message."), 
                    "field_id": "MSH.1", 
                    "length": msh1_def.get("length", "1"), 
                    "data_type": msh1_def.get("data_type", "ST") 
                })
                
                msh_field_values = parts[1:]
                for i, field_value in enumerate(msh_field_values, start=2):
                    field_index_str = str(i)
                    field_def = segment_def.get(field_index_str, {})
                    segment_data["fields"].append({ 
                        "index": i, 
                        "value": field_value, 
                        "name": field_def.get("name", "Unknown Field"), 
                        "description": field_def.get("description", "No description available."), 
                        "field_id": f"{segment_name}.{i}", 
                        "length": field_def.get("length", "N/A"), 
                        "data_type": field_def.get("data_type", "Unknown") 
                    })
            else:
                field_values = parts[1:]
                for i, field_value in enumerate(field_values, start=1):
                    field_index_str = str(i)
                    field_def = segment_def.get(field_index_str, {})
                    segment_data["fields"].append({ 
                        "index": i, 
                        "value": field_value, 
                        "name": field_def.get("name", "Unknown Field"), 
                        "description": field_def.get("description", "No description available."), 
                        "field_id": f"{segment_name}.{i}", 
                        "length": field_def.get("length", "N/A"), 
                        "data_type": field_def.get("data_type", "Unknown") 
                    })

            defined_indexes = {int(k) for k in segment_def.keys() if k.isdigit()}
            parsed_indexes = {f['index'] for f in segment_data['fields']}
            missing_indexes = defined_indexes - parsed_indexes
            for missing_index in sorted(list(missing_indexes)):
                field_def = segment_def.get(str(missing_index), {})
                segment_data["fields"].append({ 
                    "index": missing_index, 
                    "value": "", 
                    "name": field_def.get("name", f"Unknown Field {missing_index}"), 
                    "description": field_def.get("description", "No description available."), 
                    "field_id": f"{segment_name}.{missing_index}", 
                    "length": field_def.get("length", "N/A"), 
                    "data_type": field_def.get("data_type", "Unknown") 
                })
            
            segment_data["fields"].sort(key=lambda f: f["index"])
            structured_data.append(segment_data)

        return jsonify({"status": "success", "data": structured_data})
    except Exception as e:
        logging.error("PARSING FAILED. I AM A MONSTER:", exc_info=True)
        return jsonify({"status": "error", "message": f"A server error occurred during parsing: {str(e)}"}), 500


# AI Analysis and Send HL7 endpoints are unchanged
@app.route('/analyze_hl7', methods=['POST'])
def analyze_hl7_api():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Google AI API key is not configured on the server."}), 500
    data = request.get_json()
    hl7_message = data.get('message', '')
    if not hl7_message:
        return jsonify({"error": "No message provided for analysis."}), 400
    try:
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        model = genai.GenerativeModel('gemini-1.5-flash', generation_config=generation_config)
        prompt = f"""
Analyze the following HL7 v2.5.1 message for common errors, inconsistencies, or structural problems.
Focus on structure, field usage, and compliance. Do not change patient data.
Your response will be a JSON object with two keys: "explanation" and "fixed_message".
- "explanation": A concise, markdown-formatted string explaining the issues. If none, say so.
- "fixed_message": The corrected HL7 message. If no corrections are needed, return the original message.
Analyze this message:
---
{hl7_message}
---
"""
        response = model.generate_content(prompt)
        analysis_result = json.loads(response.text)
        return jsonify(analysis_result)
    except Exception as e:
        logging.error("Gemini analysis failed:", exc_info=True)
        return jsonify({ "explanation": f"**Analysis Error:** The AI had a meltdown. \n\n```\n{str(e)}\n```", "fixed_message": hl7_message }), 500

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