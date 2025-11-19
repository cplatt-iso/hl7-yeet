# EXAMGEN-2.0: ExamSpec Schema Design

**Status:** Complete  
**Created:** 2025-11-18  
**Previous:** [EXAMGEN-1.1](EXAMGEN-1.1-Root-Cause-Analysis.md)  
**Next:** [EXAMGEN-2.1](EXAMGEN-2.1-Catalog-Data-Model.md)

## Purpose

Define the canonical data structure for representing a radiology exam specification, including all metadata needed for HL7, DMWL, and DICOM generation.

## Design Principles

1. **Single Source of Truth:** All downstream metadata derives from ExamSpec
2. **Type Safety:** Use Pydantic models for validation and serialization
3. **Extensibility:** Allow custom fields without breaking core logic
4. **Interoperability:** Map to standard vocabularies (CPT, LOINC, SNOMED, RadLex)
5. **Readability:** JSON-serializable for human editing and version control

## Core Schema

### ExamSpec (Python Model)

```python
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum

class Laterality(str, Enum):
    """DICOM laterality codes"""
    RIGHT = "R"
    LEFT = "L"
    BILATERAL = "B"
    UNILATERAL = "U"
    UNPAIRED = ""  # Not applicable

class ContrastType(str, Enum):
    """Contrast administration type"""
    NONE = "none"
    IV = "intravenous"
    ORAL = "oral"
    RECTAL = "rectal"
    INTRATHECAL = "intrathecal"

class SeriesProtocol(BaseModel):
    """Defines a single series within a study"""
    protocol_name: str = Field(..., description="e.g., 'AX T1 PRE', 'COR T2 FS'")
    series_description: str = Field(..., description="DICOM SeriesDescription tag")
    instances: int = Field(..., ge=1, description="Number of images/slices")
    acquisition_duration_sec: Optional[float] = Field(None, description="Simulated scan time")
    sequence_name: Optional[str] = Field(None, description="e.g., 'ep2d_diff', 'tfl3d'")
    
class ProcedureCode(BaseModel):
    """Standard medical coding for procedure"""
    system: Literal["CPT", "LOINC", "SNOMED", "ICD10PCS"] = "CPT"
    code: str = Field(..., description="Alphanumeric code")
    display: str = Field(..., description="Human-readable name")

class ExamSpec(BaseModel):
    """Complete specification for a radiology exam"""
    
    # Identity & Classification
    id: str = Field(..., description="Unique identifier, e.g., 'MR-KNEE-RIGHT-WO'")
    version: str = Field("1.0", description="Schema version for compatibility")
    
    # Core Attributes
    modality: str = Field(..., description="DICOM modality code (CT, MR, DX, US, etc.)")
    name: str = Field(..., description="Canonical exam name for display")
    description: str = Field(..., description="Study description for HL7/DICOM")
    body_part: str = Field(..., description="DICOM BodyPartExamined code")
    laterality: Laterality = Field(Laterality.UNPAIRED, description="Side if applicable")
    
    # Clinical Context
    indication_template: Optional[str] = Field(None, description="Reason for exam (supports {placeholders})")
    contrast: ContrastType = Field(ContrastType.NONE, description="Contrast administration")
    contrast_agent: Optional[str] = Field(None, description="e.g., 'Gadolinium', 'Iodinated'")
    contrast_volume_ml: Optional[float] = Field(None, description="Typical dose")
    
    # Standard Codes
    procedure_codes: List[ProcedureCode] = Field(default_factory=list, description="CPT/LOINC/SNOMED codes")
    
    # Study Structure
    series: List[SeriesProtocol] = Field(..., description="Expected series in study", min_items=1)
    estimated_duration_min: float = Field(..., gt=0, description="Total exam time for scheduling")
    
    # Demographic Constraints
    min_age: Optional[int] = Field(None, description="Minimum patient age in years")
    max_age: Optional[int] = Field(None, description="Maximum patient age in years")
    required_sex: Optional[Literal["M", "F"]] = Field(None, description="If exam is sex-specific")
    
    # Utilization Metadata (for weighted selection)
    frequency_weight: float = Field(1.0, ge=0, description="Relative frequency in population")
    setting: List[Literal["outpatient", "inpatient", "emergency", "screening"]] = Field(
        default=["outpatient"], description="Clinical settings where exam is ordered"
    )
    
    # Extensibility
    custom_metadata: Dict[str, str] = Field(default_factory=dict, description="Org-specific fields")
    
    @validator('modality')
    def validate_modality(cls, v):
        valid_modalities = {
            'CT', 'MR', 'DX', 'CR', 'US', 'NM', 'PT', 'MG', 'XA', 'RF', 
            'ES', 'OT', 'BI', 'CD', 'DD', 'DG', 'ECG', 'EPS', 'GM', 'HC'
        }
        if v not in valid_modalities:
            raise ValueError(f"Modality must be one of {valid_modalities}")
        return v
    
    @validator('series', each_item=True)
    def validate_series_consistency(cls, series, values):
        """Ensure series protocols make sense for modality"""
        modality = values.get('modality')
        if modality == 'DX' and series.instances > 10:
            raise ValueError("X-ray series should not exceed 10 instances")
        return series
```

### Example JSON Representation

```json
{
  "id": "MR-KNEE-RIGHT-WO",
  "version": "1.0",
  "modality": "MR",
  "name": "MRI Knee Right Without Contrast",
  "description": "MRI KNEE RIGHT W/O CONTRAST",
  "body_part": "KNEE",
  "laterality": "R",
  "indication_template": "Pain in right knee, rule out meniscal tear",
  "contrast": "none",
  "procedure_codes": [
    {
      "system": "CPT",
      "code": "73721",
      "display": "Magnetic resonance (eg, proton) imaging, any joint of lower extremity; without contrast material"
    },
    {
      "system": "LOINC",
      "code": "24838-6",
      "display": "MR Lower extremity joint"
    }
  ],
  "series": [
    {
      "protocol_name": "SAG T1",
      "series_description": "SAG T1 KNEE",
      "instances": 25,
      "acquisition_duration_sec": 180,
      "sequence_name": "t1_tse_sag"
    },
    {
      "protocol_name": "SAG T2 FS",
      "series_description": "SAG T2 FS KNEE",
      "instances": 28,
      "acquisition_duration_sec": 240,
      "sequence_name": "t2_tse_fs_sag"
    },
    {
      "protocol_name": "COR PD",
      "series_description": "COR PD KNEE",
      "instances": 22,
      "acquisition_duration_sec": 200,
      "sequence_name": "pd_tse_cor"
    },
    {
      "protocol_name": "AX T2 FS",
      "series_description": "AX T2 FS KNEE",
      "instances": 30,
      "acquisition_duration_sec": 220,
      "sequence_name": "t2_tse_fs_ax"
    }
  ],
  "estimated_duration_min": 25.0,
  "min_age": 5,
  "required_sex": null,
  "frequency_weight": 1.5,
  "setting": ["outpatient", "emergency"],
  "custom_metadata": {
    "department": "MSK",
    "requires_positioning_device": "true"
  }
}
```

## Mapping to Downstream Systems

### HL7 ORM^O01 Message

| ExamSpec Field | HL7 Field | Notes |
|----------------|-----------|-------|
| `description` | OBR-4.2 (description component) | Universal procedure ID |
| `procedure_codes[0].code` | OBR-4.1 (identifier) | Primary code |
| `procedure_codes[0].system` | OBR-4.3 (coding system) | e.g., "CPT" |
| `modality` | OBR-24 (diagnostic service ID) | May need AE title mapping |
| `laterality` | OBR-15 (specimen source) | Custom field, not standard |
| `indication_template` | OBR-13 (relevant clinical info) | Filled with patient context |

### DICOM Modality Worklist (C-FIND)

| ExamSpec Field | DICOM Tag | Tag Name |
|----------------|-----------|----------|
| `modality` | (0008,0060) | Modality |
| `description` | (0032,1060) | RequestedProcedureDescription |
| `body_part` | (0018,0015) | BodyPartExamined |
| `laterality` | (0020,0060) | Laterality |
| `procedure_codes[0].code` | (0040,1001) | RequestedProcedureID |
| `estimated_duration_min` | (0040,0260) | PerformedProtocolCodeSequence |

### DICOM Study/Series Instances

| ExamSpec Field | DICOM Tag | Tag Name |
|----------------|-----------|----------|
| `modality` | (0008,0060) | Modality |
| `description` | (0008,1030) | StudyDescription |
| `body_part` | (0018,0015) | BodyPartExamined |
| `laterality` | (0020,0060) | Laterality |
| `contrast_agent` | (0018,0010) | ContrastBolusAgent |
| `series[n].protocol_name` | (0018,1030) | ProtocolName |
| `series[n].series_description` | (0008,103E) | SeriesDescription |
| `series[n].sequence_name` | (0018,0024) | SequenceName |

## Validation Rules

### Modality-Specific Constraints

```python
MODALITY_RULES = {
    'MR': {
        'allowed_body_parts': ['BRAIN', 'HEAD', 'SPINE', 'CSPINE', 'TSPINE', 'LSPINE', 
                                'CHEST', 'ABDOMEN', 'PELVIS', 'KNEE', 'SHOULDER', 'ANKLE', 
                                'WRIST', 'HAND', 'FOOT', 'HEART'],
        'typical_series_count': (3, 8),
        'contrast_types': ['none', 'intravenous'],
    },
    'CT': {
        'allowed_body_parts': ['HEAD', 'NECK', 'CHEST', 'ABDOMEN', 'PELVIS', 'SPINE', 
                                'EXTREMITY'],
        'typical_series_count': (1, 4),  # Pre, arterial, venous, delayed
        'contrast_types': ['none', 'intravenous', 'oral'],
    },
    'DX': {
        'allowed_body_parts': ['CHEST', 'ABDOMEN', 'SPINE', 'EXTREMITY', 'SKULL'],
        'typical_series_count': (1, 3),  # Usually 1-2 views
        'contrast_types': ['none'],
    },
    'US': {
        'allowed_body_parts': ['ABDOMEN', 'PELVIS', 'BREAST', 'THYROID', 'CAROTID', 
                                'HEART', 'VENOUS', 'ARTERIAL'],
        'typical_series_count': (1, 1),  # US is typically one "series" with many clips
        'contrast_types': ['none', 'intravenous'],  # Microbubble contrast
    },
    'MG': {
        'allowed_body_parts': ['BREAST'],
        'typical_series_count': (4, 8),  # CC/MLO per side, +/- additional views
        'contrast_types': ['none'],
        'required_sex': 'F',  # (except in rare male breast cancer cases)
    }
}
```

### Demographic Constraints

```python
DEMOGRAPHIC_RULES = {
    'obstetric_ultrasound': {
        'required_sex': 'F',
        'min_age': 12,
        'max_age': 55,
    },
    'prostate_mri': {
        'required_sex': 'M',
        'min_age': 40,
    },
    'pediatric_head_ct': {
        'max_age': 18,
        'warning': 'Requires special dose reduction protocols'
    }
}
```

## Schema Evolution Strategy

- **Version field:** Allows parsing old/new formats
- **Optional fields:** New attributes default gracefully
- **Deprecation warnings:** Old field names supported for 2 major versions
- **Migration scripts:** Auto-upgrade catalog files on first load

## Implementation Checklist

- [x] Create `app/exam_spec/__init__.py` with the authoritative Pydantic schema (moved out of `app/models.py` to avoid namespace clashes)
- [x] Add unit tests for validation rules (`tests/test_exam_spec.py`)
- [ ] Create example ExamSpec instances for each modality (tracked under EXAMGEN-3.0 population work)
- [ ] Document `custom_metadata` conventions
- [ ] Implement JSON schema export for editor autocomplete

### Implementation Notes

- The schema now lives in `app/exam_spec/__init__.py`, making it importable throughout the backend and reducing coupling with legacy SQLAlchemy models.
- Validation tests enforce modality lists, series requirements, demographic guards, and numeric ranges; failing validations now surface `pydantic.ValidationError` instances for easier troubleshooting.
- The new module is exercised via `tests/test_exam_spec.py` (11 cases) and referenced by the catalog loader, ensuring the same validation path is used both during authoring and at runtime.

## Next Steps

See [EXAMGEN-2.1: Catalog Data Model & Storage](EXAMGEN-2.1-Catalog-Data-Model.md) for how ExamSpecs are organized and loaded.
