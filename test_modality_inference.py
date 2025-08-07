#!/usr/bin/env python3

"""
Quick test script to verify modality inference logic works correctly.
"""

import sys
import os

# Add the app directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_modality_inference():
    """Test the modality inference logic with various study descriptions."""
    
    # Mock the simulation runner class
    class MockSimulationRunner:
        def _log_event(self, step_order, patient_iter, repeat_iter, status, details):
            print(f"[{status}] {details}")
        
        def _infer_modality_from_description(self, description, step, patient_iter, repeat_iter):
            """
            Intelligently infer DICOM modality from study description text.
            Maps common procedure names/keywords to appropriate DICOM modality codes.
            """
            if not description:
                return None
                
            # Convert to uppercase for case-insensitive matching
            desc_upper = description.upper()
            
            # Define modality mapping patterns - order matters (most specific first)
            modality_patterns = [
                # PET/CT hybrid (must come before CT and PET)
                (['PET/CT', 'PET-CT'], 'PT'),
                
                # MRI patterns
                (['MRI', 'MAGNETIC RESONANCE', 'MR '], 'MR'),
                
                # CT patterns  
                (['CT ', 'COMPUTED TOMOGRAPHY', 'CAT SCAN'], 'CT'),
                
                # Nuclear Medicine patterns
                (['PET', 'SPECT', 'NUCLEAR MED', 'SCINTIGRAPHY', 'BONE SCAN'], 'NM'),
                
                # Ultrasound patterns
                (['ULTRASOUND', 'ECHO', 'DOPPLER', 'US ', 'SONOGRAPHY'], 'US'),
                
                # Digital Radiography patterns
                (['X-RAY', 'XRAY', 'RADIOGRAPH', 'CHEST PA', 'BONE SURVEY'], 'DX'),
                
                # Computed Radiography patterns
                (['CR ', 'COMPUTED RADIOGRAPHY'], 'CR'),
                
                # Mammography patterns
                (['MAMMOGRAM', 'MAMMO', 'BREAST'], 'MG'),
                
                # Angiography patterns
                (['ANGIOGRAM', 'ANGIO', 'ARTERIOGRAM', 'DSA'], 'XA'),
                
                # Fluoroscopy patterns
                (['FLUORO', 'BARIUM', 'UPPER GI', 'LOWER GI'], 'RF'),
                
                # Endoscopy patterns
                (['ENDOSCOPY', 'COLONOSCOPY', 'EGD', 'BRONCHOSCOPY'], 'ES'),
                
                # OCT patterns
                (['OCT', 'OPTICAL COHERENCE'], 'OCT'),
            ]
            
            # Check each pattern
            for keywords, modality in modality_patterns:
                for keyword in keywords:
                    if keyword in desc_upper:
                        self._log_event(0, 1, 1, 'DEBUG', f"Matched keyword '{keyword}' -> modality '{modality}'")
                        return modality
            
            # Special case: if description contains anatomical regions, make reasonable assumptions
            anatomy_patterns = [
                (['SPINE', 'LUMBAR', 'CERVICAL', 'THORACIC', 'VERTEBRA'], 'MR'),  # Spine studies often MRI
                (['BRAIN', 'HEAD', 'SKULL'], 'MR'),  # Brain studies often MRI
                (['CHEST', 'LUNG', 'PULMONARY'], 'DX'),  # Chest studies often X-ray
                (['ABDOMEN', 'PELVIS'], 'CT'),  # Abdominal studies often CT
            ]
            
            for keywords, modality in anatomy_patterns:
                for keyword in keywords:
                    if keyword in desc_upper:
                        self._log_event(0, 1, 1, 'DEBUG', f"Anatomical inference: '{keyword}' -> modality '{modality}'")
                        return modality
            
            # No match found
            self._log_event(0, 1, 1, 'DEBUG', f"Could not infer modality from description: '{description}'")
            return None
    
    # Test cases
    test_cases = [
        ("MRI LUMBAR SPINE W/O", "MR"),
        ("CT CHEST WITH CONTRAST", "CT"),
        ("CHEST X-RAY PA AND LATERAL", "DX"),
        ("ULTRASOUND ABDOMEN", "US"),
        ("PET/CT WHOLE BODY", "PT"),
        ("MAMMOGRAM BILATERAL", "MG"),
        ("BRAIN MRI", "MR"),
        ("SPINE LUMBAR", "MR"),  # Should infer MR from anatomy
        ("CHEST PA", "DX"),  # Should infer DX from anatomy
        ("SOME UNKNOWN PROCEDURE", None),  # Should return None
    ]
    
    runner = MockSimulationRunner()
    
    print("Testing modality inference logic:")
    print("=" * 50)
    
    for description, expected in test_cases:
        result = runner._infer_modality_from_description(description, None, 1, 1)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{description}' -> Expected: {expected}, Got: {result}")
        print()

if __name__ == "__main__":
    test_modality_inference()
