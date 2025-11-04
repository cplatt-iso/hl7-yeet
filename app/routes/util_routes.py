# --- START OF FILE app/routes/util_routes.py ---
# import re # No longer needed here
# import logging # No longer needed here
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from .. import schemas, crud
from ..extensions import db
from ..auth_utils import auth_required, get_authenticated_user_id
# from ..models import Hl7TableDefinition # No longer needed here

util_bp = Blueprint('utils', __name__)

@util_bp.route('/get_supported_versions', methods=['GET'])
def get_supported_versions():
    """
    Gets a list of active, processed HL7 versions from the database.
    """
    try:
        active_versions = crud.get_active_hl7_versions(db)
        # Return full version objects, sorted by version descending
        from ..schemas import Hl7VersionResponse
        response = [Hl7VersionResponse.model_validate(v).model_dump() for v in active_versions]
        # Sort by version descending (string sort)
        response = sorted(response, key=lambda x: x['version'], reverse=True)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Template Routes ---

@util_bp.route('/templates', methods=['GET'])
@auth_required()
def get_templates():
    user_id = get_authenticated_user_id()
    templates = crud.get_templates_for_user(db, user_id=user_id)
    response_data = [schemas.Template.model_validate(t) for t in templates]
    return jsonify([t.model_dump() for t in response_data])

@util_bp.route('/templates', methods=['POST'])
@auth_required()
def save_template():
    user_id = get_authenticated_user_id()
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
@auth_required()
def delete_template(template_id: int):
    user_id = get_authenticated_user_id()
    deleted_template = crud.delete_template(db, user_id=user_id, template_id=template_id)
    if not deleted_template:
        return jsonify({"error": "Template not found or you do not have permission to delete it"}), 404
    return jsonify({"message": "Template deleted successfully"}), 200

# --- Token Usage Routes ---

@util_bp.route('/get_total_token_usage', methods=['GET'])
@auth_required()
def get_total_token_usage():
    user_id = get_authenticated_user_id()
    total_usage = crud.get_total_usage_for_user(db, user_id=user_id)
    return jsonify({"total_usage": total_usage})

@util_bp.route('/get_usage_by_model', methods=['GET'])
@auth_required()
def get_usage_by_model():
    user_id = get_authenticated_user_id()
    usage_data = crud.get_usage_by_model_for_user(db, user_id=user_id)
    return jsonify(usage_data)

# --- THE TABLE DEFINITION ROUTE HAS BEEN MOVED TO MLLP_ROUTES.PY ---

# --- END OF FILE app/routes/util_routes.py ---