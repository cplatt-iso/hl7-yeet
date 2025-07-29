from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models import Hl7Destination, User

destinations_bp = Blueprint('destinations_bp', __name__)

@destinations_bp.route('/destinations', methods=['GET'])
@jwt_required()
def get_destinations():
    user_id = get_jwt_identity()
    destinations = db.session.execute(db.select(Hl7Destination).filter_by(user_id=user_id)).scalars().all()
    return jsonify([d.to_dict() for d in destinations])

@destinations_bp.route('/destinations', methods=['POST'])
@jwt_required()
def add_destination():
    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get('name')
    hostname = data.get('hostname')
    port = data.get('port')

    if not all([name, hostname, port]):
        return jsonify({"error": "Missing name, hostname, or port"}), 400

    try:
        port = int(port)
    except (ValueError, TypeError):
        return jsonify({"error": "Port must be a valid number"}), 400

    new_destination = Hl7Destination(
        user_id=user_id,
        name=name,
        hostname=hostname,
        port=port
    )
    db.session.add(new_destination)
    db.session.commit()

    return jsonify(new_destination.to_dict()), 201

@destinations_bp.route('/destinations/<int:destination_id>', methods=['DELETE'])
@jwt_required()
def delete_destination(destination_id):
    user_id = get_jwt_identity()
    destination = db.session.get(Hl7Destination, destination_id)

    if not destination:
        return jsonify({"error": "Destination not found"}), 404

    if destination.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(destination)
    db.session.commit()

    return jsonify({"message": "Destination deleted successfully"}), 200
