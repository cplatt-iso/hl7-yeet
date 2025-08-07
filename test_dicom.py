#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '.')

try:
    from app.util.dicom_generator import create_study_files
    import tempfile
    
    print('Testing enhanced DICOM generator...')
    
    # Test MR spine study
    overrides = {
        'PatientName': 'TEST^PATIENT',
        'PatientID': '12345',
        'AccessionNumber': 'ACC123',
        'Modality': 'MR',
        'StudyDescription': 'MRI LUMBAR SPINE'
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        files = create_study_files(temp_dir, 2, overrides, generate_pixels=True)
        print(f'✓ Generated {len(files)} MR spine files')
        for f in files:
            size = os.path.getsize(f)
            print(f'  {os.path.basename(f)} ({size} bytes)')
    
    # Test CT chest study
    overrides['Modality'] = 'CT'
    overrides['StudyDescription'] = 'CT CHEST W/O CONTRAST'
    
    with tempfile.TemporaryDirectory() as temp_dir:
        files = create_study_files(temp_dir, 2, overrides, generate_pixels=True)
        print(f'✓ Generated {len(files)} CT chest files')
        for f in files:
            size = os.path.getsize(f)
            print(f'  {os.path.basename(f)} ({size} bytes)')
    
    print('✓ Enhanced DICOM generator working correctly!')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
