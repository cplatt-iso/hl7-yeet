# EXAMGEN-1.0: Current Architecture Analysis

**Status:** Complete  
**Created:** 2025-11-18  
**Next:** [EXAMGEN-1.1](EXAMGEN-1.1-Root-Cause-Analysis.md)

## Purpose

Document the current exam generation pipeline as of commit `c2d1654` to establish a baseline for refactoring work.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Template Parsing (faker_parser.py)                           │
│    - HL7 generator templates use {$Faker.Order.StudyDescription}│
│    - _generate_study_and_modality() picks from 30 hardcoded     │
│      (description, modality) tuples                              │
│    - Results cached in run_context['order']                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. HL7 Message Generation (simulation_runner.py)                │
│    - process_faker_string() replaces template placeholders      │
│    - ORM^O01 message built with patient + order context         │
│    - Message stored in run_context['last_hl7_message']          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. HL7 Parsing & Context Extraction (simulation_runner.py)      │
│    - parse_message() reads generated ORM                         │
│    - _extract_order_context() pulls from OBR segment:           │
│      • OBR-4: study description                                  │
│      • OBR-24: explicit modality (if present)                    │
│      • CPT code prefixes → modality inference                    │
│      • ZDS custom segment → AE title modality hints              │
│    - _infer_modality_from_description() as last resort           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. DICOM Generation (simulation_runner.py)                      │
│    - handle_generate_dicom() priority order:                    │
│      1. Explicit step parameter                                  │
│      2. DMWL worklist item                                       │
│      3. Order context (from HL7 parsing)                         │
│      4. Infer from description                                   │
│      5. **RANDOM WEIGHTED FALLBACK**                             │
│    - _infer_body_part_from_description() guesses body part      │
│    - create_study_files() generates DICOM instances             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Pixel Generation (dicom_generator.py)                        │
│    - _generate_medical_image() creates synthetic pixels         │
│    - Modality-specific rendering (CT, MR, DX, US, etc.)         │
│    - Body part determines anatomical structures drawn           │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. faker_parser.py

**Location:** `app/util/faker_parser.py`

**Responsibilities:**
- Defines 30 hardcoded exam tuples in `_generate_study_and_modality()`
- Provides template placeholder resolution via `process_faker_string()`
- Caches generated values in `run_context` for consistency

**Key Functions:**
```python
def _generate_study_and_modality() -> Tuple[str, str]:
    """Returns (description, modality) from fixed list"""
    
def _generate_and_cache_study_description(context: Dict) -> str:
    """Ensures description/modality generated together"""
    
def _generate_and_cache_modality(context: Dict) -> str:
    """Returns cached modality or generates new pair"""
```

**Current Exam Catalog (Sample):**
- CT: "CT HEAD W/O CONTRAST", "CT CHEST W/O CONTRAST", etc. (7 entries)
- MR: "MRI LUMBAR SPINE W/O CONTRAST", "MRI KNEE RIGHT W/O CONTRAST", etc. (7 entries)
- DX: "CHEST X-RAY 2 VIEWS", "X-RAY FOOT 3 VIEWS LEFT", etc. (6 entries)
- US: "ULTRASOUND ABDOMEN COMPLETE", "ECHOCARDIOGRAM COMPLETE", etc. (4 entries)
- MG: "MAMMOGRAM SCREENING BILATERAL", etc. (3 entries)
- NM: "NUCLEAR MEDICINE BONE SCAN", etc. (3 entries)

**Limitations:**
- Fixed vocabulary cannot cover procedure variety
- No support for laterality metadata
- No contrast/protocol annotations
- No CPT/LOINC codes

### 2. simulation_runner.py

**Location:** `app/util/simulation_runner.py`

**Responsibilities:**
- Orchestrates HL7 generation, parsing, and DICOM creation
- Maintains `run_context` state across steps
- Handles modality resolution and fallback logic

**Key Methods:**

```python
def handle_generate_hl7(self, step, patient_iter, repeat_iter):
    """Generates HL7 message using faker-populated template"""
    # Calls process_faker_string() to resolve placeholders
    # Parses result to extract accession/modality
    
def _extract_order_context(self, order_group, step, patient_iter, repeat_iter):
    """Extracts modality and description from OBR segment"""
    # Tries OBR-24, OBR-4 code prefixes, ZDS, then inference
    
def _infer_modality_from_description(self, description, step, patient_iter, repeat_iter):
    """Keyword-based modality guessing"""
    # Searches for MRI, CT, PET, etc. in description text
    
def handle_generate_dicom(self, step, patient_iter, repeat_iter):
    """Creates DICOM files using resolved metadata"""
    # Priority: param > MWL > order context > inference > RANDOM
```

**Fallback Logic (Lines 647-697):**
When no modality found in any context:
1. Try inferring from cached study description
2. If still empty, **randomly pick** from weighted list:
   - DX: 35% (most common)
   - CT: 25%
   - MR: 20%
   - US: 10%
   - CR: 5%
   - NM: 3%
   - MG: 2%
3. Generate matching description for the random modality

**Problem:** Random selection can contradict existing description text.

### 3. dicom_generator.py

**Location:** `app/util/dicom_generator.py`

**Responsibilities:**
- Creates DICOM file metadata and pixel arrays
- Infers body part from description text
- Generates modality-specific synthetic images

**Key Functions:**

```python
def _infer_body_part_from_description(description: str) -> str:
    """Maps keywords to DICOM body part codes"""
    # 40+ pattern rules for HEAD, CHEST, SPINE, KNEE, etc.
    
def create_study_files(output_dir, num_images, overrides, ...):
    """Main entry point for DICOM generation"""
    # Creates Study/Series/Instance hierarchy
    # Calls _generate_medical_image() for pixels
    
def _generate_medical_image(modality, body_part, width, height, ...):
    """Renders synthetic anatomical images"""
    # Modality-specific rendering (CT, MR, DX, US, NM, MG)
```

**Body Part Inference Rules:**
- ~40 pattern groups ordered by specificity
- Falls back to `CHEST` if no match found
- No validation that body part is appropriate for modality

## Context Data Structure

```python
run_context = {
    'patient': {
        'last_name': str,
        'first_name': str,
        'mrn': str,
        'dob': str,  # YYYYMMDD
        'sex': str,  # M/F/O
    },
    'order': {
        'study_description': str,   # May be set by faker
        'modality': str,            # May be set by faker or extraction
        'accession_number': str,
        'placer_order_number': str,
    },
    'Context': {
        'MessageTimestamp': datetime,
        'ScheduledStart': datetime,
        'ScheduledEnd': datetime,
    },
    'last_hl7_message': str,
    'last_dicom_files': List[str],
    'worklist_item': Dataset,  # Optional MWL result
}
```

## Template Integration

**Example ORM Template Snippet:**
```
OBR|1|{$Faker.Order.PlacerOrderNumber}^RIS|{$Faker.Order.AccessionNumber}^RIS|
{$Faker.random_element(['73721', '73722', '73723'])}^{$Faker.Order.StudyDescription}^CPT|
```

**Issues:**
- Templates can hardcode descriptions without calling faker helpers
- No enforcement that `{$Faker.Order.Modality}` is used if description is referenced
- Templates may write OBR-24 explicitly, bypassing context

## Performance Characteristics

- **Faker string resolution:** <1ms per placeholder
- **HL7 parsing:** ~5-10ms per message
- **DICOM file creation:** 50-200ms for 10 instances (with pixel generation)
- **Total per-patient overhead:** ~300-500ms

## Technical Debt

1. **No schema validation** for run_context structure
2. **Implicit state dependencies** between steps (e.g., DICOM generation assumes HL7 ran first)
3. **Logging inconsistency** - some paths log to events, others to app logger
4. **No retry logic** if faker/DICOM generation fails
5. **Hardcoded paths** (`/data/sim_runs/{run_id}`)

## Next Steps

See [EXAMGEN-1.1: Root Cause Analysis](EXAMGEN-1.1-Root-Cause-Analysis.md) for failure mode analysis and impact assessment.
