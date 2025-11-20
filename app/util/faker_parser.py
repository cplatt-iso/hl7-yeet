# --- START OF FILE app/util/faker_parser.py ---

from __future__ import annotations

import ast
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from faker import Faker
from pydantic import ValidationError

from app.exam_spec import ExamSpec

fake = Faker()
FAKER_CUE_REGEX = re.compile(r'\{\$Faker\.(.+?)\}')
LOGGER = logging.getLogger(__name__)

DEFAULT_STUDY_MODALITY_PAIRS: Tuple[Tuple[str, str], ...] = (
    ('CT HEAD W/O CONTRAST', 'CT'),
    ('CT CHEST W/O CONTRAST', 'CT'),
    ('CT ABDOMEN PELVIS W CONTRAST', 'CT'),
    ('CT SPINE CERVICAL W/O CONTRAST', 'CT'),
    ('CT SPINE LUMBAR W/O CONTRAST', 'CT'),
    ('CT ANGIOGRAM HEAD AND NECK', 'CT'),
    ('CT CHEST W CONTRAST', 'CT'),
    ('MRI LUMBAR SPINE W/O CONTRAST', 'MR'),
    ('MRI KNEE RIGHT W/O CONTRAST', 'MR'),
    ('MRI BRAIN W/O CONTRAST', 'MR'),
    ('MRI CERVICAL SPINE W/O CONTRAST', 'MR'),
    ('MRI SHOULDER LEFT W/O CONTRAST', 'MR'),
    ('MRI KNEE LEFT W/O CONTRAST', 'MR'),
    ('MRI ANKLE RIGHT W/O CONTRAST', 'MR'),
    ('CHEST X-RAY 2 VIEWS', 'DX'),
    ('X-RAY FOOT 3 VIEWS LEFT', 'DX'),
    ('X-RAY HAND 3 VIEWS RIGHT', 'DX'),
    ('X-RAY SPINE LUMBAR 2 VIEWS', 'DX'),
    ('X-RAY PELVIS 1 VIEW', 'DX'),
    ('X-RAY ABDOMEN 2 VIEWS', 'DX'),
    ('ULTRASOUND ABDOMEN COMPLETE', 'US'),
    ('ULTRASOUND PELVIS TRANSVAGINAL', 'US'),
    ('ULTRASOUND CAROTID DUPLEX', 'US'),
    ('ECHOCARDIOGRAM COMPLETE', 'US'),
    ('ULTRASOUND RENAL', 'US'),
    ('MAMMOGRAM SCREENING BILATERAL', 'MG'),
    ('MAMMOGRAM DIAGNOSTIC BILATERAL', 'MG'),
    ('MAMMOGRAM UNILATERAL LEFT', 'MG'),
    ('NUCLEAR MEDICINE BONE SCAN', 'NM'),
    ('NUCLEAR MEDICINE CARDIAC STRESS', 'NM'),
    ('NUCLEAR MEDICINE THYROID SCAN', 'NM'),
    ('CR CHEST PA', 'CR'),
    ('CR ABDOMEN SUPINE', 'CR'),
    ('CR PELVIS AP', 'CR'),
)

_current_exam: Optional[ExamSpec] = None


def set_current_exam(exam: Optional[ExamSpec]) -> None:
    """Set the active ExamSpec so faker cues can reuse consistent metadata."""

    global _current_exam
    _current_exam = exam


def get_current_exam() -> Optional[ExamSpec]:
    """Return the currently cached ExamSpec, if any."""

    return _current_exam


def clear_exam_context() -> None:
    """Clear any cached ExamSpec to avoid cross-template leakage."""

    global _current_exam
    _current_exam = None


def _random_study_and_modality() -> Tuple[str, str]:
    return fake.random_element(elements=DEFAULT_STUDY_MODALITY_PAIRS)


def _coerce_exam_spec(exam_data: Any) -> Optional[ExamSpec]:
    if isinstance(exam_data, ExamSpec):
        return exam_data
    if isinstance(exam_data, dict):
        try:
            return ExamSpec(**exam_data)
        except ValidationError as exc:  # pragma: no cover - defensive
            LOGGER.warning("Invalid exam_spec payload in context: %s", exc)
            return None
    if isinstance(exam_data, str):
        try:
            payload = json.loads(exam_data)
        except ValueError as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to decode exam_spec JSON: %s", exc)
            return None
        return _coerce_exam_spec(payload)
    return None


def _resolve_exam_from_context(context: Dict[str, Any]) -> Optional[ExamSpec]:
    if _current_exam is not None:
        return _current_exam

    for key in ('exam', 'exam_spec'):
        exam_candidate = context.get(key)
        exam = _coerce_exam_spec(exam_candidate)
        if exam is not None:
            return exam

    order_exam_id = context.get('order', {}).get('exam_id')
    if order_exam_id:
        try:
            from app.catalog.factory import get_exam_factory

            return get_exam_factory().get_exam_by_id(order_exam_id)
        except ValueError:
            LOGGER.warning("Exam ID '%s' referenced in context but not found", order_exam_id)
    return None


def _seed_exam_metadata(context: Dict[str, Any], exam: ExamSpec) -> None:
    order = context.setdefault('order', {})
    order.setdefault('exam_id', exam.id)
    order.setdefault('study_description', exam.description)
    order.setdefault('modality', exam.modality)
    order.setdefault('body_part', exam.body_part)
    order.setdefault('laterality', getattr(exam.laterality, 'value', exam.laterality))
    if exam.procedure_codes and 'procedure_codes' not in order:
        order['procedure_codes'] = [code.dict() for code in exam.procedure_codes]
    if exam.indication_template and 'reason_for_exam' not in order:
        order['reason_for_exam'] = exam.indication_template


def faker_study_description() -> str:
    exam = get_current_exam()
    if exam:
        return exam.description
    study_desc, _ = _random_study_and_modality()
    return study_desc


def faker_modality() -> str:
    exam = get_current_exam()
    if exam:
        return exam.modality
    _, modality = _random_study_and_modality()
    return modality


def faker_body_part() -> str:
    exam = get_current_exam()
    if exam:
        return exam.body_part
    return "BODY"


def faker_laterality() -> str:
    exam = get_current_exam()
    if exam:
        return getattr(exam.laterality, 'value', exam.laterality)
    return ""


def faker_procedure_code() -> str:
    exam = get_current_exam()
    if exam and exam.procedure_codes:
        return exam.procedure_codes[0].code
    return "99999"


def faker_indication() -> str:
    exam = get_current_exam()
    if exam:
        if exam.indication_template:
            return exam.indication_template
        return f"{exam.modality} {exam.body_part} exam"
    return "Clinical indication not specified"

def _generate_accession():
    return f"ACC{fake.random_number(digits=8, fix_len=True)}"

def _generate_and_cache_study_description(context: Dict[str, Any]) -> str:
    """Generate a study description and cache it in the context for reuse."""
    exam = _resolve_exam_from_context(context)
    if exam:
        _seed_exam_metadata(context, exam)

    order = context.setdefault('order', {})
    if 'study_description' not in order:
        study_desc, modality = _random_study_and_modality()
        order['study_description'] = study_desc
        order.setdefault('modality', modality)
    return order['study_description']

def _generate_and_cache_modality(context: Dict[str, Any]) -> str:
    """Generate a modality and cache it in the context for reuse."""
    exam = _resolve_exam_from_context(context)
    if exam:
        _seed_exam_metadata(context, exam)

    order = context.setdefault('order', {})
    if 'modality' not in order:
        study_desc, modality = _random_study_and_modality()
        order.setdefault('study_description', study_desc)
        order['modality'] = modality
    return order['modality']

def _generate_and_cache_accession(context: Dict[str, Any]) -> str:
    """Generate an accession number and cache it in the context for reuse."""
    if 'order' not in context:
        context['order'] = {}
    
    if 'accession_number' not in context['order']:
        context['order']['accession_number'] = _generate_accession()
    
    return context['order']['accession_number']

def _generate_and_cache_placer_order(context: Dict[str, Any]) -> str:
    """Generate a placer order number and cache it in the context for reuse."""
    if 'order' not in context:
        context['order'] = {}
    
    if 'placer_order_number' not in context['order']:
        context['order']['placer_order_number'] = f"PLR{fake.random_number(digits=8, fix_len=True)}"
    
    return context['order']['placer_order_number']


def _resolve_context_path(context: Dict[str, Any], cue: str) -> Tuple[Any, bool]:
    """Resolve a dotted path (with optional method calls) against the run context."""
    parts = cue.split('.')
    obj: Any = context
    last_was_method = False

    for part in parts:
        if isinstance(obj, dict) and '(' not in part:
            if part not in obj:
                raise KeyError(part)
            obj = obj[part]
            last_was_method = False
            continue

        if '(' in part and part.endswith(')'):
            method_name, args_str = part[:-1].split('(', 1)
            if not hasattr(obj, method_name) or not callable(getattr(obj, method_name)):
                raise AttributeError(f"Object '{type(obj).__name__}' has no callable method '{method_name}'")
            args, kwargs = _safe_eval_call_params(args_str)
            obj = getattr(obj, method_name)(*args, **kwargs)
            last_was_method = True
        else:
            if hasattr(obj, part):
                obj = getattr(obj, part)
                last_was_method = False
            else:
                raise AttributeError(f"Object '{type(obj).__name__}' has no attribute '{part}'")

    return obj, last_was_method

def _safe_eval_call_params(args_str: str) -> Tuple[list, dict]:
    """
    Safely evaluates a string of Python arguments (both positional and keyword) using AST.
    Returns a tuple of (args, kwargs).
    """
    if not args_str.strip():
        return [], {}
    
    try:
        wrapper = f"dummy({args_str})"
        tree = ast.parse(wrapper, mode='eval')
        
        if not isinstance(tree.body, ast.Call):
            raise ValueError("Argument string is not a valid function call.")
            
        # Extract positional arguments
        args = [ast.literal_eval(arg) for arg in tree.body.args]
        
        # Extract keyword arguments
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in tree.body.keywords}
            
        return args, kwargs
    except (ValueError, SyntaxError, TypeError) as e:
        logging.error(f"[FAKER_PARSER_AST] Could not parse arguments '{args_str}': {e}")
        raise ValueError(f"Invalid argument format: {args_str}")


def process_faker_string(template_string: str, context: Dict[str, Any]) -> str:
    exam = _resolve_exam_from_context(context)
    if exam:
        _seed_exam_metadata(context, exam)

    def replacer(match):
        cue = match.group(1)
        
        # --- 1. Context Variable Check ---
        if cue == 'Patient.MRN':
            return context.get('patient', {}).get('mrn', 'MRN_MISSING')
        if cue == 'Person.LastName':
            return context.get('patient', {}).get('last_name', 'LNAME_MISSING')
        if cue == 'Person.FirstName':
            return context.get('patient', {}).get('first_name', 'FNAME_MISSING')
        if cue == 'Person.DOB':
            return context.get('patient', {}).get('dob', '19000101')
        if cue == 'Order.AccessionNumber':
            return _generate_and_cache_accession(context)
        if cue == 'Order.PlacerOrderNumber':
            return _generate_and_cache_placer_order(context)
        if cue == 'Order.StudyDescription':
            return _generate_and_cache_study_description(context)
        if cue == 'Order.Modality':
            return _generate_and_cache_modality(context)
        
        # Additional contextual variables for reuse
        if cue == 'Context.AccessionNumber': 
            # Return the cached accession number if it exists, otherwise generate one
            return context.get('order', {}).get('accession_number', _generate_and_cache_accession(context))
        if cue == 'Context.PlacerOrderNumber':
            # Return the cached placer order number if it exists, otherwise generate one
            return context.get('order', {}).get('placer_order_number', _generate_and_cache_placer_order(context))
        if cue == 'Context.StudyDescription':
            return context.get('order', {}).get('study_description', _generate_and_cache_study_description(context))
        if cue == 'Context.Modality':
            return context.get('order', {}).get('modality', _generate_and_cache_modality(context))

        # Attempt to resolve against the full run context (supports nested structures and method calls)
        try:
            resolved_value, last_was_method = _resolve_context_path(context, cue)
            if isinstance(resolved_value, datetime) and not last_was_method:
                return resolved_value.strftime('%Y%m%d%H%M%S')
            return str(resolved_value)
        except (KeyError, AttributeError, ValueError, TypeError):
            pass

        # Support for PACS-specific accession placement
        # Some PACS look for accession in OBR-2, some in OBR-3
        if cue == 'PACS.AccessionInOBR2':
            # For PACS that expect accession in OBR-2 (Placer Order Number)
            return _generate_and_cache_accession(context)
        if cue == 'PACS.AccessionInOBR3':  
            # For PACS that expect accession in OBR-3 (Filler Order Number) - this is most common
            return _generate_and_cache_accession(context)

        # --- 2. Robust Faker Method/Attribute Resolution ---
        try:
            parts = cue.split('.')
            obj = fake
            
            for part in parts:
                if '(' in part and part.endswith(')'):
                    method_name, args_str = part[:-1].split('(', 1)
                    
                    if not hasattr(obj, method_name) or not callable(getattr(obj, method_name)):
                        raise AttributeError(f"Object '{type(obj).__name__}' has no callable method '{method_name}'")

                    # Use the new parser that gets both args and kwargs
                    args, kwargs = _safe_eval_call_params(args_str)
                    obj = getattr(obj, method_name)(*args, **kwargs)
                else: # It's an attribute
                    obj = getattr(obj, part)
            return str(obj)

        except Exception as e:
            logging.warning(f"[FAKER_PARSER] Failed to process cue '{{$Faker.{cue}}}': {type(e).__name__} - {e}")
            return f"{{$Faker.{cue}}}"

    return FAKER_CUE_REGEX.sub(replacer, template_string)
# --- END OF FILE app/util/faker_parser.py ---