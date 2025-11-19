# EXAMGEN-3.1: Vocabulary Integration

**Status:** Not Started  
**Created:** 2025-01-18  
**Previous:** [EXAMGEN-3.0](EXAMGEN-3.0-Initial-Catalog-Population.md)  
**Next:** [EXAMGEN-4.0](EXAMGEN-4.0-SimulationRunner-Integration.md)

## Purpose

Integrate standard medical code systems (CPT, LOINC, RadLex, SNOMED) into the ExamSpec catalog to enable interoperability, realistic reporting, and external system lookups.

## Vocabulary Systems

### 1. CPT (Current Procedural Terminology)

**Source:** American Medical Association  
**Usage:** Billing and procedure identification  
**Coverage:** ~300 radiology-specific codes

#### Integration Points

```python
# app/catalog/vocabulary/cpt_codes.json
{
  "70450": {
    "display": "Computed tomography, head or brain; without contrast material",
    "relative_value_units": 1.57,
    "typical_reimbursement": 124.83,
    "exam_ids": ["CT-HEAD-WO"]
  },
  "73721": {
    "display": "Magnetic resonance (eg, proton) imaging, any joint of lower extremity; without contrast material",
    "relative_value_units": 3.77,
    "typical_reimbursement": 299.45,
    "exam_ids": ["MR-KNEE-RIGHT-WO", "MR-KNEE-LEFT-WO", "MR-ANKLE-RIGHT-WO"]
  }
}
```

#### Lookup API

```python
# app/catalog/vocabulary/cpt.py
from typing import Optional, List
import json

class CPTVocabulary:
    def __init__(self, json_path: str):
        with open(json_path) as f:
            self._codes = json.load(f)
    
    def get_code_info(self, cpt_code: str) -> Optional[dict]:
        """Get CPT code metadata"""
        return self._codes.get(cpt_code)
    
    def find_exams_by_cpt(self, cpt_code: str) -> List[str]:
        """Get exam IDs associated with CPT code"""
        code_data = self._codes.get(cpt_code)
        return code_data['exam_ids'] if code_data else []
    
    def validate_cpt_code(self, cpt_code: str) -> bool:
        """Check if CPT code exists"""
        return cpt_code in self._codes
```

### 2. LOINC (Logical Observation Identifiers Names and Codes)

**Source:** Regenstrief Institute  
**Usage:** Lab and radiology test identifiers  
**Coverage:** ~1000 radiology codes

#### LOINC Part Structure

```
LOINC Code: 24727-0
Part Structure: {Property}^{System}^{Method}^{Component}
Example: CT^HEAD^IMAGING^UNENHANCED
```

#### Integration Points

```python
# app/catalog/vocabulary/loinc_codes.json
{
  "24727-0": {
    "long_common_name": "CT Head",
    "display_name": "CT Head unenhanced",
    "component": "Head",
    "property": "Find",
    "timing": "Pt",
    "system": "Head",
    "scale_typ": "Doc",
    "method_typ": "CT",
    "exam_ids": ["CT-HEAD-WO"]
  },
  "37017-7": {
    "long_common_name": "MR Lower extremity - right joint",
    "display_name": "MR Lower extremity - right joint unenhanced",
    "component": "Lower extremity - right>Joint",
    "property": "Find",
    "timing": "Pt",
    "system": "Lower extremity.right.joint",
    "scale_typ": "Doc",
    "method_typ": "MR",
    "exam_ids": ["MR-KNEE-RIGHT-WO", "MR-ANKLE-RIGHT-WO"]
  }
}
```

#### Lookup API

```python
# app/catalog/vocabulary/loinc.py
class LOINCVocabulary:
    def __init__(self, json_path: str):
        with open(json_path) as f:
            self._codes = json.load(f)
    
    def get_code_info(self, loinc_code: str) -> Optional[dict]:
        return self._codes.get(loinc_code)
    
    def search_by_modality_and_body_part(self, 
                                          modality: str, 
                                          body_part: str) -> List[dict]:
        """Find LOINC codes matching modality and anatomy"""
        results = []
        for code, data in self._codes.items():
            if data['method_typ'] == modality and body_part.upper() in data['component'].upper():
                results.append({'code': code, **data})
        return results
```

### 3. RadLex (Radiology Lexicon)

**Source:** RSNA (Radiological Society of North America)  
**Usage:** Anatomy and imaging procedure ontology  
**Coverage:** ~68,000 terms (anatomy, modalities, procedures)

#### RadLex RID (Radiology ID) Structure

```
RID38780: "knee region"
RID28518: "right knee"
RID1243: "magnetic resonance imaging"
```

#### Integration Points

```python
# app/catalog/vocabulary/radlex_mappings.json
{
  "body_parts": {
    "HEAD": {
      "rid": "RID6434",
      "preferred_name": "head",
      "synonyms": ["brain", "skull"]
    },
    "KNEE": {
      "rid": "RID38780",
      "preferred_name": "knee region",
      "synonyms": ["knee joint", "genu"]
    }
  },
  "modalities": {
    "CT": {
      "rid": "RID10321",
      "preferred_name": "computed tomography",
      "synonyms": ["CAT scan", "CT scan"]
    },
    "MR": {
      "rid": "RID10312",
      "preferred_name": "magnetic resonance imaging",
      "synonyms": ["MRI", "nuclear magnetic resonance imaging"]
    }
  },
  "laterality": {
    "R": {
      "rid": "RID5825",
      "preferred_name": "right"
    },
    "L": {
      "rid": "RID5824",
      "preferred_name": "left"
    },
    "B": {
      "rid": "RID29663",
      "preferred_name": "bilateral"
    }
  }
}
```

#### Lookup API

```python
# app/catalog/vocabulary/radlex.py
class RadLexVocabulary:
    def __init__(self, json_path: str):
        with open(json_path) as f:
            self._mappings = json.load(f)
    
    def get_body_part_rid(self, dicom_body_part: str) -> Optional[str]:
        """Map DICOM BodyPartExamined to RadLex RID"""
        bp = self._mappings['body_parts'].get(dicom_body_part)
        return bp['rid'] if bp else None
    
    def get_modality_rid(self, dicom_modality: str) -> Optional[str]:
        """Map DICOM Modality to RadLex RID"""
        mod = self._mappings['modalities'].get(dicom_modality)
        return mod['rid'] if mod else None
    
    def get_laterality_rid(self, dicom_laterality: str) -> Optional[str]:
        """Map DICOM Laterality to RadLex RID"""
        lat = self._mappings['laterality'].get(dicom_laterality)
        return lat['rid'] if lat else None
```

### 4. ICD-10-CM (Diagnosis Codes)

**Source:** WHO / CMS  
**Usage:** Clinical indications (reason for exam)  
**Coverage:** ~70,000 codes (subset relevant to radiology indications)

#### Integration Points

```python
# app/catalog/vocabulary/icd10_indications.json
{
  "M23.201": {
    "description": "Derangement of unspecified meniscus due to old tear or injury, right knee",
    "body_part": "KNEE",
    "laterality": "R",
    "exam_suggestions": ["MR-KNEE-RIGHT-WO", "MR-KNEE-RIGHT-W"]
  },
  "I63.9": {
    "description": "Cerebral infarction, unspecified",
    "body_part": "HEAD",
    "laterality": "",
    "exam_suggestions": ["MR-BRAIN-STROKE", "CT-HEAD-WO", "MR-BRAIN-WO"]
  },
  "R07.9": {
    "description": "Chest pain, unspecified",
    "body_part": "CHEST",
    "laterality": "",
    "exam_suggestions": ["DX-CHEST-PA-LAT", "CT-CHEST-W"]
  }
}
```

#### Indication Template Generator

```python
# app/catalog/vocabulary/icd10.py
class ICD10Vocabulary:
    def __init__(self, json_path: str):
        with open(json_path) as f:
            self._codes = json.load(f)
    
    def get_indication_text(self, icd10_code: str) -> Optional[str]:
        """Get plain-text indication for HL7/DICOM"""
        code_data = self._codes.get(icd10_code)
        return code_data['description'] if code_data else None
    
    def suggest_exams(self, icd10_code: str) -> List[str]:
        """Get exam IDs appropriate for diagnosis"""
        code_data = self._codes.get(icd10_code)
        return code_data['exam_suggestions'] if code_data else []
    
    def random_indication_for_exam(self, exam_id: str) -> Optional[str]:
        """Find random realistic indication for exam"""
        matching_codes = [
            code for code, data in self._codes.items()
            if exam_id in data['exam_suggestions']
        ]
        if matching_codes:
            selected_code = random.choice(matching_codes)
            return self.get_indication_text(selected_code)
        return None
```

## Unified Vocabulary Manager

```python
# app/catalog/vocabulary/__init__.py
from typing import Optional
from .cpt import CPTVocabulary
from .loinc import LOINCVocabulary
from .radlex import RadLexVocabulary
from .icd10 import ICD10Vocabulary

class VocabularyManager:
    """Unified access to all medical code systems"""
    
    def __init__(self, vocab_dir: str):
        self.cpt = CPTVocabulary(f"{vocab_dir}/cpt_codes.json")
        self.loinc = LOINCVocabulary(f"{vocab_dir}/loinc_codes.json")
        self.radlex = RadLexVocabulary(f"{vocab_dir}/radlex_mappings.json")
        self.icd10 = ICD10Vocabulary(f"{vocab_dir}/icd10_indications.json")
    
    def enrich_exam_spec(self, exam: ExamSpec) -> ExamSpec:
        """Add vocabulary metadata to ExamSpec"""
        # Add RadLex RIDs
        exam.custom_metadata['radlex_body_part_rid'] = \
            self.radlex.get_body_part_rid(exam.body_part)
        exam.custom_metadata['radlex_modality_rid'] = \
            self.radlex.get_modality_rid(exam.modality)
        
        # Validate CPT codes
        for code in exam.procedure_codes:
            if code.system == "CPT" and not self.cpt.validate_cpt_code(code.code):
                logger.warning(f"Invalid CPT code in {exam.id}: {code.code}")
        
        return exam
    
    def generate_indication(self, exam: ExamSpec) -> str:
        """Generate realistic clinical indication"""
        # Try exam's template first
        if exam.indication_template:
            return exam.indication_template
        
        # Fall back to ICD-10 lookup
        indication = self.icd10.random_indication_for_exam(exam.id)
        return indication or f"Clinical indication for {exam.name}"

# Singleton
_vocab_manager: Optional[VocabularyManager] = None

def get_vocabulary() -> VocabularyManager:
    global _vocab_manager
    if _vocab_manager is None:
        vocab_dir = os.path.join(
            os.path.dirname(__file__), 
            '../vocabulary'
        )
        _vocab_manager = VocabularyManager(vocab_dir)
    return _vocab_manager
```

## Usage in Simulation

```python
# app/util/simulation_runner.py
from app.catalog.factory import get_exam_factory
from app.catalog.vocabulary import get_vocabulary

class SimulationRunner:
    def __init__(self):
        self.exam_factory = get_exam_factory()
        self.vocabulary = get_vocabulary()
    
    def handle_generate_hl7(self, step_config: Dict, run_context: Dict):
        # Select exam
        exam = self.exam_factory.get_random_exam(
            modality=step_config.get('modality'),
            patient_age=run_context['patient'].age,
            patient_sex=run_context['patient'].sex
        )
        
        # Generate indication using ICD-10 vocabulary
        indication = self.vocabulary.generate_indication(exam)
        
        # Build OBR segment with CPT code
        cpt_code = exam.procedure_codes[0].code
        cpt_display = exam.procedure_codes[0].display
        
        obr_segment = (
            f"OBR|1||{run_context['accession_number']}|"
            f"{cpt_code}^{exam.description}^CPT|"
            f"||{timestamp}|||||||"
            f"{indication}|"
            f"||||||||||"
        )
        
        # Store for DICOM generation
        run_context['exam'] = exam
        run_context['indication'] = indication
        
        return hl7_message
```

## Data Source Acquisition

### CPT Codes (Manual Entry)
- **Free Source:** CMS Physician Fee Schedule Lookup Tool
- **URL:** https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files
- **Format:** Excel (convert to JSON)
- **Count:** ~50-100 radiology codes needed

### LOINC Codes (Free Download)
- **Source:** LOINC Table (requires free account)
- **URL:** https://loinc.org/downloads/
- **File:** LOINC_2.78_Text.zip (or latest version)
- **Filter:** Method_Typ IN ('CT', 'MR', 'DX', 'US', 'MG', 'NM')
- **Format:** Tab-delimited text → convert to JSON

### RadLex (API or Download)
- **Source:** RadLex OWL file or RSNA Informatics site
- **URL:** https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon
- **Format:** OWL XML (requires parsing) or CSV mappings
- **Alternative:** Use existing DICOM → RadLex mappings from literature

### ICD-10-CM (Free Download)
- **Source:** CMS ICD-10-CM Code Descriptions
- **URL:** https://www.cms.gov/medicare/coding-billing/icd-10-codes
- **File:** 2025 ICD-10-CM Codes (TXT format)
- **Filter:** Manually curate ~200 radiology-relevant diagnoses

## Implementation Checklist

- [ ] Create `app/catalog/vocabulary/` directory
- [ ] Download LOINC table (free registration)
- [ ] Extract radiology-specific LOINC codes (method=CT/MR/etc)
- [ ] Create `loinc_codes.json` with ~100 codes
- [ ] Manually curate CPT codes from CMS fee schedule
- [ ] Create `cpt_codes.json` with ~50 codes
- [ ] Create `radlex_mappings.json` with body part/modality RIDs
- [ ] Curate ICD-10 diagnosis codes (top 100 radiology indications)
- [ ] Create `icd10_indications.json` with exam suggestions
- [ ] Implement `VocabularyManager` class
- [ ] Add unit tests for each vocabulary module
- [ ] Integrate into `ExamFactory.get_random_exam()`
- [ ] Update ExamSpec schema to include vocabulary metadata
- [ ] Document data sources and licensing in README

## Validation Checklist

- [ ] All CPT codes in catalog exist in `cpt_codes.json`
- [ ] All LOINC codes in catalog exist in `loinc_codes.json`
- [ ] Body parts map to RadLex RIDs
- [ ] Modalities map to RadLex RIDs
- [ ] Each exam has at least one ICD-10 indication
- [ ] Run validation: `python -m app.catalog.validate --check-vocabulary`

## Next Steps

See [EXAMGEN-4.0: SimulationRunner Integration](EXAMGEN-4.0-SimulationRunner-Integration.md) for using ExamSpecs in workflow orchestration.
