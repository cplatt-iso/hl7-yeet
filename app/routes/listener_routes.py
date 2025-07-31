# --- CREATE NEW FILE: app/routes/listener_routes.py ---

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from .. import crud
from ..extensions import db

listener_bp = Blueprint('listener_api', __name__, url_prefix='/api/listener')

@listener_bp.route('/messages', methods=['GET'])
@jwt_required()
def get_messages():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', None, type=str)
    
    pagination = crud.get_received_messages(db, page=page, per_page=per_page, search_term=search)
    
    return jsonify({
        'items': [msg.to_summary_dict() for msg in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    })

@listener_bp.route('/messages/<int:msg_id>', methods=['GET'])
@jwt_required()
def get_message_detail(msg_id):
    message = crud.get_received_message_by_id(db, msg_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404
    return jsonify({"raw_message": message.raw_message})

@listener_bp.route('/messages', methods=['DELETE'])
@jwt_required()
def clear_messages():
    crud.clear_all_received_messages(db)
    return '', 204