#!/usr/bin/env python3
"""
PACS Compatibility Validation Script
Tests enhanced DICOM generation for Brit PACS compatibility
"""

import sys
import os
import logging
import tempfile
import shutil
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.util.dicom_generator import create_study_files
import pydicom

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_dicom_file(filepath):
    """Comprehensive DICOM validation for PACS compatibility."""
    
    print(f"\n=== VALIDATING: {os.path.basename(filepath)} ===")
    
    try:
        # Load DICOM file
        ds = pydicom.dcmread(filepath)
        
        # Core DICOM validation
        validation_results = {
            'file_valid': True,
            'pacs_compatible': True,
            'issues': [],
            'warnings': []
        }
        
        # 1. Check essential DICOM attributes
        essential_attrs = [
            'SOPClassUID', 'SOPInstanceUID', 'StudyInstanceUID', 'SeriesInstanceUID',
            'PatientID', 'PatientName', 'StudyDate', 'StudyTime',
            'Modality', 'SeriesNumber', 'InstanceNumber'
        ]
        
        missing_attrs = []
        for attr in essential_attrs:
            if not hasattr(ds, attr) or getattr(ds, attr) == '':
                missing_attrs.append(attr)
        
        if missing_attrs:
            validation_results['pacs_compatible'] = False
            validation_results['issues'].append(f"Missing essential attributes: {missing_attrs}")
        
        # 2. Check pixel data attributes if present
        if hasattr(ds, 'PixelData'):
            pixel_attrs = ['Rows', 'Columns', 'BitsAllocated', 'BitsStored', 'HighBit',
                          'PixelRepresentation', 'PhotometricInterpretation', 'SamplesPerPixel']
            
            missing_pixel_attrs = []
            for attr in pixel_attrs:
                if not hasattr(ds, attr):
                    missing_pixel_attrs.append(attr)
            
            if missing_pixel_attrs:
                validation_results['pacs_compatible'] = False
                validation_results['issues'].append(f"Missing pixel attributes: {missing_pixel_attrs}")
            
            # Check pixel data size consistency
            if hasattr(ds, 'Rows') and hasattr(ds, 'Columns') and hasattr(ds, 'BitsAllocated'):
                expected_size = ds.Rows * ds.Columns * (ds.BitsAllocated // 8)
                actual_size = len(ds.PixelData)
                
                if actual_size != expected_size:
                    validation_results['pacs_compatible'] = False
                    validation_results['issues'].append(
                        f"Pixel data size mismatch: expected {expected_size}, got {actual_size}")
                
                print(f"  Pixel Data: {ds.Rows}x{ds.Columns}, {ds.BitsAllocated}-bit, {actual_size} bytes")
        
        # 3. Check transfer syntax
        if hasattr(ds, 'file_meta') and hasattr(ds.file_meta, 'TransferSyntaxUID'):
            transfer_syntax = ds.file_meta.TransferSyntaxUID
            print(f"  Transfer Syntax: {transfer_syntax}")
            
            # Check for common PACS-compatible transfer syntaxes
            compatible_syntaxes = [
                '1.2.840.10008.1.2',      # Implicit VR Little Endian
                '1.2.840.10008.1.2.1',    # Explicit VR Little Endian
                '1.2.840.10008.1.2.2'     # Explicit VR Big Endian
            ]
            
            if str(transfer_syntax) not in compatible_syntaxes:
                validation_results['warnings'].append(f"Uncommon transfer syntax: {transfer_syntax}")
        
        # 4. Check modality-specific attributes
        modality = getattr(ds, 'Modality', 'Unknown')
        print(f"  Modality: {modality}")
        
        if modality == 'CT':
            ct_attrs = ['ImageOrientationPatient', 'ImagePositionPatient', 'SliceThickness']
            missing_ct = [attr for attr in ct_attrs if not hasattr(ds, attr)]
            if missing_ct:
                validation_results['warnings'].append(f"Missing CT attributes: {missing_ct}")
        
        elif modality == 'MR':
            mr_attrs = ['ImageOrientationPatient', 'ImagePositionPatient', 'SliceThickness']
            missing_mr = [attr for attr in mr_attrs if not hasattr(ds, attr)]
            if missing_mr:
                validation_results['warnings'].append(f"Missing MR attributes: {missing_mr}")
        
        # 5. Check windowing parameters
        if hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
            print(f"  Windowing: Center={ds.WindowCenter}, Width={ds.WindowWidth}")
        else:
            validation_results['warnings'].append("Missing windowing parameters")
        
        # 6. Check character set
        if hasattr(ds, 'SpecificCharacterSet'):
            print(f"  Character Set: {ds.SpecificCharacterSet}")
        else:
            validation_results['warnings'].append("Missing SpecificCharacterSet")
        
        # 7. Print file size and basic info
        file_size = os.path.getsize(filepath)
        print(f"  File Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        if hasattr(ds, 'PatientName'):
            print(f"  Patient: {ds.PatientName}")
        
        if hasattr(ds, 'StudyDescription'):
            print(f"  Study: {ds.StudyDescription}")
        
        # Summary
        if validation_results['pacs_compatible']:
            print("  ✅ PACS Compatible")
        else:
            print("  ❌ PACS Issues Found")
        
        if validation_results['issues']:
            print("  🔴 CRITICAL ISSUES:")
            for issue in validation_results['issues']:
                print(f"    - {issue}")
        
        if validation_results['warnings']:
            print("  🟡 WARNINGS:")
            for warning in validation_results['warnings']:
                print(f"    - {warning}")
        
        return validation_results
        
    except Exception as e:
        print(f"  ❌ VALIDATION FAILED: {str(e)}")
        return {
            'file_valid': False,
            'pacs_compatible': False,
            'issues': [f"File validation error: {str(e)}"],
            'warnings': []
        }

def test_enhanced_dicom_generation():
    """Test the enhanced DICOM generation with various modalities."""
    
    print("=== ENHANCED DICOM GENERATION TEST ===")
    
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test cases with different modalities and study descriptions
        test_cases = [
            {
                'description': 'CT CHEST W/O CONTRAST',
                'modality': 'CT',
                'body_part': 'CHEST'
            },
            {
                'description': 'MRI LUMBAR SPINE W/O',
                'modality': 'MR', 
                'body_part': 'LSPINE'
            },
            {
                'description': 'CHEST X-RAY PA',
                'modality': 'DX',
                'body_part': 'CHEST'
            },
            {
                'description': 'ABDOMINAL ULTRASOUND',
                'modality': 'US',
                'body_part': 'ABDOMEN'
            }
        ]
        
        all_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i}: {test_case['description']} ---")
            
            try:
                # Generate DICOM files using the correct function and parameters
                study_dir = temp_path / f"test_{i}"
                study_dir.mkdir(exist_ok=True)
                
                overrides = {
                    'PatientID': f"TEST{i:03d}",
                    'PatientName': f"Test^Patient^{i}",
                    'AccessionNumber': f"ACC{i:06d}",
                    'StudyDescription': test_case['description'],
                    'Modality': test_case['modality'],
                    'BodyPartExamined': test_case['body_part']
                }
                
                generated_files = create_study_files(
                    output_dir=str(study_dir),
                    num_images=3,  # Generate 3 images for cross-sectional
                    overrides=overrides,
                    generate_pixels=True
                )
                
                print(f"Generated {len(generated_files)} files")
                
                # Validate each generated file
                case_results = []
                for filepath in generated_files:
                    result = validate_dicom_file(filepath)
                    case_results.append(result)
                
                all_results.append({
                    'test_case': test_case,
                    'files_generated': len(generated_files),
                    'validation_results': case_results
                })
                
            except Exception as e:
                print(f"❌ Test case failed: {str(e)}")
                all_results.append({
                    'test_case': test_case,
                    'files_generated': 0,
                    'validation_results': [],
                    'error': str(e)
                })
        
        # Generate summary report
        print("\n" + "="*60)
        print("VALIDATION SUMMARY REPORT")
        print("="*60)
        
        total_files = 0
        compatible_files = 0
        total_issues = 0
        total_warnings = 0
        
        for i, result in enumerate(all_results, 1):
            test_case = result['test_case']
            print(f"\nTest {i}: {test_case['description']}")
            
            if 'error' in result:
                print(f"  ❌ FAILED: {result['error']}")
                continue
            
            files_generated = result['files_generated']
            validation_results = result['validation_results']
            
            total_files += files_generated
            
            compatible_count = sum(1 for v in validation_results if v['pacs_compatible'])
            compatible_files += compatible_count
            
            issues_count = sum(len(v['issues']) for v in validation_results)
            warnings_count = sum(len(v['warnings']) for v in validation_results)
            
            total_issues += issues_count
            total_warnings += warnings_count
            
            print(f"  Files Generated: {files_generated}")
            print(f"  PACS Compatible: {compatible_count}/{files_generated}")
            print(f"  Issues: {issues_count}, Warnings: {warnings_count}")
        
        print(f"\nOVERALL RESULTS:")
        print(f"  Total Files: {total_files}")
        print(f"  PACS Compatible: {compatible_files}/{total_files} ({100*compatible_files/total_files if total_files > 0 else 0:.1f}%)")
        print(f"  Total Issues: {total_issues}")
        print(f"  Total Warnings: {total_warnings}")
        
        if compatible_files == total_files and total_issues == 0:
            print("\n🎉 ALL TESTS PASSED - Ready for PACS deployment!")
        elif total_issues == 0:
            print(f"\n✅ All files are PACS compatible (with {total_warnings} warnings)")
        else:
            print(f"\n⚠️  Found {total_issues} critical issues that must be fixed")
        
        return all_results

if __name__ == "__main__":
    print("PACS Compatibility Validation for Enhanced DICOM Generation")
    print("=" * 60)
    
    try:
        results = test_enhanced_dicom_generation()
        
        # Return appropriate exit code
        total_issues = sum(len(v.get('issues', [])) for result in results 
                          for v in result.get('validation_results', []))
        
        if total_issues == 0:
            print("\n✅ Validation completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Validation failed with {total_issues} critical issues")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test script failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
