#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '.')

try:
    from app.util.dicom_generator import create_study_files
    import tempfile
    
    print('Testing SR (Structured Report) generation...')
    
    # Test CT chest study with SR report
    overrides = {
        'PatientName': 'TEST^SR^PATIENT',
        'PatientID': 'SR12345',
        'AccessionNumber': 'ACCSR123',
        'Modality': 'CT',
        'StudyDescription': 'CT CHEST W/O CONTRAST',
        'BodyPartExamined': 'CHEST'
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        files = create_study_files(
            temp_dir, 
            num_images=2, 
            overrides=overrides, 
            generate_pixels=True,
            generate_report=True  # This should create an SR object
        )
        print(f'✓ Generated {len(files)} files (including SR):')
        for f in files:
            size = os.path.getsize(f)
            filename = os.path.basename(f)
            file_type = "SR Report" if filename.startswith("SR.") else "Image"
            print(f'  {filename} ({size} bytes) - {file_type}')
    
    # Test MR spine study with SR report
    print('\nTesting MR study with SR...')
    overrides['Modality'] = 'MR'
    overrides['StudyDescription'] = 'MRI LUMBAR SPINE W/O CONTRAST'
    overrides['BodyPartExamined'] = 'LSPINE'
    
    with tempfile.TemporaryDirectory() as temp_dir:
        files = create_study_files(
            temp_dir, 
            num_images=3, 
            overrides=overrides, 
            generate_pixels=True,
            generate_report=True
        )
        print(f'✓ Generated {len(files)} files (including SR):')
        for f in files:
            size = os.path.getsize(f)
            filename = os.path.basename(f)
            file_type = "SR Report" if filename.startswith("SR.") else "Image"
            print(f'  {filename} ({size} bytes) - {file_type}')
    
    print('\n✓ SR generation working correctly!')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
