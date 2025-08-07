#!/usr/bin/env python3
"""
PACS Validation Script - Checks DICOM files for common PACS compatibility issues
that cause java.io.EOFException and PROCESSING_FAILURE errors.
"""

import sys
import os
import pydicom
import numpy as np

def validate_dicom_for_pacs(file_path):
    """
    Validate a DICOM file for PACS compatibility.
    Returns (is_valid, issues_found, recommendations)
    """
    issues = []
    recommendations = []
    
    try:
        ds = pydicom.dcmread(file_path)
        
        # Check 1: File meta information
        if not hasattr(ds, 'file_meta') or ds.file_meta is None:
            issues.append("Missing file meta information")
            recommendations.append("Add proper file_meta with TransferSyntaxUID")
        
        # Check 2: Transfer Syntax
        if hasattr(ds, 'file_meta') and hasattr(ds.file_meta, 'TransferSyntaxUID'):
            ts = ds.file_meta.TransferSyntaxUID
            if ts not in ['1.2.840.10008.1.2', '1.2.840.10008.1.2.1', '1.2.840.10008.1.2.2']:
                issues.append(f"Non-standard transfer syntax: {ts}")
                recommendations.append("Use ImplicitVRLittleEndian (1.2.840.10008.1.2)")
        else:
            issues.append("Missing TransferSyntaxUID")
        
        # Check 3: Required DICOM attributes
        required_attrs = [
            'SOPClassUID', 'SOPInstanceUID', 'StudyInstanceUID', 'SeriesInstanceUID',
            'Modality', 'PatientName', 'PatientID', 'StudyDate', 'StudyTime'
        ]
        
        for attr in required_attrs:
            if not hasattr(ds, attr) or getattr(ds, attr) is None:
                issues.append(f"Missing required attribute: {attr}")
                recommendations.append(f"Add {attr} attribute")
        
        # Check 4: Pixel data attributes (if pixel data exists)
        if hasattr(ds, 'PixelData'):
            pixel_attrs = [
                'Rows', 'Columns', 'BitsAllocated', 'BitsStored', 'HighBit',
                'PixelRepresentation', 'SamplesPerPixel', 'PhotometricInterpretation'
            ]
            
            for attr in pixel_attrs:
                if not hasattr(ds, attr):
                    issues.append(f"Missing pixel attribute: {attr}")
                    recommendations.append(f"Add {attr} for pixel data")
            
            # Check pixel data size consistency
            if all(hasattr(ds, attr) for attr in ['Rows', 'Columns', 'BitsAllocated']):
                expected_size = ds.Rows * ds.Columns * (ds.BitsAllocated // 8)
                actual_size = len(ds.PixelData)
                
                if expected_size != actual_size:
                    issues.append(f"Pixel data size mismatch: expected {expected_size}, got {actual_size}")
                    recommendations.append("Ensure pixel data matches declared dimensions and bit depth")
            
            # Check byte order for multi-byte pixels
            if hasattr(ds, 'BitsAllocated') and ds.BitsAllocated > 8:
                # Test if pixel data is little-endian
                try:
                    test_array = np.frombuffer(ds.PixelData[:8], dtype='<u2')
                    if len(test_array) == 0:
                        issues.append("Pixel data appears corrupted or empty")
                except:
                    issues.append("Pixel data byte order may be incorrect")
                    recommendations.append("Ensure little-endian byte order for multi-byte pixels")
        
        # Check 5: Spatial attributes for cross-sectional imaging
        if hasattr(ds, 'Modality') and ds.Modality in ['CT', 'MR']:
            spatial_attrs = ['ImageOrientationPatient', 'ImagePositionPatient', 'PixelSpacing']
            for attr in spatial_attrs:
                if not hasattr(ds, attr):
                    issues.append(f"Missing spatial attribute for {ds.Modality}: {attr}")
                    recommendations.append(f"Add {attr} for proper PACS spatial handling")
        
        # Check 6: Windowing attributes for grayscale images
        if hasattr(ds, 'PhotometricInterpretation') and 'MONOCHROME' in ds.PhotometricInterpretation:
            if not (hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth')):
                issues.append("Missing windowing attributes for monochrome image")
                recommendations.append("Add WindowCenter and WindowWidth for proper display")
        
        is_valid = len(issues) == 0
        return is_valid, issues, recommendations
        
    except Exception as e:
        return False, [f"Failed to read DICOM file: {e}"], ["Ensure file is valid DICOM format"]

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 pacs_validator.py <dicom_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    print(f"Validating DICOM file for PACS compatibility: {file_path}")
    print("="*60)
    
    is_valid, issues, recommendations = validate_dicom_for_pacs(file_path)
    
    if is_valid:
        print("✓ PACS COMPATIBILITY: PASSED")
        print("  File should be compatible with PACS systems")
    else:
        print("✗ PACS COMPATIBILITY: ISSUES FOUND")
        print(f"  Found {len(issues)} potential compatibility issues:")
        
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
        
        print("\nRecommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"    {i}. {rec}")
    
    print("="*60)
    return 0 if is_valid else 1

if __name__ == "__main__":
    sys.exit(main())
