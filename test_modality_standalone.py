#!/usr/bin/env python3
"""
Test modality detection variety - standalone version
"""

def _infer_modality_from_description(description: str) -> str:
    """Enhanced modality inference from study description with comprehensive patterns."""
    description = description.upper()
    
    # MR/MRI patterns (check first since MR is often part of other words)
    mr_patterns = [
        'MRI', 'MR ', 'MAGNETIC RESONANCE', 'MAGNETOM', 'SIGNA',
        'MR BRAIN', 'MR SPINE', 'MR CARDIAC', 'MR ANGIO',
        'FMRI', 'DIFFUSION', 'PERFUSION', 'SPECTROSCOPY'
    ]
    
    # CT patterns
    ct_patterns = [
        'CT ', 'COMPUTED TOMOGRAPHY', 'CAT SCAN', 'SPIRAL CT', 'HELICAL CT',
        'CT HEAD', 'CT CHEST', 'CT ABDOMEN', 'CT PELVIS', 'CTA', 'CTV',
        'MULTISLICE', 'MSCT', 'HRCT', 'CONTRAST CT', 'CT ANGIO'
    ]
    
    # X-ray/Radiography patterns
    xray_patterns = [
        'X-RAY', 'XRAY', 'X RAY', 'RADIOGRAPH', 'PLAIN FILM', 'BONE SURVEY',
        'CHEST PA', 'CHEST AP', 'CHEST LAT', 'LATERAL', 'AP VIEW', 'PA VIEW',
        'BONE AGE', 'SKELETAL SURVEY', 'ORTHOPEDIC', 'TRAUMA SERIES',
        'DX ', 'CR ', 'DIGITAL RADIOGRAPHY', 'COMPUTED RADIOGRAPHY'
    ]
    
    # Nuclear Medicine patterns
    nm_patterns = [
        'NUCLEAR MEDICINE', 'NM ', 'BONE SCAN', 'THYROID SCAN', 'CARDIAC PERFUSION',
        'GALLIUM', 'INDIUM', 'TECHNETIUM', 'THALLIUM', 'SESTAMIBI', 'HIDA',
        'RENOGRAM', 'LUNG PERFUSION', 'VENTILATION', 'OCTREOTIDE'
    ]
    
    # PET patterns
    pet_patterns = [
        'PET', 'POSITRON EMISSION', 'FDG', 'F-18', 'FLUORODEOXYGLUCOSE',
        'PET/CT', 'PET CT', 'ONCOLOGY PET', 'CARDIAC PET'
    ]
    
    # Ultrasound patterns
    us_patterns = [
        'ULTRASOUND', 'ULTRASONOGRAPHY', 'US ', 'SONOGRAM', 'DOPPLER',
        'ECHOCARDIOGRAM', 'ECHO', 'CARDIAC ECHO', 'ABDOMINAL US',
        'PELVIC US', 'OBSTETRIC', 'GYNECOLOGIC', 'VASCULAR US',
        'CAROTID DUPLEX', 'VENOUS DUPLEX', 'ARTERIAL DUPLEX'
    ]
    
    # Mammography patterns
    mg_patterns = [
        'MAMMOGRAPHY', 'MAMMOGRAM', 'MAMMO', 'BREAST IMAGING',
        'TOMOSYNTHESIS', 'DIGITAL BREAST', 'SCREENING MAMMO',
        'DIAGNOSTIC MAMMO', 'BILATERAL MAMMO'
    ]
    
    # Fluoroscopy patterns
    rf_patterns = [
        'FLUOROSCOPY', 'FLUORO', 'RF ', 'UPPER GI', 'LOWER GI', 'BARIUM',
        'SWALLOW STUDY', 'ESOPHAGRAM', 'UGI', 'SBFT', 'BE ', 'BARIUM ENEMA',
        'CYSTOGRAM', 'URETHROGRAM', 'ARTHROGRAM', 'MYELOGRAM',
        'INTERVENTIONAL', 'ANGIOGRAPHY', 'CARDIAC CATH'
    ]
    
    # Angiography patterns (can be various modalities)
    angio_patterns = [
        'ANGIOGRAPHY', 'ANGIOGRAM', 'ANGIO', 'ARTERIOGRAM', 'VENOGRAM',
        'PULMONARY ANGIO', 'RENAL ANGIO', 'CEREBRAL ANGIO', 'CORONARY ANGIO'
    ]
    
    # Check patterns in order of specificity
    for pattern in mr_patterns:
        if pattern in description:
            return 'MR'
    
    for pattern in ct_patterns:
        if pattern in description:
            return 'CT'
    
    for pattern in pet_patterns:
        if pattern in description:
            return 'PT'
    
    for pattern in nm_patterns:
        if pattern in description:
            return 'NM'
    
    for pattern in us_patterns:
        if pattern in description:
            return 'US'
    
    for pattern in mg_patterns:
        if pattern in description:
            return 'MG'
    
    for pattern in rf_patterns:
        if pattern in description:
            return 'RF'
    
    for pattern in xray_patterns:
        if pattern in description:
            return 'DX'
    
    # If angiography is mentioned but no specific modality, default to fluoroscopy
    for pattern in angio_patterns:
        if pattern in description:
            return 'RF'
    
    # Default fallback
    return 'DX'

def test_modality_detection():
    """Test modality detection with various study descriptions"""
    
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
        detected = _infer_modality_from_description(description)
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
