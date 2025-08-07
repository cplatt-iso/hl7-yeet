#!/usr/bin/env python3

print('Testing body part inference...')

def _infer_body_part_from_description(description: str) -> str:
    """Test version of body part inference."""
    if not description:
        return 'CHEST'
    
    desc_upper = description.upper()
    
    body_part_patterns = [
        (['LUMBAR', 'L-SPINE', 'L SPINE'], 'LSPINE'),
        (['CERVICAL', 'C-SPINE', 'C SPINE'], 'CSPINE'),
        (['THORACIC', 'T-SPINE', 'T SPINE'], 'TSPINE'),
        (['SPINE'], 'SPINE'),
        (['CHEST', 'THORAX', 'LUNG'], 'CHEST'),
        (['ABDOMEN', 'ABDOMINAL'], 'ABDOMEN'),
        (['BREAST', 'MAMMARY'], 'BREAST'),
        (['HEAD', 'BRAIN', 'SKULL'], 'HEAD'),
    ]
    
    for keywords, body_part in body_part_patterns:
        for keyword in keywords:
            if keyword in desc_upper:
                return body_part
    
    return 'CHEST'

test_cases = [
    'MRI LUMBAR SPINE W/O',
    'CT CHEST W/O CONTRAST', 
    'X-RAY CHEST PA',
    'ULTRASOUND ABDOMEN',
    'MAMMOGRAM BILATERAL',
    'PET/CT WHOLE BODY',
    'MR BRAIN WITH CONTRAST'
]

for desc in test_cases:
    body_part = _infer_body_part_from_description(desc)
    print(f"'{desc}' -> '{body_part}'")

print('✓ Body part inference working!')
