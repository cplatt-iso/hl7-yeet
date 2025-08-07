#!/usr/bin/env python3
"""
Test modality detection variety across different study descriptions
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.simulation_runner import SimulationRunner

def test_modality_detection():
    """Test modality detection with various study descriptions"""
    
    runner = SimulationRunner("fake_config")
    
    # Test cases with expected modalities
    test_cases = [
        ("MRI LUMBAR SPINE W/O", "MR"),
        ("CT HEAD WITHOUT CONTRAST", "CT"),
        ("CHEST X-RAY", "DX"),
        ("MR BRAIN WITH AND WITHOUT CONTRAST", "MR"),
        ("CT CHEST ABDOMEN PELVIS WITH CONTRAST", "CT"),
        ("XRAY CHEST PA AND LATERAL", "DX"),
        ("MRI CERVICAL SPINE", "MR"),
        ("CT ANGIOGRAM HEAD AND NECK", "CT"),
        ("DX FOOT 3 VIEWS", "DX"),
        ("MAGNETIC RESONANCE THORACIC SPINE", "MR"),
        ("COMPUTED TOMOGRAPHY CHEST", "CT"),
        ("RADIOGRAPH KNEE AP LAT", "DX"),
        ("ULTRASOUND ABDOMEN COMPLETE", "US"),
        ("MAMMOGRAPHY BILATERAL", "MG"),
        ("NUCLEAR MEDICINE BONE SCAN", "NM"),
        ("PET CT WHOLE BODY", "PT"),
        ("FLUOROSCOPY UPPER GI", "RF"),
        ("ECHOCARDIOGRAM COMPLETE", "US"),
        ("SPINE MRI LUMBAR", "MR"),
        ("HEAD CT WITHOUT IV CONTRAST", "CT")
    ]
    
    print("Testing Modality Detection Variety")
    print("=" * 50)
    
    correct = 0
    total = len(test_cases)
    
    for description, expected in test_cases:
        detected = runner._infer_modality_from_description(description)
        status = "✓" if detected == expected else "✗"
        print(f"{status} '{description}' → {detected} (expected: {expected})")
        if detected == expected:
            correct += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {correct}/{total} correct ({correct/total*100:.1f}%)")
    
    if correct == total:
        print("🎉 All modalities detected correctly! System provides excellent variety.")
    else:
        print(f"⚠️  {total-correct} mismatches detected.")

if __name__ == "__main__":
    test_modality_detection()
