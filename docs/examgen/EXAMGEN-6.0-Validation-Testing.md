# EXAMGEN-6.0: Validation & Testing Strategy

**Status:** Not Started  
**Created:** 2025-01-18  
**Previous:** [EXAMGEN-5.0](EXAMGEN-5.0-Template-Migration.md)  
**Next:** [EXAMGEN-7.0](EXAMGEN-7.0-Telemetry-Monitoring.md)

## Purpose

Establish comprehensive testing and validation framework to ensure ExamSpec-driven generation produces consistent, high-quality metadata across HL7, DMWL, and DICOM outputs.

## Testing Pyramid

```
         ┌────────────────┐
         │  E2E Tests     │  (10 tests)
         │  Full workflow │
         └────────────────┘
       ┌──────────────────────┐
       │  Integration Tests   │  (50 tests)
       │  Multi-component     │
       └──────────────────────┘
    ┌──────────────────────────────┐
    │      Unit Tests              │  (200+ tests)
    │  Individual functions        │
    └──────────────────────────────┘
```

## Unit Tests

### ExamSpec Schema Validation

```python
# tests/test_exam_spec.py
import pytest
from app.models.exam_spec import ExamSpec, Laterality, ContrastType, ProcedureCode

def test_exam_spec_valid_minimal():
    """Test minimal valid ExamSpec"""
    exam = ExamSpec(
        id="TEST-CT-HEAD",
        modality="CT",
        name="Test CT Head",
        description="CT HEAD W/O CONTRAST",
        body_part="HEAD",
        laterality=Laterality.UNPAIRED,
        series=[
            {
                "protocol_name": "HEAD STD",
                "series_description": "HEAD 5.0 STD",
                "instances": 35
            }
        ],
        estimated_duration_min=5.0
    )
    assert exam.modality == "CT"
    assert len(exam.series) == 1

def test_exam_spec_invalid_modality():
    """Test that invalid modality raises ValidationError"""
    with pytest.raises(ValueError, match="Modality must be one of"):
        ExamSpec(
            id="TEST-INVALID",
            modality="INVALID",  # Not a valid DICOM modality
            name="Invalid",
            description="Invalid",
            body_part="HEAD",
            series=[{"protocol_name": "TEST", "series_description": "TEST", "instances": 1}],
            estimated_duration_min=5.0
        )

def test_exam_spec_laterality_validation():
    """Test laterality consistency"""
    exam = ExamSpec(
        id="MR-KNEE-RIGHT-WO",
        modality="MR",
        name="MRI Knee Right",
        description="MRI KNEE RIGHT W/O CONTRAST",
        body_part="KNEE",
        laterality=Laterality.RIGHT,  # Should match "RIGHT" in description
        series=[{"protocol_name": "SAG T1", "series_description": "SAG T1 KNEE", "instances": 25}],
        estimated_duration_min=25.0
    )
    assert exam.laterality == Laterality.RIGHT
    assert "RIGHT" in exam.description

def test_exam_spec_demographic_constraints():
    """Test age/sex constraint validation"""
    exam = ExamSpec(
        id="US-OB-FIRST-TRI",
        modality="US",
        name="OB Ultrasound First Trimester",
        description="US OB FIRST TRIMESTER",
        body_part="UTERUS",
        required_sex="F",
        min_age=15,
        max_age=50,
        series=[{"protocol_name": "OB US", "series_description": "OB US", "instances": 1}],
        estimated_duration_min=15.0
    )
    assert exam.required_sex == "F"
    assert exam.min_age == 15
    assert exam.max_age == 50
```

### ExamCatalog Tests

```python
# tests/test_exam_catalog.py
def test_catalog_load_from_json(tmp_path):
    """Test catalog loading from JSON file"""
    catalog_data = {
        "schema_version": "1.0",
        "catalog_version": "2025.1.0",
        "metadata": {"total_exams": 1},
        "exams": [
            {
                "id": "TEST-CT-HEAD",
                "modality": "CT",
                "name": "Test CT Head",
                "description": "CT HEAD W/O CONTRAST",
                "body_part": "HEAD",
                "laterality": "",
                "series": [{"protocol_name": "HEAD", "series_description": "HEAD", "instances": 35}],
                "estimated_duration_min": 5.0
            }
        ]
    }
    
    catalog_path = tmp_path / "test_catalog.json"
    with open(catalog_path, 'w') as f:
        json.dump(catalog_data, f)
    
    from app.catalog import ExamCatalog
    catalog = ExamCatalog()
    catalog.load_from_file(str(catalog_path))
    
    assert len(catalog._exams) == 1
    assert catalog.get_by_id("TEST-CT-HEAD").modality == "CT"

def test_catalog_get_by_modality():
    """Test modality filtering"""
    catalog = load_test_catalog()  # Fixture with multiple exams
    ct_exams = catalog.get_by_modality("CT")
    assert all(e.modality == "CT" for e in ct_exams)
    assert len(ct_exams) >= 1

def test_catalog_weighted_random():
    """Test weighted random selection"""
    catalog = load_test_catalog()
    
    # Run 1000 selections, verify high-weight exams selected more often
    selections = Counter()
    for _ in range(1000):
        exam = catalog.get_random_exam(modality="CT")
        selections[exam.id] += 1
    
    # Exam with weight=3.0 should be ~3x more common than weight=1.0
    high_weight_exam = next(e for e in catalog._exams if e.frequency_weight == 3.0 and e.modality == "CT")
    low_weight_exam = next(e for e in catalog._exams if e.frequency_weight == 1.0 and e.modality == "CT")
    
    ratio = selections[high_weight_exam.id] / selections[low_weight_exam.id]
    assert 2.0 < ratio < 4.0  # Allow 33% variance
```

### ExamFactory Tests

```python
# tests/test_exam_factory.py
def test_factory_get_exam_by_id():
    """Test explicit exam ID lookup"""
    factory = ExamFactory()
    exam = factory.get_exam_by_id("CT-HEAD-WO")
    assert exam.id == "CT-HEAD-WO"
    assert exam.modality == "CT"

def test_factory_get_exam_by_id_not_found():
    """Test error when exam ID doesn't exist"""
    factory = ExamFactory()
    with pytest.raises(ValueError, match="not found in catalog"):
        factory.get_exam_by_id("NONEXISTENT-EXAM")

def test_factory_random_with_demographic_filters():
    """Test patient demographic filtering"""
    factory = ExamFactory()
    
    # Female-only exam (mammography)
    exam = factory.get_random_exam(
        modality="MG",
        patient_sex="F",
        patient_age=45
    )
    assert exam.modality == "MG"
    assert exam.required_sex is None or exam.required_sex == "F"
    
    # Should raise error for male patient
    with pytest.raises(ValueError, match="No exams match"):
        factory.get_random_exam(
            modality="MG",
            patient_sex="M"
        )

def test_factory_cpt_code_lookup():
    """Test CPT code resolution"""
    factory = ExamFactory()
    exam = factory.get_exam_by_cpt_code("70450")  # CT Head w/o contrast
    assert exam.modality == "CT"
    assert "HEAD" in exam.body_part.upper()
```

## Integration Tests

### SimulationRunner Tests

```python
# tests/test_simulation_runner_integration.py
def test_hl7_generation_with_exam_spec(app, test_user):
    """Test HL7 generation uses ExamSpec correctly"""
    runner = SimulationRunner()
    
    run_context = {
        'patient': create_fake_patient(age=42, sex='F'),
        'accession_number': '20250118001'
    }
    
    step_config = {
        'exam_id': 'MR-BRAIN-WO'
    }
    
    hl7_message = runner.handle_generate_hl7(step_config, run_context)
    
    # Verify exam stored in context
    assert 'exam' in run_context
    assert run_context['exam'].id == 'MR-BRAIN-WO'
    
    # Parse HL7 and verify metadata
    parsed = hl7apy.parse_message(hl7_message)
    obr = parsed.OBR
    
    assert obr.OBR_4.OBR_4_2.value == "MRI BRAIN W/O CONTRAST"  # Description
    assert obr.OBR_24.value == "MR"  # Modality
    assert obr.OBR_4.OBR_4_1.value == "70551"  # CPT code

def test_dicom_generation_requires_exam_spec(app, test_user):
    """Test DICOM generation fails without ExamSpec in context"""
    runner = SimulationRunner()
    
    run_context = {
        'patient': create_fake_patient(),
        'accession_number': '20250118002'
        # Missing 'exam' key
    }
    
    step_config = {}
    
    with pytest.raises(ValueError, match="No ExamSpec in context"):
        runner.handle_generate_dicom(step_config, run_context)

def test_end_to_end_hl7_to_dicom_consistency(app, test_user):
    """Test metadata consistency from HL7 → DICOM"""
    runner = SimulationRunner()
    
    run_context = {
        'patient': create_fake_patient(),
        'accession_number': '20250118003'
    }
    
    # Step 1: Generate HL7
    hl7_message = runner.handle_generate_hl7(
        {'exam_id': 'CT-CHEST-W'},
        run_context
    )
    
    # Step 2: Generate DICOM
    dicom_files = runner.handle_generate_dicom(
        {'output_dir': '/tmp/test_dicom'},
        run_context
    )
    
    # Step 3: Verify consistency
    exam = run_context['exam']
    
    # Parse first DICOM file
    ds = pydicom.dcmread(dicom_files[0])
    
    assert ds.Modality == exam.modality == "CT"
    assert ds.StudyDescription == exam.description
    assert ds.BodyPartExamined == exam.body_part
    assert ds.AccessionNumber == run_context['accession_number']
    
    # Verify series count matches ExamSpec
    series_uids = set(pydicom.dcmread(f).SeriesInstanceUID for f in dicom_files)
    assert len(series_uids) == len(exam.series)
```

### DMWL Integration Tests

```python
# tests/test_dmwl_integration.py
def test_dmwl_message_from_exam_spec(app, test_user):
    """Test DMWL worklist entry generation"""
    runner = SimulationRunner()
    
    run_context = {
        'patient': create_fake_patient(),
        'accession_number': '20250118004',
        'exam': get_exam_factory().get_exam_by_id('MR-KNEE-RIGHT-WO')
    }
    
    ds = runner._build_dmwl_from_exam(
        run_context['exam'],
        run_context['patient'],
        run_context['accession_number']
    )
    
    # Verify DICOM MWL dataset
    assert ds.Modality == "MR"
    assert "KNEE" in ds.ScheduledProcedureStepSequence[0].ScheduledProcedureStepDescription
    assert ds.AccessionNumber == '20250118004'
    
    # Verify protocol codes
    protocols = ds.ScheduledProcedureStepSequence[0].ScheduledProtocolCodeSequence
    assert len(protocols) == 4  # MR knee has 4 series
```

## Validation Tests

### Metadata Consistency Checks

```python
# tests/test_metadata_validation.py
def test_no_modality_mismatches_in_catalog():
    """Ensure catalog has no description/modality conflicts"""
    catalog = get_catalog()
    
    errors = []
    for exam in catalog._exams:
        # Extract modality keywords from description
        desc_upper = exam.description.upper()
        
        modality_keywords = {
            'CT': ['CT', 'COMPUTED TOMOGRAPHY'],
            'MR': ['MRI', 'MR ', 'MAGNETIC RESONANCE'],
            'DX': ['XRAY', 'X-RAY', 'RADIOGRAPH'],
            'US': ['ULTRASOUND', 'US ', 'DOPPLER'],
            'MG': ['MAMMOGRAM', 'MAMMO'],
            'NM': ['BONE SCAN', 'NUCLEAR']
        }
        
        expected_keywords = modality_keywords.get(exam.modality, [])
        if expected_keywords:
            if not any(kw in desc_upper for kw in expected_keywords):
                errors.append(
                    f"{exam.id}: Description '{exam.description}' doesn't match "
                    f"modality '{exam.modality}'"
                )
    
    assert len(errors) == 0, "\n".join(errors)

def test_laterality_consistency():
    """Ensure laterality in description matches laterality field"""
    catalog = get_catalog()
    
    errors = []
    for exam in catalog._exams:
        desc_upper = exam.description.upper()
        
        if exam.laterality == Laterality.RIGHT:
            if 'RIGHT' not in desc_upper and 'RT' not in desc_upper:
                errors.append(f"{exam.id}: Missing 'RIGHT' in description")
        
        elif exam.laterality == Laterality.LEFT:
            if 'LEFT' not in desc_upper and 'LT' not in desc_upper:
                errors.append(f"{exam.id}: Missing 'LEFT' in description")
        
        elif exam.laterality == Laterality.BILATERAL:
            if 'BILATERAL' not in desc_upper and 'BILAT' not in desc_upper:
                errors.append(f"{exam.id}: Missing 'BILATERAL' in description")
    
    assert len(errors) == 0, "\n".join(errors)

def test_cpt_code_validity():
    """Verify all CPT codes are valid 5-digit codes"""
    catalog = get_catalog()
    vocab = get_vocabulary()
    
    errors = []
    for exam in catalog._exams:
        for code in exam.procedure_codes:
            if code.system == "CPT":
                if not vocab.cpt.validate_cpt_code(code.code):
                    errors.append(
                        f"{exam.id}: Invalid CPT code '{code.code}'"
                    )
    
    assert len(errors) == 0, "\n".join(errors)
```

### Demographic Constraint Tests

```python
# tests/test_demographic_constraints.py
def test_age_constraints_enforced():
    """Test age filtering in factory"""
    factory = ExamFactory()
    
    # Pediatric exam (max age 18)
    pediatric_exam = factory.get_random_exam(
        modality="DX",
        patient_age=10
    )
    assert pediatric_exam.max_age is None or pediatric_exam.max_age >= 10
    
    # Should not select obstetric exam for 10-year-old
    with pytest.raises(ValueError):
        factory.get_random_exam(
            modality="US",
            body_part="UTERUS",
            patient_age=10
        )

def test_sex_constraints_enforced():
    """Test sex filtering in factory"""
    factory = ExamFactory()
    
    # Mammography is female-only
    with pytest.raises(ValueError, match="No exams match"):
        factory.get_random_exam(
            modality="MG",
            patient_sex="M"
        )
    
    # Prostate MRI is male-only
    prostate_exam = factory.get_exam_by_id("MR-PROSTATE")
    assert prostate_exam.required_sex == "M"
```

## End-to-End Tests

### Full Simulation Workflow

```python
# tests/test_e2e_simulation.py
def test_complete_simulation_no_mismatches(app, test_user):
    """Run 100-patient simulation, verify zero metadata mismatches"""
    
    # Create simulation template with multi-step workflow
    template = create_test_template(
        name="E2E Test Template",
        steps=[
            {'step_type': 'GENERATE_HL7', 'exam_filters': {'modality': 'CT'}},
            {'step_type': 'SEND_MLLP', 'endpoint_id': test_endpoint.id},
            {'step_type': 'GENERATE_DICOM'},
            {'step_type': 'SEND_DICOM', 'endpoint_id': test_pacs_endpoint.id}
        ]
    )
    
    # Run simulation
    run = start_simulation_async(template.id, patient_count=100)
    
    # Wait for completion
    wait_for_simulation_completion(run.id, timeout=300)
    
    # Collect all events
    events = SimulationRunEvent.query.filter_by(run_id=run.id).all()
    
    # Extract metadata from events
    mismatches = []
    for patient_idx in range(100):
        hl7_events = [e for e in events if f"patient_{patient_idx}" in e.event_data and "HL7" in e.event_type]
        dicom_events = [e for e in events if f"patient_{patient_idx}" in e.event_data and "DICOM" in e.event_type]
        
        if hl7_events and dicom_events:
            # Parse metadata
            hl7_modality = extract_modality_from_hl7(hl7_events[0].event_data)
            dicom_modality = extract_modality_from_dicom_event(dicom_events[0].event_data)
            
            if hl7_modality != dicom_modality:
                mismatches.append({
                    'patient': patient_idx,
                    'hl7_modality': hl7_modality,
                    'dicom_modality': dicom_modality
                })
    
    # Assert zero mismatches
    assert len(mismatches) == 0, f"Found {len(mismatches)} metadata mismatches: {mismatches}"

def test_pacs_compatibility(app, test_user):
    """Verify generated DICOM files pass PACS validator"""
    runner = SimulationRunner()
    
    # Generate DICOM study
    run_context = {
        'patient': create_fake_patient(),
        'accession_number': '20250118005',
        'exam': get_exam_factory().get_exam_by_id('CT-CHEST-W')
    }
    
    runner.handle_generate_hl7({}, run_context)
    dicom_files = runner.handle_generate_dicom({'output_dir': '/tmp/pacs_test'}, run_context)
    
    # Run PACS validator (uses pacs_validator.py)
    from app.util.pacs_validator import validate_dicom_study
    
    validation_results = validate_dicom_study(dicom_files)
    
    assert validation_results['valid'] is True
    assert len(validation_results['errors']) == 0
    assert len(validation_results['warnings']) <= 5  # Allow minor warnings
```

## Performance Tests

```python
# tests/test_performance.py
def test_catalog_load_performance():
    """Verify catalog loads in <100ms"""
    import time
    
    start = time.time()
    catalog = get_catalog()  # First load (cold)
    duration = time.time() - start
    
    assert duration < 0.1, f"Catalog load took {duration:.3f}s (should be <0.1s)"

def test_exam_selection_performance():
    """Verify weighted random selection is <1ms"""
    factory = ExamFactory()
    
    start = time.time()
    for _ in range(1000):
        exam = factory.get_random_exam(modality="CT")
    duration = time.time() - start
    
    avg_time_ms = (duration / 1000) * 1000
    assert avg_time_ms < 1.0, f"Average selection time: {avg_time_ms:.3f}ms (should be <1ms)"

def test_dicom_generation_performance():
    """Verify DICOM generation is <500ms per study"""
    runner = SimulationRunner()
    
    run_context = {
        'patient': create_fake_patient(),
        'accession_number': '20250118006',
        'exam': get_exam_factory().get_exam_by_id('MR-BRAIN-WO')
    }
    
    runner.handle_generate_hl7({}, run_context)
    
    start = time.time()
    dicom_files = runner.handle_generate_dicom({'output_dir': '/tmp/perf_test'}, run_context)
    duration = time.time() - start
    
    assert duration < 0.5, f"DICOM generation took {duration:.3f}s (should be <0.5s)"
```

## Continuous Integration Tests

### GitHub Actions Workflow

```yaml
# .github/workflows/examgen_tests.yml
name: ExamGen Tests

on:
  push:
    paths:
      - 'app/catalog/**'
      - 'app/models/exam_spec.py'
      - 'app/util/simulation_runner.py'
      - 'app/util/dicom_generator.py'
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      run: pytest tests/test_exam_spec.py tests/test_exam_catalog.py tests/test_exam_factory.py -v --cov=app/catalog
    
    - name: Run integration tests
      run: pytest tests/test_simulation_runner_integration.py -v
    
    - name: Run metadata validation tests
      run: pytest tests/test_metadata_validation.py -v
    
    - name: Generate coverage report
      run: pytest --cov=app --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

## Implementation Checklist

- [ ] Create `tests/test_exam_spec.py` with 20+ unit tests
- [ ] Create `tests/test_exam_catalog.py` with catalog loading tests
- [ ] Create `tests/test_exam_factory.py` with factory method tests
- [ ] Create `tests/test_simulation_runner_integration.py` with HL7/DICOM tests
- [ ] Create `tests/test_metadata_validation.py` with consistency checks
- [ ] Create `tests/test_e2e_simulation.py` with 100-patient workflow test
- [ ] Create `tests/test_performance.py` with benchmarks
- [ ] Add GitHub Actions workflow for CI
- [ ] Set up code coverage reporting (target: >80%)
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Document test execution in README
- [ ] Add pre-commit hook to run metadata validation

## Success Metrics

- **Unit Tests:** 200+ tests, 100% pass rate
- **Integration Tests:** 50+ tests, 100% pass rate
- **E2E Tests:** 10+ tests, 100% pass rate
- **Code Coverage:** >80% for `app/catalog/` and `app/util/simulation_runner.py`
- **Metadata Consistency:** 0 modality mismatches in 1000-sample CI run
- **Performance:** <100ms catalog load, <1ms exam selection, <500ms DICOM generation

## Next Steps

See [EXAMGEN-7.0: Telemetry & Monitoring](EXAMGEN-7.0-Telemetry-Monitoring.md) for production observability.
