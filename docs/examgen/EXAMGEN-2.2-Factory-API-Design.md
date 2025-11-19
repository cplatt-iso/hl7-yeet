# EXAMGEN-2.2: Factory API Design

**Status:** Complete  
**Created:** 2025-11-18  
**Previous:** [EXAMGEN-2.1](EXAMGEN-2.1-Catalog-Data-Model.md)  
**Next:** [EXAMGEN-3.0](EXAMGEN-3.0-Initial-Catalog-Population.md)

## Purpose

Define the public interface for selecting and instantiating ExamSpec instances, providing a clean abstraction layer between catalog internals and consuming code (simulation runner, API routes).

## Design Goals

1. **Simplicity:** Single entry point for all exam selection logic
2. **Flexibility:** Support multiple selection strategies (random, explicit ID, constraint-based)
3. **Traceability:** Log selection decisions for debugging
4. **Testability:** Allow mock catalog injection for unit tests
5. **Type Safety:** Return typed ExamSpec objects, not raw dicts

## Factory Interface

### Core API

```python
# app/catalog/factory.py
from typing import Optional, List, Dict, Any
from app.models.exam_spec import ExamSpec, Laterality
from app.catalog import get_catalog
import random
import logging

logger = logging.getLogger(__name__)

class ExamFactory:
    """Factory for selecting and instantiating ExamSpec instances"""
    
    def __init__(self, catalog=None):
        """
        Args:
            catalog: Optional ExamCatalog for dependency injection (testing)
        """
        self._catalog = catalog or get_catalog()
    
    def get_exam_by_id(self, exam_id: str) -> ExamSpec:
        """
        Get specific exam by ID.
        
        Args:
            exam_id: Unique exam identifier (e.g., "MR-BRAIN-WO")
        
        Returns:
            ExamSpec instance
        
        Raises:
            ValueError: If exam_id not found in catalog
        """
        exam = self._catalog.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam ID '{exam_id}' not found in catalog")
        
        logger.info(f"Selected exam by ID: {exam_id}")
        return exam
    
    def get_random_exam(self, 
                        modality: Optional[str] = None,
                        body_part: Optional[str] = None,
                        laterality: Optional[Laterality] = None,
                        setting: Optional[str] = None,
                        patient_age: Optional[int] = None,
                        patient_sex: Optional[str] = None) -> ExamSpec:
        """
        Select random exam using weighted distribution and optional constraints.
        
        Args:
            modality: Filter by DICOM modality code (CT, MR, etc.)
            body_part: Filter by body part examined
            laterality: Filter by laterality requirement
            setting: Filter by clinical setting (outpatient, emergency, etc.)
            patient_age: Filter by age constraints in ExamSpec
            patient_sex: Filter by required_sex field (M/F)
        
        Returns:
            ExamSpec instance selected via weighted random choice
        
        Raises:
            ValueError: If no exams match the provided constraints
        """
        candidates = self._catalog._exams
        
        # Apply filters
        if modality:
            candidates = [e for e in candidates if e.modality == modality]
        if body_part:
            candidates = [e for e in candidates if e.body_part == body_part]
        if laterality:
            candidates = [e for e in candidates if e.laterality == laterality]
        if setting:
            candidates = [e for e in candidates if setting in e.setting]
        
        # Demographic filters
        if patient_age is not None:
            candidates = [
                e for e in candidates 
                if (e.min_age is None or e.min_age <= patient_age) and
                   (e.max_age is None or e.max_age >= patient_age)
            ]
        if patient_sex:
            candidates = [
                e for e in candidates
                if e.required_sex is None or e.required_sex == patient_sex
            ]
        
        if not candidates:
            filter_desc = ", ".join([
                f"{k}={v}" for k, v in {
                    'modality': modality,
                    'body_part': body_part,
                    'laterality': laterality,
                    'setting': setting,
                    'age': patient_age,
                    'sex': patient_sex
                }.items() if v is not None
            ])
            raise ValueError(f"No exams match filters: {filter_desc}")
        
        # Weighted random selection
        weights = [e.frequency_weight for e in candidates]
        selected = random.choices(candidates, weights=weights)[0]
        
        logger.info(
            f"Selected exam: {selected.id} (filters: {filter_desc}, "
            f"pool size: {len(candidates)})"
        )
        return selected
    
    def get_exam_by_cpt_code(self, cpt_code: str) -> ExamSpec:
        """
        Look up exam by CPT procedure code.
        
        Args:
            cpt_code: 5-digit CPT code string
        
        Returns:
            ExamSpec instance
        
        Raises:
            ValueError: If CPT code not found or maps to multiple exams
        """
        exam = self._catalog._by_cpt_code.get(cpt_code)
        if exam is None:
            raise ValueError(f"CPT code '{cpt_code}' not found in catalog")
        
        logger.info(f"Selected exam by CPT code {cpt_code}: {exam.id}")
        return exam
    
    def get_exams_by_modality(self, modality: str) -> List[ExamSpec]:
        """
        Get all exams for a specific modality (for UI dropdowns).
        
        Args:
            modality: DICOM modality code
        
        Returns:
            List of ExamSpec instances sorted by name
        """
        exams = self._catalog.get_by_modality(modality)
        return sorted(exams, key=lambda e: e.name)
    
    def get_available_modalities(self) -> List[str]:
        """Get list of modalities with at least one exam defined"""
        return sorted(self._catalog._by_modality.keys())
    
    def resolve_template_string(self, template: str, **context) -> ExamSpec:
        """
        Parse template string and select exam (transitional API).
        
        Supports formats:
        - "exam_id:MR-BRAIN-WO"
        - "random:CT"
        - "cpt:70450"
        
        Args:
            template: Template string from SimulationStep
            context: Additional context (patient data, etc.)
        
        Returns:
            ExamSpec instance
        """
        if template.startswith("exam_id:"):
            exam_id = template.split(":", 1)[1]
            return self.get_exam_by_id(exam_id)
        
        elif template.startswith("random:"):
            modality = template.split(":", 1)[1] if ":" in template else None
            return self.get_random_exam(
                modality=modality,
                patient_age=context.get('patient_age'),
                patient_sex=context.get('patient_sex')
            )
        
        elif template.startswith("cpt:"):
            cpt_code = template.split(":", 1)[1]
            return self.get_exam_by_cpt_code(cpt_code)
        
        else:
            # Legacy fallback: treat as exam ID
            logger.warning(f"Using legacy exam ID format: {template}")
            return self.get_exam_by_id(template)

# Singleton instance
_factory_instance: Optional[ExamFactory] = None

def get_exam_factory() -> ExamFactory:
    """Get singleton factory instance"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ExamFactory()
    return _factory_instance
```

## Usage Examples

### Simulation Runner Integration

```python
# app/util/simulation_runner.py
from app.catalog.factory import get_exam_factory

class SimulationRunner:
    def __init__(self):
        self.exam_factory = get_exam_factory()
    
    def handle_generate_hl7(self, step_config: Dict, run_context: Dict) -> str:
        """Generate HL7 message using ExamSpec"""
        
        # Option 1: Explicit exam ID in template
        if 'exam_id' in step_config:
            exam = self.exam_factory.get_exam_by_id(step_config['exam_id'])
        
        # Option 2: Random with constraints
        elif 'random_exam' in step_config:
            patient = run_context['patient']
            exam = self.exam_factory.get_random_exam(
                modality=step_config.get('modality'),
                setting=step_config.get('setting', 'outpatient'),
                patient_age=patient.age,
                patient_sex=patient.sex
            )
        
        # Option 3: Legacy template string
        else:
            template = step_config.get('procedure_template', 'random:')
            exam = self.exam_factory.resolve_template_string(
                template,
                patient_age=run_context['patient'].age,
                patient_sex=run_context['patient'].sex
            )
        
        # Store exam in context for downstream steps
        run_context['exam'] = exam
        
        # Generate HL7 message using exam metadata
        hl7_message = self._build_hl7_from_exam(exam, run_context)
        return hl7_message
    
    def handle_generate_dicom(self, step_config: Dict, run_context: Dict) -> List[str]:
        """Generate DICOM files using ExamSpec from context"""
        
        # Retrieve exam from earlier HL7 generation step
        exam = run_context.get('exam')
        if exam is None:
            raise ValueError("No ExamSpec in run_context - did HL7 step run first?")
        
        # Pass exam to DICOM generator
        file_paths = dicom_generator.create_study_from_exam_spec(
            exam=exam,
            patient=run_context['patient'],
            accession_number=run_context['accession_number'],
            study_instance_uid=run_context['study_instance_uid']
        )
        
        return file_paths
```

## Implementation Notes (2025-11-18)

- Implemented in `app/catalog/factory.py` with `ExamFactory` class that wraps the catalog, exposes `get_exam_by_id`, `get_exam_by_cpt_code`, `get_random_exam`, `get_exams_by_modality`, `get_available_modalities`, and `resolve_template_string`, plus the singleton `get_exam_factory()`.
- `ExamFactory.get_random_exam()` delegates to the strengthened `ExamCatalog.get_random_exam()` filters (modality/body part/setting/laterality/demographics) and logs the final selection with structured filter metadata.
- Template parsing supports `exam_id:`, `random:` (optional modality), `cpt:`, and legacy plain IDs; random selection respects optional `patient_age`/`patient_sex` context with type-checked helpers.
- New unit coverage lives in `tests/test_exam_factory.py`, using deterministic RNG injection to make weighted sampling predictable under pytest.
- Simulation runner and API integration will consume `get_exam_factory()` in EXAMGEN-4.x work; for now the module can already be imported anywhere needing consistent exam lookup.

### API Route for Manual Selection

```python
# app/routes/simulator_routes.py
from app.catalog.factory import get_exam_factory

@simulator_bp.route('/exams/random', methods=['POST'])
@jwt_required()
def get_random_exam_api():
    """
    Select random exam for manual simulation.
    
    Request body:
    {
        "modality": "MR",
        "setting": "emergency",
        "patient_age": 42,
        "patient_sex": "F"
    }
    """
    data = request.get_json()
    factory = get_exam_factory()
    
    try:
        exam = factory.get_random_exam(
            modality=data.get('modality'),
            body_part=data.get('body_part'),
            setting=data.get('setting'),
            patient_age=data.get('patient_age'),
            patient_sex=data.get('patient_sex')
        )
        
        return jsonify(exam.dict()), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@simulator_bp.route('/exams/modalities', methods=['GET'])
def get_modalities_api():
    """Get list of available modalities"""
    factory = get_exam_factory()
    return jsonify({
        'modalities': factory.get_available_modalities()
    }), 200
```

### Testing with Mock Catalog

```python
# tests/test_exam_factory.py
import pytest
from app.catalog.factory import ExamFactory
from app.models.exam_spec import ExamSpec, Laterality

@pytest.fixture
def mock_catalog():
    """Create minimal catalog for testing"""
    class MockCatalog:
        def __init__(self):
            self._exams = [
                ExamSpec(
                    id="TEST-CT-HEAD",
                    modality="CT",
                    name="Test CT Head",
                    description="CT HEAD W/O CONTRAST",
                    body_part="HEAD",
                    laterality=Laterality.UNPAIRED,
                    series=[/* minimal series */],
                    estimated_duration_min=10.0,
                    frequency_weight=1.0,
                    setting=["emergency"]
                ),
                # ... more test exams
            ]
            self._by_id = {e.id: e for e in self._exams}
        
        def get_by_id(self, exam_id):
            return self._by_id.get(exam_id)
    
    return MockCatalog()

def test_get_exam_by_id(mock_catalog):
    factory = ExamFactory(catalog=mock_catalog)
    exam = factory.get_exam_by_id("TEST-CT-HEAD")
    assert exam.modality == "CT"
    assert exam.body_part == "HEAD"

def test_get_random_exam_with_filters(mock_catalog):
    factory = ExamFactory(catalog=mock_catalog)
    exam = factory.get_random_exam(modality="CT", setting="emergency")
    assert exam.modality == "CT"
    assert "emergency" in exam.setting

def test_no_matching_exams_raises_error(mock_catalog):
    factory = ExamFactory(catalog=mock_catalog)
    with pytest.raises(ValueError, match="No exams match"):
        factory.get_random_exam(modality="MG")  # No mammography in mock
```

## Selection Strategy Details

### Weighted Random Algorithm

```python
# Pseudocode for weighted selection
def weighted_random(candidates: List[ExamSpec]) -> ExamSpec:
    """
    Use frequency_weight as probability modifier:
    - weight=1.0: baseline frequency
    - weight=2.0: twice as likely to be selected
    - weight=0.5: half as likely
    
    Implementation uses random.choices() with weights parameter.
    """
    weights = [e.frequency_weight for e in candidates]
    total_weight = sum(weights)
    
    # Normalize to probabilities
    probabilities = [w / total_weight for w in weights]
    
    # Select one exam
    return random.choices(candidates, weights=weights)[0]
```

### Default Weights by Setting

```python
# Suggested weights for realistic distributions
SETTING_WEIGHTS = {
    'outpatient': {
        'MR-KNEE': 2.0,       # Common MSK
        'MR-LSPINE': 1.8,     # Very common back pain
        'CT-ABDPELVIS': 1.5,  # Common diagnostic
        'DX-CHEST': 3.0,      # Most common X-ray
        'US-ABDOMEN': 1.2,    # Moderate
    },
    'emergency': {
        'CT-HEAD': 2.5,       # Common trauma/stroke workup
        'CT-CHEST': 2.0,      # PE/trauma protocol
        'DX-CHEST': 3.0,      # Always high volume
        'US-ABDOMEN': 0.8,    # Less common in ER
    },
    'inpatient': {
        'CT-CHEST': 1.8,      # Follow-up imaging
        'DX-CHEST': 2.5,      # Portable films
        'US-DOPPLER': 1.2,    # DVT checks
    }
}
```

## Error Handling

### User-Facing Errors

```python
class ExamSelectionError(Exception):
    """Base exception for exam selection failures"""
    pass

class ExamNotFoundError(ExamSelectionError):
    """Exam ID or code not found in catalog"""
    def __init__(self, identifier: str, lookup_type: str = "ID"):
        super().__init__(f"Exam {lookup_type} '{identifier}' not found")

class NoMatchingExamsError(ExamSelectionError):
    """No exams match provided constraints"""
    def __init__(self, filters: Dict[str, Any]):
        filter_str = ", ".join(f"{k}={v}" for k, v in filters.items())
        super().__init__(f"No exams match filters: {filter_str}")
```

## Performance Benchmarks

```python
# Expected performance characteristics
import timeit

def benchmark_factory():
    factory = get_exam_factory()
    
    # Get by ID (O(1) dict lookup)
    time_by_id = timeit.timeit(
        lambda: factory.get_exam_by_id("MR-BRAIN-WO"),
        number=10000
    )
    print(f"By ID: {time_by_id / 10000 * 1000:.3f}ms per call")
    # Expected: <0.01ms
    
    # Random with filters (O(n) scan + weighted choice)
    time_random = timeit.timeit(
        lambda: factory.get_random_exam(modality="CT", setting="emergency"),
        number=1000
    )
    print(f"Random filtered: {time_random / 1000 * 1000:.3f}ms per call")
    # Expected: ~0.1-0.3ms for 200 exams
```

## Implementation Checklist

- [ ] Create `app/catalog/factory.py` with `ExamFactory` class
- [ ] Implement all public methods with docstrings
- [ ] Add custom exception classes
- [ ] Create `get_exam_factory()` singleton function
- [ ] Write unit tests for each selection method
- [ ] Add integration tests with real catalog
- [ ] Document template string formats
- [ ] Create example usage in docstrings

## Next Steps

See [EXAMGEN-3.0: Initial Catalog Population](EXAMGEN-3.0-Initial-Catalog-Population.md) for populating the catalog with real exam data.
