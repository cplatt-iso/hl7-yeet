# --- CREATE NEW FILE: app/routes/endpoint_routes.py ---

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from ..extensions import db
from .. import crud, schemas
from .admin_routes import admin_required

endpoint_bp = Blueprint('endpoint_bp', __name__, url_prefix='/api/endpoints')

@endpoint_bp.route('', methods=['POST'])
@admin_required()
def create_endpoint():
    user_id = get_jwt_identity()
    try:
        data = schemas.EndpointCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    
    endpoint = crud.create_endpoint(db, user_id, data)
    return jsonify(schemas.EndpointResponse.model_validate(endpoint).model_dump()), 201

@endpoint_bp.route('', methods=['GET'])
@jwt_required() # Any logged in user can see the endpoints
def get_endpoints():
    endpoints = crud.get_all_endpoints(db)
    return jsonify([schemas.EndpointResponse.model_validate(e).model_dump() for e in endpoints])

@endpoint_bp.route('/<int:endpoint_id>', methods=['PUT'])
@admin_required()
def update_endpoint(endpoint_id):
    try:
        data = schemas.EndpointUpdate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422
    
    endpoint = crud.update_endpoint(db, endpoint_id, data)
    if not endpoint:
        return jsonify({"error": "Endpoint not found"}), 404
    return jsonify(schemas.EndpointResponse.model_validate(endpoint).model_dump())

@endpoint_bp.route('/<int:endpoint_id>', methods=['DELETE'])
@admin_required()
def delete_endpoint(endpoint_id):
    success = crud.delete_endpoint(db, endpoint_id)
    if not success:
        return jsonify({"error": "Endpoint not found"}), 404
    return '', 204

# --- END OF FILE app/routes/endpoint_routes.py ---