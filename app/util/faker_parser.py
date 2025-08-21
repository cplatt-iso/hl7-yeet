# --- START OF FILE app/util/faker_parser.py ---
import re
import logging
import ast
from faker import Faker
from typing import Dict, Any, Tuple

fake = Faker()
FAKER_CUE_REGEX = re.compile(r'\{\$Faker\.(.+?)\}')

def _generate_accession():
    return f"ACC{fake.random_number(digits=8, fix_len=True)}"

def _generate_study_and_modality():
    """Generates a realistic study description paired with appropriate modality."""
    # Define realistic study description and modality pairs
    study_modality_pairs = [
        # CT Studies
        ('CT HEAD W/O CONTRAST', 'CT'),
        ('CT CHEST W/O CONTRAST', 'CT'),
        ('CT ABDOMEN PELVIS W CONTRAST', 'CT'),
        ('CT SPINE CERVICAL W/O CONTRAST', 'CT'),
        ('CT SPINE LUMBAR W/O CONTRAST', 'CT'),
        ('CT ANGIOGRAM HEAD AND NECK', 'CT'),
        ('CT CHEST W CONTRAST', 'CT'),
        
        # MRI Studies  
        ('MRI LUMBAR SPINE W/O CONTRAST', 'MR'),
        ('MRI KNEE RIGHT W/O CONTRAST', 'MR'),
        ('MRI BRAIN W/O CONTRAST', 'MR'),
        ('MRI CERVICAL SPINE W/O CONTRAST', 'MR'),
        ('MRI SHOULDER LEFT W/O CONTRAST', 'MR'),
        ('MRI KNEE LEFT W/O CONTRAST', 'MR'),
        ('MRI ANKLE RIGHT W/O CONTRAST', 'MR'),
        
        # X-Ray Studies
        ('CHEST X-RAY 2 VIEWS', 'DX'),
        ('X-RAY FOOT 3 VIEWS LEFT', 'DX'),
        ('X-RAY HAND 3 VIEWS RIGHT', 'DX'),
        ('X-RAY SPINE LUMBAR 2 VIEWS', 'DX'),
        ('X-RAY PELVIS 1 VIEW', 'DX'),
        ('X-RAY ABDOMEN 2 VIEWS', 'DX'),
        
        # Ultrasound Studies
        ('ULTRASOUND ABDOMEN COMPLETE', 'US'),
        ('ULTRASOUND PELVIS TRANSVAGINAL', 'US'),
        ('ULTRASOUND CAROTID DUPLEX', 'US'),
        ('ECHOCARDIOGRAM COMPLETE', 'US'),
        ('ULTRASOUND RENAL', 'US'),
        
        # Mammography Studies
        ('MAMMOGRAM SCREENING BILATERAL', 'MG'),
        ('MAMMOGRAM DIAGNOSTIC BILATERAL', 'MG'),
        ('MAMMOGRAM UNILATERAL LEFT', 'MG'),
        
        # Nuclear Medicine Studies
        ('NUCLEAR MEDICINE BONE SCAN', 'NM'),
        ('NUCLEAR MEDICINE CARDIAC STRESS', 'NM'),
        ('NUCLEAR MEDICINE THYROID SCAN', 'NM'),
        
        # Computed Radiography Studies
        ('CR CHEST PA', 'CR'),
        ('CR ABDOMEN SUPINE', 'CR'),
        ('CR PELVIS AP', 'CR'),
    ]
    
    return fake.random_element(elements=study_modality_pairs)

def _generate_and_cache_study_description(context: Dict[str, Any]) -> str:
    """Generate a study description and cache it in the context for reuse."""
    if 'order' not in context:
        context['order'] = {}
    if 'study_description' not in context['order']:
        # Generate paired study description and modality
        study_desc, modality = _generate_study_and_modality()
        context['order']['study_description'] = study_desc
        context['order']['modality'] = modality
    return context['order']['study_description']

def _generate_and_cache_modality(context: Dict[str, Any]) -> str:
    """Generate a modality and cache it in the context for reuse."""
    if 'order' not in context:
        context['order'] = {}
    if 'modality' not in context['order']:
        # Generate paired study description and modality
        study_desc, modality = _generate_study_and_modality()
        context['order']['study_description'] = study_desc
        context['order']['modality'] = modality
    return context['order']['modality']

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
    def replacer(match):
        cue = match.group(1)
        
        # --- 1. Context Variable Check ---
        if cue == 'Patient.MRN': return context.get('patient', {}).get('mrn', 'MRN_MISSING')
        if cue == 'Person.LastName': return context.get('patient', {}).get('last_name', 'LNAME_MISSING')
        if cue == 'Person.FirstName': return context.get('patient', {}).get('first_name', 'FNAME_MISSING')
        if cue == 'Person.DOB': return context.get('patient', {}).get('dob', '19000101')
        if cue == 'Order.AccessionNumber': return _generate_and_cache_accession(context)
        if cue == 'Order.PlacerOrderNumber': return _generate_and_cache_placer_order(context)
        if cue == 'Order.StudyDescription': return _generate_and_cache_study_description(context)
        if cue == 'Order.Modality': return _generate_and_cache_modality(context)
        
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