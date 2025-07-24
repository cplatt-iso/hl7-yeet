# --- START OF FILE app/routes/util_routes.py ---
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from .. import schemas, crud
from ..extensions import db # <-- db is imported here
from ..models import Hl7TableDefinition

util_bp = Blueprint('utils', __name__)
# This pathing is still a bit fucked, let's make it more robust
DEFINITIONS_DIRECTORY = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'segment-dictionary')
)


@util_bp.route('/get_supported_versions', methods=['GET'])
def get_supported_versions():
    try:
        versions = [d for d in os.listdir(DEFINITIONS_DIRECTORY) if os.path.isdir(os.path.join(DEFINITIONS_DIRECTORY, d))]
        return jsonify(sorted(versions, reverse=True))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Template Routes ---

@util_bp.route('/templates', methods=['GET'])
@jwt_required()
def get_templates():
    user_id = get_jwt_identity()
    templates = crud.get_templates_for_user(db, user_id=user_id)
    response_data = [schemas.Template.model_validate(t) for t in templates]
    return jsonify([t.model_dump() for t in response_data])

@util_bp.route('/templates', methods=['POST'])
@jwt_required()
def save_template():
    user_id = get_jwt_identity()
    try:
        template_data = schemas.TemplateCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    existing_templates = crud.get_templates_for_user(db, user_id=user_id)
    if any(t.name == template_data.name for t in existing_templates):
        return jsonify({"error": "A template with this name already exists"}), 409

    new_template = crud.create_template(db, user_id=user_id, template=template_data)
    response_data = schemas.Template.model_validate(new_template)
    return jsonify(response_data.model_dump()), 201

@util_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@jwt_required()
def delete_template(template_id: int):
    user_id = get_jwt_identity()
    deleted_template = crud.delete_template(db, user_id=user_id, template_id=template_id)
    if not deleted_template:
        return jsonify({"error": "Template not found or you do not have permission to delete it"}), 404
    return jsonify({"message": "Template deleted successfully"}), 200

# --- Token Usage Routes ---

@util_bp.route('/get_total_token_usage', methods=['GET'])
@jwt_required()
def get_total_token_usage():
    user_id = get_jwt_identity()
    total_usage = crud.get_total_usage_for_user(db, user_id=user_id)
    return jsonify({"total_usage": total_usage})


@util_bp.route('/get_usage_by_model', methods=['GET'])
@jwt_required()
def get_usage_by_model():
    user_id = get_jwt_identity()
    usage_data = crud.get_usage_by_model_for_user(db, user_id=user_id)
    return jsonify(usage_data)

@util_bp.route('/tables/<string:table_id>', methods=['GET'])
@jwt_required() # Protect it so only logged-in users can hammer it
def get_table_definitions(table_id: str):
    """Fetches all values for a given HL7 table ID."""
    version = request.args.get('version', '2.5.1') # Allow for future versioning

    definitions = db.session.execute(
        db.select(Hl7TableDefinition).filter_by(table_id=table_id, version=version)
    ).scalars().all()

    if not definitions:
        return jsonify({"error": f"Table '{table_id}' not found for version '{version}'."}), 404

    # Pydantic would be even better here, but for now this is fine.
    results = [
        {"value": d.value, "description": d.description}
        for d in definitions
    ]
    return jsonify(results)
# --- END OF FILE app/routes/util_routes.py ---