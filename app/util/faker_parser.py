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
        if cue == 'Order.AccessionNumber': return context.get('order', {}).get('accession_number', _generate_accession())

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