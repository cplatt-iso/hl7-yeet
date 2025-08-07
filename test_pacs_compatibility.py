#!/usr/bin/env python3

import sys
import os
import tempfile
sys.path.insert(0, '.')

try:
    from app.util.dicom_generator import create_study_files
    import pydicom
    
    print('Testing DICOM PACS compatibility...')
    
    # Test different modalities for variety
    test_cases = [
        {'Modality': 'MR', 'StudyDescription': 'MRI LUMBAR SPINE W/O', 'PatientName': 'TEST^MR'},
        {'Modality': 'CT', 'StudyDescription': 'CT CHEST W/O CONTRAST', 'PatientName': 'TEST^CT'},
        {'Modality': 'DX', 'StudyDescription': 'CHEST X-RAY PA', 'PatientName': 'TEST^DX'},
        {'Modality': 'US', 'StudyDescription': 'ULTRASOUND ABDOMEN', 'PatientName': 'TEST^US'},
    ]
    
    for i, overrides in enumerate(test_cases):
        print(f'\n--- Testing {overrides["Modality"]} DICOM ---')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            files = create_study_files(temp_dir, 2, overrides, generate_pixels=True)
            
            for file_path in files:
                # Load and validate DICOM file
                ds = pydicom.dcmread(file_path)
                
                # Check critical PACS compatibility attributes
                checks = [
                    ('SOPClassUID', lambda x: x is not None and len(x) > 0),
                    ('SOPInstanceUID', lambda x: x is not None and len(x) > 0),
                    ('StudyInstanceUID', lambda x: x is not None and len(x) > 0),
                    ('SeriesInstanceUID', lambda x: x is not None and len(x) > 0),
                    ('Modality', lambda x: x == overrides['Modality']),
                    ('PatientName', lambda x: x is not None),
                    ('PatientID', lambda x: x is not None),
                    ('StudyDate', lambda x: x is not None and len(x) == 8),
                    ('StudyTime', lambda x: x is not None and len(x) >= 6),
                    ('ImageOrientationPatient', lambda x: len(x) == 6),
                    ('ImagePositionPatient', lambda x: len(x) == 3),
                    ('PixelSpacing', lambda x: len(x) == 2),
                    ('Rows', lambda x: x == 512),
                    ('Columns', lambda x: x == 512),
                    ('BitsAllocated', lambda x: x == 16),
                    ('PhotometricInterpretation', lambda x: x == 'MONOCHROME2'),
                    ('PixelData', lambda x: x is not None and len(x) > 0),
                ]
                
                passed = 0
                total = len(checks)
                
                for attr_name, check_func in checks:
                    try:
                        attr_value = getattr(ds, attr_name)
                        if check_func(attr_value):
                            passed += 1
                        else:
                            print(f"  ⚠️  {attr_name}: FAILED check")
                    except AttributeError:
                        print(f"  ❌ {attr_name}: MISSING")
                
                # Check file meta information
                meta_checks = [
                    ('MediaStorageSOPClassUID', lambda x: x is not None),
                    ('MediaStorageSOPInstanceUID', lambda x: x is not None),
                    ('TransferSyntaxUID', lambda x: x is not None),
                ]
                
                for attr_name, check_func in meta_checks:
                    try:
                        attr_value = getattr(ds.file_meta, attr_name)
                        if check_func(attr_value):
                            passed += 1
                        else:
                            print(f"  ⚠️  file_meta.{attr_name}: FAILED check")
                    except AttributeError:
                        print(f"  ❌ file_meta.{attr_name}: MISSING")
                
                total += len(meta_checks)
                
                # Summary
                compatibility = (passed / total) * 100
                status = "✅" if compatibility >= 90 else "⚠️" if compatibility >= 75 else "❌"
                print(f"  {status} PACS Compatibility: {compatibility:.1f}% ({passed}/{total} checks passed)")
                
                # Check pixel data integrity
                pixel_array = ds.pixel_array
                print(f"  📊 Pixel data: {pixel_array.shape}, range: {pixel_array.min()}-{pixel_array.max()}")
                
                file_size = os.path.getsize(file_path) / 1024  # KB
                print(f"  📁 File size: {file_size:.1f} KB")
    
    print('\\n✅ DICOM PACS compatibility testing completed!')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
