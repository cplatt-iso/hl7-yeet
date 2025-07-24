# --- START OF FILE app/util/mllp_listener.py ---
import socket
import logging
import threading
from datetime import datetime

VT = b'\x0b'
FS = b'\x1c'
CR = b'\x0d'

# Global event to signal the listener thread to stop
stop_listener_event = threading.Event()

def mllp_server_worker(port: int, socketio_instance):
    server_socket = None
    # We need to get the app context to use socketio in a thread
    app = socketio_instance.server.environ['werkzeug.request'].environ['flask.app']
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', port))
        server_socket.listen(1)
        server_socket.settimeout(1.0) # Timeout allows checking the stop_listener_event
        
        logging.info(f"MLLP Listener started on port {port}. Waiting for connections.")
        with app.app_context():
            socketio_instance.emit('listener_status', {'status': 'listening', 'port': port})

        while not stop_listener_event.is_set():
            try:
                conn, addr = server_socket.accept()
                with conn:
                    logging.info(f"Connection from {addr}")
                    buffer = b''
                    while not (FS in buffer and CR in buffer):
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
                            socketio_instance.emit('incoming_message', { 
                                'message': hl7_message_str, 
                                'timestamp': timestamp, 
                                'from': f"{addr[0]}:{addr[1]}" 
                            })

                        # Create and send ACK
                        msh_segments = [s for s in hl7_message_str.split('\r') if s.startswith('MSH')]
                        control_id = "UNKNOWN"
                        if msh_segments:
                            fields = msh_segments[0].split('|')
                            if len(fields) > 9: control_id = fields[9]
                        
                        ack_msg = f"MSH|^~\\&|HL7_YEETER|LISTENER|REMOTE_APP|REMOTE_FACILITY|{datetime.now().strftime('%Y%m%d%H%M%S')}||ACK|{control_id}|P|2.5.1\rMSA|AA|{control_id}"
                        mllp_ack = VT + ack_msg.encode('utf-8') + FS + CR
                        conn.sendall(mllp_ack)
                        logging.info(f"Sent ACK for message {control_id}")

            except socket.timeout:
                continue # This is normal, just loop again to check stop_listener_event
            except Exception as e:
                logging.error(f"Error in listener connection loop: {e}")

    except Exception as e:
        logging.error(f"Could not start MLLP listener on port {port}: {e}")
        with app.app_context():
            socketio_instance.emit('listener_status', {'status': 'error', 'message': f"Failed to bind to port {port}. Is it already in use?"})
    finally:
        if server_socket:
            server_socket.close()
        logging.info(f"MLLP Listener on port {port} has stopped.")
        with app.app_context():
            socketio_instance.emit('listener_status', {'status': 'idle'})

# --- END OF FILE app/util/mllp_listener.py ---