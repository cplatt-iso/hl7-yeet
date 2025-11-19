# EXAMGEN-4.0: SimulationRunner Integration

**Status:** In Progress  
**Created:** 2025-01-18  
**Previous:** [EXAMGEN-3.1](EXAMGEN-3.1-Vocabulary-Integration.md)  
**Next:** [EXAMGEN-5.0](EXAMGEN-5.0-Template-Migration.md)

## Purpose

Refactor `app/util/simulation_runner.py` to use `ExamFactory` and `ExamSpec` as the single source of truth for all exam metadata generation, eliminating random fallback logic and ensuring consistency across HL7, DMWL, and DICOM outputs.

## Current Issues (From EXAMGEN-1.1)

1. **Random modality fallback** in `handle_generate_dicom()` (lines 647-697)
2. **String-based modality inference** from descriptions
3. **Inconsistent context extraction** between HL7 parsing and default generation
4. **No validation** between HL7 OBR fields and DICOM metadata

## Refactoring Strategy

### Phase 1: HL7 Generation (`handle_generate_hl7`)

**Before:**
```python
def handle_generate_hl7(self, step_config, run_context):
    template = step_config.get('template', 'default_template.txt')
    with open(f'templates/{template}') as f:
        hl7_template = f.read()
    
    # Uses faker_parser with random study/modality pairs
    hl7_message = faker_parser.process_faker_string(
        hl7_template,
        run_context['patient']
    )
    
    # Parse back to extract metadata
    parsed = hl7apy.parse_message(hl7_message)
    obr = parsed.OBR
    run_context['order_description'] = obr.OBR_4.OBR_4_2.value
    run_context['procedure_code'] = obr.OBR_4.OBR_4_1.value
    ...
```

**After (ExamSpec-driven):**
```python
def handle_generate_hl7(self, step_config, run_context):
    """Generate HL7 ORM^O01 message using ExamSpec"""
    
    # Step 1: Select exam using factory
    exam = self._select_exam(step_config, run_context)
    
    # Step 2: Generate patient-specific context
    indication = self.vocabulary.generate_indication(exam)
    accession_number = self._generate_accession_number()
    
    # Step 3: Build HL7 message directly (no template needed)
    hl7_message = self._build_hl7_from_exam(
        exam=exam,
        patient=run_context['patient'],
        accession_number=accession_number,
        indication=indication
    )
    
    # Step 4: Store exam in context for downstream steps
    run_context['exam'] = exam
    run_context['accession_number'] = accession_number
    run_context['indication'] = indication
    run_context['study_description'] = exam.description
    run_context['modality'] = exam.modality
    run_context['body_part'] = exam.body_part
    run_context['laterality'] = exam.laterality.value
    
    return hl7_message

def _select_exam(self, step_config: Dict, run_context: Dict) -> ExamSpec:
    """Select exam using factory with step configuration"""
    patient = run_context['patient']
    
    # Priority 1: Explicit exam ID
    if 'exam_id' in step_config:
        return self.exam_factory.get_exam_by_id(step_config['exam_id'])
    
    # Priority 2: CPT code lookup
    if 'cpt_code' in step_config:
        return self.exam_factory.get_exam_by_cpt_code(step_config['cpt_code'])
    
    # Priority 3: Weighted random with constraints
    return self.exam_factory.get_random_exam(
        modality=step_config.get('modality'),
        body_part=step_config.get('body_part'),
        setting=step_config.get('setting', 'outpatient'),
        patient_age=patient.age,
        patient_sex=patient.sex
    )

def _build_hl7_from_exam(self, exam: ExamSpec, patient, 
                          accession_number: str, indication: str) -> str:
    """Construct HL7 ORM^O01 message from ExamSpec"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # MSH segment
    msh = (
        f"MSH|^~\\&|YEETER|FACILITY|PACS|PACS|{timestamp}||"
        f"ORM^O01|{accession_number}|P|2.5\r"
    )
    
    # PID segment (from run_context patient)
    dob = patient.date_of_birth.strftime('%Y%m%d')
    pid = (
        f"PID|1||{patient.mrn}^^^FACILITY^MR||"
        f"{patient.last_name}^{patient.first_name}^{patient.middle_name}||"
        f"{dob}|{patient.sex}||||||||||{patient.ssn}\r"
    )
    
    # ORC segment
    orc = f"ORC|NW|{accession_number}|{accession_number}|||||||{timestamp}\r"
    
    # OBR segment (using ExamSpec procedure codes)
    cpt_code = exam.procedure_codes[0]
    obr = (
        f"OBR|1|{accession_number}|{accession_number}|"
        f"{cpt_code.code}^{exam.description}^{cpt_code.system}|"
        f"|NW|{timestamp}|||||||"
        f"{indication}|"
        f"||||||||{exam.modality}||||"
        f"^^^{timestamp}||||\r"
    )
    
    # ZDS segment (custom - DICOM study metadata)
    zds = (
        f"ZDS|{exam.body_part}|{exam.laterality.value}|"
        f"{exam.estimated_duration_min}|{len(exam.series)}\r"
    )
    
    return msh + pid + orc + obr + zds
```

### Phase 2: DMWL Send (`handle_send_dmwl`)

**Before:**
```python
def handle_send_dmwl(self, step_config, run_context):
    # Extract from parsed HL7
    description = run_context.get('order_description', 'UNKNOWN')
    modality = self._infer_modality_from_description(description)
    ...
```

**After:**
```python
def handle_send_dmwl(self, step_config, run_context):
    """Send DICOM Modality Worklist entry using ExamSpec"""
    
    exam = run_context.get('exam')
    if exam is None:
        raise ValueError("No ExamSpec in context - HL7 step must run first")
    
    patient = run_context['patient']
    accession_number = run_context['accession_number']
    
    # Build C-FIND request dataset
    worklist_entry = self._build_dmwl_from_exam(
        exam=exam,
        patient=patient,
        accession_number=accession_number,
        requested_datetime=run_context.get('scheduled_datetime')
    )
    
    # Send to worklist SCP
    endpoint = step_config['endpoint']
    success = dmwl_client.send_worklist_entry(
        endpoint.host,
        endpoint.port,
        endpoint.ae_title,
        worklist_entry
    )
    
    return success

def _build_dmwl_from_exam(self, exam: ExamSpec, patient, 
                           accession_number: str, 
                           requested_datetime=None) -> Dataset:
    """Create DICOM MWL dataset from ExamSpec"""
    from pydicom.dataset import Dataset
    from datetime import datetime
    
    ds = Dataset()
    
    # Patient Identification
    ds.PatientName = f"{patient.last_name}^{patient.first_name}"
    ds.PatientID = patient.mrn
    ds.PatientBirthDate = patient.date_of_birth.strftime('%Y%m%d')
    ds.PatientSex = patient.sex
    
    # Scheduled Procedure Step Sequence
    sps = Dataset()
    sps.Modality = exam.modality
    sps.ScheduledStationAETitle = step_config.get('station_ae_title', 'MODALITY')
    sps.ScheduledProcedureStepStartDate = \
        (requested_datetime or datetime.now()).strftime('%Y%m%d')
    sps.ScheduledProcedureStepStartTime = \
        (requested_datetime or datetime.now()).strftime('%H%M%S')
    sps.ScheduledPerformingPhysicianName = "REFERRING^PHYSICIAN"
    sps.ScheduledProcedureStepDescription = exam.description
    sps.ScheduledProtocolCodeSequence = []
    
    # Add protocol codes for each series
    for series in exam.series:
        protocol_code = Dataset()
        protocol_code.CodeValue = series.protocol_name
        protocol_code.CodingSchemeDesignator = "99YEETER"  # Private scheme
        protocol_code.CodeMeaning = series.series_description
        sps.ScheduledProtocolCodeSequence.append(protocol_code)
    
    ds.ScheduledProcedureStepSequence = [sps]
    
    # Requested Procedure
    ds.RequestedProcedureID = accession_number
    ds.RequestedProcedureDescription = exam.description
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.AccessionNumber = accession_number
    
    # Requested Procedure Code (using CPT)
    rpc = Dataset()
    cpt_code = exam.procedure_codes[0]
    rpc.CodeValue = cpt_code.code
    rpc.CodingSchemeDesignator = cpt_code.system
    rpc.CodeMeaning = cpt_code.display
    ds.RequestedProcedureCodeSequence = [rpc]
    
    return ds
```

### Phase 3: DICOM Generation (`handle_generate_dicom`)

**Before (PROBLEMATIC):**
```python
def handle_generate_dicom(self, step_config, run_context):
    # Try to extract modality from context
    modality = run_context.get('modality')
    if not modality:
        description = run_context.get('order_description', '')
        modality = self._infer_modality_from_description(description)
    
    # FALLBACK TO RANDOM (BAD!)
    if not modality or modality == 'UN':
        modality = random.choice(['CT', 'MR', 'DX', 'US'])
    
    # Generate with inconsistent metadata
    file_paths = dicom_generator.create_study_files(
        modality=modality,
        description=description,
        patient=run_context['patient'],
        ...
    )
```

**After (ExamSpec-driven):**
```python
def handle_generate_dicom(self, step_config, run_context):
    """Generate DICOM study files using ExamSpec"""
    
    exam = run_context.get('exam')
    if exam is None:
        raise ValueError(
            "No ExamSpec in context. DICOM generation requires prior HL7 step "
            "to establish exam metadata."
        )
    
    patient = run_context['patient']
    accession_number = run_context['accession_number']
    study_uid = run_context.get('study_instance_uid') or pydicom.uid.generate_uid()
    
    # Generate DICOM files with ExamSpec metadata
    file_paths = dicom_generator.create_study_from_exam_spec(
        exam=exam,
        patient=patient,
        accession_number=accession_number,
        study_instance_uid=study_uid,
        referring_physician=step_config.get('referring_physician'),
        output_dir=step_config.get('output_dir', 'db-data/sim_runs')
    )
    
    # Store paths in context for DICOM send step
    run_context['dicom_file_paths'] = file_paths
    run_context['study_instance_uid'] = study_uid
    
    self.emit_event(
        f"Generated {len(file_paths)} DICOM instances across "
        f"{len(exam.series)} series for {exam.name}"
    )
    
    return file_paths
```

## Progress Log

| Date | Update |
| ---- | ------ |
| 2025-11-19 | Wired `ExamFactory` exposure through `/api/simulator/exams*` endpoints, added `ExamFilterParams`/`ExamSelectionRequest` validation, and landed backend/pytest coverage so the UI can inspect the live catalog before launching runs. |
| 2025-11-19 | Hardened `ExamFactory.list_exams()` metadata helpers for catalog summaries and added frontend API shims so the React client can request catalog slices and random selections. |
| 2025-11-19 | Schema guard compatibility fixes unblock the new API tests on SQLite, confirming the integration path is ready for SimulationRunner adoption. |

### Remaining Scope

- Replace the placeholder Faker-driven HL7/DICOM codepaths inside `simulation_runner.py` with ExamSpec-aware helpers outlined above.
- Update `dicom_generator` to consume `ExamSpec` objects end-to-end (tracked in EXAMGEN-4.2 but required before closing this work package).
- Add socket events/metrics so Simulator UI exposes which catalog exam was bound to a run.

## DICOM Generator Refactor

## Simulator API Additions

Expose the ExamFactory through authenticated simulator routes so the UI (and automation clients) can preview or pin specific studies before launching a run.

### Endpoints

- `GET /api/simulator/exams` &mdash; Returns the full catalog (or a filtered slice) along with catalog metadata and applied filters. Query params: `modality`, `body_part`, `setting`, `laterality`, `patient_age`, `patient_sex`.
- `GET /api/simulator/exams/<exam_id>` &mdash; Fetch a single `ExamSpec` by ID.
- `GET /api/simulator/exams/modalities` &mdash; Lists available modalities plus how many catalog entries map to each code.
- `POST /api/simulator/exams/select` &mdash; Unified selector that accepts `exam_id`, `cpt_code`, or weighted-random filters (same shape as query params) and returns the resolved `ExamSpec` with a `_selection` block describing the strategy.

### Example Requests

```bash
curl -H "X-API-Key: $KEY" "https://yeet.trazen.org/api/simulator/exams?setting=outpatient"

curl -H "Authorization: ApiKey $KEY" \
    -H "Content-Type: application/json" \
    -d '{"modality": "MR", "patient_age": 42}' \
    https://yeet.trazen.org/api/simulator/exams/select
```

The responses use the raw `ExamSpec` schema (serialized via Pydantic) so downstream clients receive modality, series protocols, CPT/LOINC codes, and contrast metadata without needing to inspect the JSON catalog directly.

### New Entry Point

```python
# app/util/dicom_generator.py
from app.models.exam_spec import ExamSpec

def create_study_from_exam_spec(exam: ExamSpec,
                                  patient,
                                  accession_number: str,
                                  study_instance_uid: str,
                                  referring_physician: str = None,
                                  output_dir: str = 'db-data/sim_runs') -> List[str]:
    """
    Generate complete DICOM study using ExamSpec protocol.
    
    Returns:
        List of absolute file paths to created DICOM files
    """
    from pydicom.dataset import Dataset, FileDataset
    from datetime import datetime
    import os
    
    file_paths = []
    study_date = datetime.now().strftime('%Y%m%d')
    study_time = datetime.now().strftime('%H%M%S')
    
    # Create output directory
    study_dir = os.path.join(output_dir, study_instance_uid)
    os.makedirs(study_dir, exist_ok=True)
    
    # Generate each series from ExamSpec
    for series_idx, series_protocol in enumerate(exam.series, start=1):
        series_uid = pydicom.uid.generate_uid()
        series_number = series_idx
        
        # Generate instances for this series
        for instance_idx in range(series_protocol.instances):
            instance_number = instance_idx + 1
            sop_instance_uid = pydicom.uid.generate_uid()
            
            # Create DICOM dataset
            ds = _create_dicom_instance(
                exam=exam,
                series_protocol=series_protocol,
                patient=patient,
                study_uid=study_instance_uid,
                series_uid=series_uid,
                sop_instance_uid=sop_instance_uid,
                accession_number=accession_number,
                series_number=series_number,
                instance_number=instance_number,
                study_date=study_date,
                study_time=study_time,
                referring_physician=referring_physician
            )
            
            # Generate pixel data
            ds = _add_pixel_data(ds, exam.modality, series_protocol)
            
            # Save file
            filename = f"{series_number:03d}_{instance_number:04d}.dcm"
            filepath = os.path.join(study_dir, filename)
            ds.save_as(filepath, write_like_original=False)
            file_paths.append(filepath)
    
    return file_paths

def _create_dicom_instance(exam: ExamSpec, 
                            series_protocol, 
                            patient, 
                            **kwargs) -> FileDataset:
    """Create single DICOM instance with complete metadata"""
    ds = FileDataset(
        filename="",
        dataset={},
        file_meta=_create_file_meta(exam.modality),
        preamble=b"\0" * 128
    )
    
    # Patient Module
    ds.PatientName = f"{patient.last_name}^{patient.first_name}"
    ds.PatientID = patient.mrn
    ds.PatientBirthDate = patient.date_of_birth.strftime('%Y%m%d')
    ds.PatientSex = patient.sex
    
    # Study Module
    ds.StudyInstanceUID = kwargs['study_uid']
    ds.StudyDate = kwargs['study_date']
    ds.StudyTime = kwargs['study_time']
    ds.AccessionNumber = kwargs['accession_number']
    ds.StudyDescription = exam.description
    ds.ReferringPhysicianName = kwargs.get('referring_physician', 'REFERRING^PHYSICIAN')
    ds.StudyID = kwargs['accession_number'][-6:]
    
    # Series Module
    ds.SeriesInstanceUID = kwargs['series_uid']
    ds.SeriesNumber = kwargs['series_number']
    ds.SeriesDescription = series_protocol.series_description
    ds.Modality = exam.modality
    ds.ProtocolName = series_protocol.protocol_name
    ds.SeriesDate = kwargs['study_date']
    ds.SeriesTime = kwargs['study_time']
    
    # General Equipment Module
    ds.Manufacturer = "HL7 Yeeter Simulator"
    ds.ManufacturerModelName = f"{exam.modality} Virtual Scanner"
    ds.SoftwareVersions = "1.0"
    
    # Image Module
    ds.InstanceNumber = kwargs['instance_number']
    ds.SOPInstanceUID = kwargs['sop_instance_uid']
    ds.SOPClassUID = _get_sop_class_uid(exam.modality)
    
    # Modality-Specific Attributes
    ds.BodyPartExamined = exam.body_part
    ds.Laterality = exam.laterality.value
    
    if exam.contrast != "none":
        ds.ContrastBolusAgent = exam.contrast_agent or "Contrast Medium"
        ds.ContrastBolusVolume = str(exam.contrast_volume_ml) if exam.contrast_volume_ml else ""
    
    # MR-specific
    if exam.modality == "MR" and series_protocol.sequence_name:
        ds.ScanningSequence = _parse_sequence_type(series_protocol.sequence_name)
        ds.SequenceName = series_protocol.sequence_name
        ds.MagneticFieldStrength = "1.5"  # Tesla
    
    # CT-specific
    if exam.modality == "CT":
        ds.KVP = "120"
        ds.XRayTubeCurrent = "200"
        ds.SliceThickness = "5.0"
    
    return ds
```

### Pixel Data Generation

```python
def _add_pixel_data(ds: FileDataset, modality: str, series_protocol) -> FileDataset:
    """Generate synthetic pixel data based on modality"""
    import numpy as np
    
    # Modality-specific image sizes
    dimensions = {
        'CT': (512, 512),
        'MR': (256, 256),
        'DX': (2048, 2048),
        'US': (640, 480),
        'MG': (2560, 3328),
        'NM': (128, 128)
    }
    
    rows, cols = dimensions.get(modality, (512, 512))
    
    # Generate realistic noise patterns
    if modality in ['CT', 'MR']:
        # Anatomical-like structures with Gaussian noise
        img = _generate_anatomical_phantom(rows, cols, modality)
    elif modality == 'DX':
        # Chest X-ray-like pattern
        img = _generate_xray_phantom(rows, cols)
    elif modality == 'US':
        # Speckle noise
        img = _generate_ultrasound_phantom(rows, cols)
    else:
        # Generic noise
        img = np.random.randint(0, 4096, (rows, cols), dtype=np.uint16)
    
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.PixelData = img.tobytes()
    
    return ds
```

## Step Configuration Schema Updates

### Old Format (Template-Based)

```python
{
    "step_type": "GENERATE_HL7",
    "template": "orm_radiology_template.txt",  # Uses faker strings
    "wait_after": 0
}
```

### New Format (ExamSpec-Based)

```python
# Option 1: Explicit exam ID
{
    "step_type": "GENERATE_HL7",
    "exam_id": "MR-KNEE-RIGHT-WO",
    "indication": "Right knee pain, evaluate for meniscal tear",  # Optional override
    "wait_after": 0
}

# Option 2: Random with constraints
{
    "step_type": "GENERATE_HL7",
    "modality": "CT",
    "setting": "emergency",
    "wait_after": 0
}

# Option 3: CPT code lookup
{
    "step_type": "GENERATE_HL7",
    "cpt_code": "73721",
    "wait_after": 0
}
```

## Validation Guards

```python
def handle_generate_dicom(self, step_config, run_context):
    """With validation guards"""
    
    exam = run_context.get('exam')
    if exam is None:
        raise ValueError(
            "DICOM generation requires ExamSpec in run_context. "
            "Ensure a GENERATE_HL7 step runs before GENERATE_DICOM."
        )
    
    # Validate consistency with HL7 metadata (if available)
    if 'order_description' in run_context:
        hl7_description = run_context['order_description']
        if hl7_description != exam.description:
            logger.warning(
                f"Description mismatch: HL7='{hl7_description}' vs "
                f"ExamSpec='{exam.description}'. Using ExamSpec."
            )
    
    # Validate patient demographics against exam constraints
    patient = run_context['patient']
    if exam.required_sex and patient.sex != exam.required_sex:
        raise ValueError(
            f"Exam {exam.id} requires sex={exam.required_sex}, "
            f"but patient is {patient.sex}"
        )
    
    if exam.min_age and patient.age < exam.min_age:
        raise ValueError(
            f"Exam {exam.id} requires min_age={exam.min_age}, "
            f"but patient is {patient.age}"
        )
    
    # Proceed with generation...
```

## Implementation Checklist

- [ ] Refactor `handle_generate_hl7()` to use `ExamFactory`
- [ ] Implement `_build_hl7_from_exam()` method
- [ ] Refactor `handle_generate_dicom()` to require `ExamSpec` in context
- [ ] Create `dicom_generator.create_study_from_exam_spec()` function
- [ ] Implement `_create_dicom_instance()` with full metadata
- [ ] Add validation guards for missing ExamSpec
- [ ] Update `handle_send_dmwl()` to use ExamSpec protocols
- [ ] Remove deprecated `_infer_modality_from_description()` method
- [ ] Remove random modality fallback logic (lines 647-697)
- [ ] Add unit tests for each refactored method
- [ ] Update existing simulation templates to new step format
- [ ] Run integration tests with 10-patient async simulation
- [ ] Verify no modality mismatches in generated DICOM files

## Migration Path

### Phase 1: Coexistence (1 week)
- New code paths use ExamSpec
- Old template-based paths still functional
- Log warnings when old paths are used

### Phase 2: Template Deprecation (1 week)
- Convert existing templates to new format
- Mark old methods as deprecated
- Update documentation

### Phase 3: Removal (After testing)
- Delete deprecated methods
- Remove faker_parser study/modality tuple logic
- Clean up codebase

## Next Steps

See [EXAMGEN-5.0: Template Migration](EXAMGEN-5.0-Template-Migration.md) for converting existing HL7 templates to ExamSpec format.
