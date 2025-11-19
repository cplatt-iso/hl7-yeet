# EXAMGEN-3.0: Initial Catalog Population

**Status:** Not Started  
**Created:** 2025-11-18  
**Previous:** [EXAMGEN-2.2](EXAMGEN-2.2-Factory-API-Design.md)  
**Next:** [EXAMGEN-3.1](EXAMGEN-3.1-Vocabulary-Integration.md)

## Purpose

Create the initial `app/catalog/exams.json` file with a curated set of 50-100 high-fidelity ExamSpec entries covering common modalities and use cases.

## Scope & Priorities

### Phase 1: Core Modalities (Target: 50 exams)

| Modality | Target Count | Rationale |
|----------|-------------|-----------|
| **CT** | 15 | High volume, diverse protocols (contrast timing, body regions) |
| **MR** | 15 | Complex protocols (sequences, planes), laterality variations |
| **DX** | 10 | Simple but high frequency, multiple views |
| **US** | 5 | Common exams (abdomen, OB, vascular) |
| **MG** | 3 | Standardized views, female-only |
| **NM** | 2 | Basic nuclear medicine (bone scan, cardiac) |

### Selection Criteria

1. **Clinical Frequency:** Focus on top 80% of real-world exam volumes
2. **Technical Diversity:** Cover key variations (contrast, laterality, multi-series)
3. **Workflow Coverage:** Include outpatient, emergency, inpatient settings
4. **Educational Value:** Represent different anatomy systems (neuro, MSK, body, etc.)

## Data Sources

### 1. ACR Appropriateness Criteria
- URL: https://www.acr.org/Clinical-Resources/ACR-Appropriateness-Criteria
- Usage: Common exam indications and typical protocols

### 2. RadiologyInfo.org Exam Catalog
- URL: https://www.radiologyinfo.org/en/info/safety-index
- Usage: Patient-friendly descriptions, procedure durations

### 3. CMS Physician Fee Schedule (CPT Codes)
- URL: https://www.cms.gov/medicare/payment/fee-schedules/physician
- Usage: CPT code → exam name mappings, relative frequency data

### 4. LOINC Radiology Playbook
- URL: https://loinc.org/usage/obs/radiology/
- Usage: LOINC codes for structured reporting

### 5. RadLex Lexicon
- URL: https://radlex.org/
- Usage: Body part ontology, standardized terminology

## Catalog Structure

### Initial File Template

```json
{
  "schema_version": "1.0",
  "catalog_version": "2025.1.0",
  "last_updated": "2025-01-18T00:00:00Z",
  "metadata": {
    "total_exams": 50,
    "modalities": ["CT", "MR", "DX", "US", "MG", "NM"],
    "maintainer": "HL7 Yeeter Project",
    "license": "MIT",
    "data_sources": [
      "ACR Appropriateness Criteria",
      "CMS Physician Fee Schedule",
      "LOINC Radiology Playbook"
    ]
  },
  "exams": [
    /* Array of ExamSpec objects */
  ]
}
```

## Example Entries

### CT Head Without Contrast (Emergency)

```json
{
  "id": "CT-HEAD-WO",
  "version": "1.0",
  "modality": "CT",
  "name": "CT Head Without Contrast",
  "description": "CT HEAD W/O CONTRAST",
  "body_part": "HEAD",
  "laterality": "",
  "indication_template": "Acute headache, rule out intracranial hemorrhage",
  "contrast": "none",
  "procedure_codes": [
    {
      "system": "CPT",
      "code": "70450",
      "display": "Computed tomography, head or brain; without contrast material"
    },
    {
      "system": "LOINC",
      "code": "24727-0",
      "display": "CT Head"
    }
  ],
  "series": [
    {
      "protocol_name": "HEAD STD",
      "series_description": "HEAD 5.0 STD",
      "instances": 35,
      "acquisition_duration_sec": 180,
      "sequence_name": "head_std_axial"
    }
  ],
  "estimated_duration_min": 5.0,
  "min_age": 0,
  "required_sex": null,
  "frequency_weight": 3.0,
  "setting": ["emergency", "inpatient"],
  "custom_metadata": {
    "department": "Neuroradiology",
    "contrast_contraindications": "None for non-contrast"
  }
}
```

### MRI Knee Right Without Contrast (Outpatient)

```json
{
  "id": "MR-KNEE-RIGHT-WO",
  "version": "1.0",
  "modality": "MR",
  "name": "MRI Knee Right Without Contrast",
  "description": "MRI KNEE RIGHT W/O CONTRAST",
  "body_part": "KNEE",
  "laterality": "R",
  "indication_template": "Right knee pain, evaluate for meniscal tear",
  "contrast": "none",
  "procedure_codes": [
    {
      "system": "CPT",
      "code": "73721",
      "display": "Magnetic resonance (eg, proton) imaging, any joint of lower extremity; without contrast material"
    },
    {
      "system": "LOINC",
      "code": "37017-7",
      "display": "MR Lower extremity - right joint"
    }
  ],
  "series": [
    {
      "protocol_name": "SAG PD",
      "series_description": "SAG PD KNEE",
      "instances": 25,
      "acquisition_duration_sec": 240,
      "sequence_name": "pd_tse_sag"
    },
    {
      "protocol_name": "SAG T2 FS",
      "series_description": "SAG T2 FS KNEE",
      "instances": 28,
      "acquisition_duration_sec": 260,
      "sequence_name": "t2_tse_fs_sag"
    },
    {
      "protocol_name": "COR PD FS",
      "series_description": "COR PD FS KNEE",
      "instances": 22,
      "acquisition_duration_sec": 220,
      "sequence_name": "pd_tse_fs_cor"
    },
    {
      "protocol_name": "AX PD FS",
      "series_description": "AX PD FS KNEE",
      "instances": 30,
      "acquisition_duration_sec": 240,
      "sequence_name": "pd_tse_fs_ax"
    }
  ],
  "estimated_duration_min": 25.0,
  "min_age": 5,
  "required_sex": null,
  "frequency_weight": 2.0,
  "setting": ["outpatient"],
  "custom_metadata": {
    "department": "MSK",
    "requires_positioning_device": "knee coil"
  }
}
```

### Chest X-Ray 2 Views (High Volume)

```json
{
  "id": "DX-CHEST-PA-LAT",
  "version": "1.0",
  "modality": "DX",
  "name": "Chest X-Ray 2 Views",
  "description": "CHEST 2 VIEWS PA AND LATERAL",
  "body_part": "CHEST",
  "laterality": "",
  "indication_template": "Cough and shortness of breath, rule out pneumonia",
  "contrast": "none",
  "procedure_codes": [
    {
      "system": "CPT",
      "code": "71046",
      "display": "Radiologic examination, chest; 2 views"
    },
    {
      "system": "LOINC",
      "code": "36643-5",
      "display": "XR Chest 2 Views"
    }
  ],
  "series": [
    {
      "protocol_name": "CHEST PA",
      "series_description": "CHEST PA",
      "instances": 1,
      "acquisition_duration_sec": 5,
      "sequence_name": null
    },
    {
      "protocol_name": "CHEST LAT",
      "series_description": "CHEST LATERAL",
      "instances": 1,
      "acquisition_duration_sec": 5,
      "sequence_name": null
    }
  ],
  "estimated_duration_min": 5.0,
  "min_age": 0,
  "required_sex": null,
  "frequency_weight": 5.0,
  "setting": ["outpatient", "inpatient", "emergency"],
  "custom_metadata": {
    "department": "General Radiology",
    "portable_capable": "true"
  }
}
```

## Complete Exam List (Phase 1)

### CT Exams (15)
1. CT-HEAD-WO - Head without contrast (emergency stroke/trauma)
2. CT-HEAD-W - Head with contrast (tumor/infection)
3. CT-CSPINE-WO - Cervical spine without contrast (trauma)
4. CT-CHEST-WO - Chest without contrast (lung nodule)
5. CT-CHEST-W - Chest with contrast (PE protocol)
6. CT-ABDPELVIS-WO - Abdomen/pelvis without contrast (stones)
7. CT-ABDPELVIS-W - Abdomen/pelvis with contrast (single phase)
8. CT-ABDPELVIS-3PHASE - Abdomen/pelvis 3-phase (oncology)
9. CT-CHEST-ABD-PELVIS - Chest/abdomen/pelvis with contrast (trauma)
10. CT-ANGIO-NECK - CTA neck (stroke workup)
11. CT-ANGIO-CHEST - CTA chest (aortic dissection)
12. CT-COLONOGRAPHY - CT colonography (screening)
13. CT-SINUS - Sinus without contrast
14. CT-EXTREMITY - Extremity without contrast (fracture)
15. CT-CARDIAC - Cardiac CT angiography

### MR Exams (15)
1. MR-BRAIN-WO - Brain without contrast (headache)
2. MR-BRAIN-W - Brain with contrast (tumor)
3. MR-BRAIN-STROKE - Brain stroke protocol (DWI/PWI)
4. MR-CSPINE-WO - Cervical spine without contrast
5. MR-TSPINE-WO - Thoracic spine without contrast
6. MR-LSPINE-WO - Lumbar spine without contrast
7. MR-KNEE-RIGHT-WO - Knee right without contrast
8. MR-KNEE-LEFT-WO - Knee left without contrast
9. MR-SHOULDER-RIGHT-WO - Shoulder right without contrast
10. MR-SHOULDER-LEFT-WO - Shoulder left without contrast
11. MR-ABDOMEN-W - Abdomen with contrast (liver protocol)
12. MR-PELVIS-W - Pelvis with contrast
13. MR-MRCP - MRCP (biliary tree)
14. MR-PROSTATE - Prostate MRI (male only)
15. MR-BREAST-BILATERAL - Breast bilateral with contrast (female only)

### DX Exams (10)
1. DX-CHEST-PA-LAT - Chest 2 views
2. DX-CHEST-PA - Chest PA single view
3. DX-ABDOMEN-2VIEW - Abdomen 2 views (supine/upright)
4. DX-SPINE-LSPINE - Lumbar spine 2-3 views
5. DX-SPINE-CSPINE - Cervical spine 3-4 views
6. DX-HAND-RIGHT - Hand right 3 views
7. DX-FOOT-RIGHT - Foot right 3 views
8. DX-KNEE-RIGHT - Knee right 2 views
9. DX-SHOULDER-RIGHT - Shoulder right 2-3 views
10. DX-PELVIS - Pelvis AP

### US Exams (5)
1. US-ABDOMEN-COMPLETE - Abdomen complete
2. US-PELVIS-TRANSVAGINAL - Pelvis transvaginal (female only)
3. US-OB-FIRST-TRIMESTER - OB first trimester (female only, age 15-45)
4. US-VENOUS-LE-BILATERAL - Venous Doppler lower extremities
5. US-CAROTID-BILATERAL - Carotid Doppler bilateral

### MG Exams (3)
1. MG-SCREENING-BILATERAL - Screening mammogram bilateral (female, age 40+)
2. MG-DIAGNOSTIC-BILATERAL - Diagnostic mammogram bilateral (female)
3. MG-UNILATERAL-RIGHT - Unilateral mammogram right (female)

### NM Exams (2)
1. NM-BONE-SCAN-WHOLE-BODY - Bone scan whole body
2. NM-MYOCARDIAL-PERFUSION - Myocardial perfusion stress/rest

## Population Process

### Step 1: Create Template File

```bash
cd /home/icculus/projects/yeeter
mkdir -p app/catalog
touch app/catalog/exams.json
```

### Step 2: Populate Metadata Header

```python
# scripts/populate_catalog.py
import json
from datetime import datetime

def create_catalog_skeleton():
    return {
        "schema_version": "1.0",
        "catalog_version": "2025.1.0",
        "last_updated": datetime.now().isoformat(),
        "metadata": {
            "total_exams": 0,
            "modalities": [],
            "maintainer": "HL7 Yeeter Project",
            "license": "MIT",
            "data_sources": [
                "ACR Appropriateness Criteria",
                "CMS Physician Fee Schedule",
                "LOINC Radiology Playbook"
            ]
        },
        "exams": []
    }
```

### Step 3: Add Exams Iteratively

```python
def add_exam_to_catalog(catalog_path: str, exam: ExamSpec):
    """Add single exam to catalog file"""
    with open(catalog_path, 'r+') as f:
        data = json.load(f)
        
        # Append exam
        data['exams'].append(exam.dict())
        
        # Update metadata
        data['metadata']['total_exams'] = len(data['exams'])
        modalities = set(e['modality'] for e in data['exams'])
        data['metadata']['modalities'] = sorted(modalities)
        data['last_updated'] = datetime.now().isoformat()
        
        # Write back
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
```

### Step 4: Validation Pass

```bash
# After populating all 50 exams
python -m app.catalog.validate app/catalog/exams.json
```

## CPT Code Reference

### Common CPT Codes by Modality

| CPT | Description | Modality | Frequency |
|-----|-------------|----------|-----------|
| 70450 | CT head w/o contrast | CT | Very High |
| 70553 | MRI brain w/contrast | MR | High |
| 71046 | CXR 2 views | DX | Very High |
| 72148 | MRI lumbar spine w/o | MR | Very High |
| 73721 | MRI joint lower extremity w/o | MR | High |
| 74177 | CT abdomen/pelvis w/contrast | CT | Very High |
| 76700 | US abdomen complete | US | High |
| 77067 | Screening mammogram bilateral | MG | Very High |
| 78306 | Bone scan whole body | NM | Moderate |

## LOINC Code Reference

Use LOINC Radiology codes when available:
- https://loinc.org/usage/obs/radiology/
- Search format: "CT Head" → finds 24727-0

## Implementation Checklist

- [ ] Create `app/catalog/` directory
- [ ] Initialize `exams.json` with metadata header
- [ ] Add 15 CT exam entries with CPT/LOINC codes
- [ ] Add 15 MR exam entries with series protocols
- [ ] Add 10 DX exam entries (simple 1-3 views)
- [ ] Add 5 US exam entries
- [ ] Add 3 MG exam entries (female-only)
- [ ] Add 2 NM exam entries
- [ ] Run validation: `python -m app.catalog.validate`
- [ ] Test loading: `from app.catalog import get_catalog; catalog = get_catalog()`
- [ ] Commit to git with message "feat: initial exam catalog with 50 entries"

## Quality Checklist Per Exam

- [ ] Modality code is valid DICOM modality
- [ ] Body part is consistent with description
- [ ] Laterality matches description (RIGHT, LEFT, BILATERAL, or empty)
- [ ] At least one CPT code provided
- [ ] Series count matches typical protocol (1-8 series)
- [ ] Instance counts realistic for modality (CT: 30-200, MR: 15-40, DX: 1)
- [ ] Estimated duration matches real-world timing
- [ ] Frequency weight reflects clinical volume
- [ ] Setting list is appropriate for exam type
- [ ] Demographic constraints (age, sex) are correct

## Next Steps

See [EXAMGEN-3.1: Vocabulary Integration](EXAMGEN-3.1-Vocabulary-Integration.md) for mapping to external code systems.
