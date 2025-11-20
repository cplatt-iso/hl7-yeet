# EXAMGEN-5.0: Template Migration & Faker Refactor

**Status:** In Progress  
**Created:** 2025-01-18  
**Previous:** [EXAMGEN-4.0](EXAMGEN-4.0-SimulationRunner-Integration.md)  
**Next:** [EXAMGEN-6.0](EXAMGEN-6.0-Validation-Testing.md)

## Purpose

Migrate existing HL7 message templates from faker string format to ExamSpec-driven generation, and refactor `app/util/faker_parser.py` to remove hardcoded study/modality tuples.

## Progress Log

| Date | Update |
| ---- | ------ |
| 2025-11-19 | Added ExamSpec-aware context helpers in `faker_parser.py`, wired SimulationRunner to call them, and created `tests/test_faker_parser.py` to prove we no longer fall back to random study/modality pairs when an exam is available. |

## Current Template Inventory

### Active Templates (in `templates/`)

```bash
$ ls templates/
orm_radiology_template.txt
orm_cardiology_template.txt
adt_admit_template.txt
oru_lab_results_template.txt
```

### Example Current Format (`orm_radiology_template.txt`)

```
MSH|^~\&|{{FAKER:system_name}}|{{FAKER:hospital_name}}|PACS|RADIOLOGY|{{FAKER:timestamp}}||ORM^O01|{{FAKER:message_id}}|P|2.5
PID|1||{{FAKER:mrn}}^^^{{FAKER:hospital_id}}^MR||{{FAKER:last_name}}^{{FAKER:first_name}}^{{FAKER:middle_name}}||{{FAKER:dob}}|{{FAKER:sex}}||||||||||{{FAKER:ssn}}
ORC|NW|{{FAKER:accession_number}}|{{FAKER:accession_number}}|||||||{{FAKER:timestamp}}
OBR|1|{{FAKER:accession_number}}|{{FAKER:accession_number}}|{{FAKER:procedure_code}}^{{FAKER:study_description}}^CPT||NW|{{FAKER:timestamp}}|||||||{{FAKER:indication}}||||||||{{FAKER:modality}}||||^^^{{FAKER:timestamp}}||||
```

## Migration Strategy

### Option A: Deprecate Templates Entirely

**Rationale:** ExamSpec provides all metadata needed to construct HL7 messages programmatically.

**Approach:**
1. Remove all template files
2. Generate HL7 messages directly in `SimulationRunner._build_hl7_from_exam()`
3. Update UI to remove template selection field
4. Migration: Convert existing SimulationTemplates with `template` field to `exam_id` field

**Pros:**
- Eliminates template maintenance burden
- Ensures consistency (one code path)
- Easier to validate output

**Cons:**
- Loss of flexibility for custom message formats
- Users cannot easily customize HL7 structure

### Option B: Hybrid Approach (Recommended)

**Rationale:** Keep templates for advanced users, but default to ExamSpec generation.

**Approach:**
1. Add `use_exam_spec` boolean to SimulationStep model
2. If `True`, use `_build_hl7_from_exam()` (no template)
3. If `False`, use legacy template with ExamSpec-aware faker functions
4. Update templates to reference ExamSpec fields instead of random generation

**Pros:**
- Maintains flexibility
- Gradual migration path
- Advanced users can customize HL7 structure

**Cons:**
- More code paths to maintain
- Potential for inconsistency if templates not updated

**Decision:** Use Option B for Phase 1, evaluate removal after 2-3 months.

## Faker Parser Refactoring

### Current Implementation (DEPRECATED)

```python
# app/util/faker_parser.py
study_modality_pairs = [
    ("CT CHEST W/O CONTRAST", "CT"),
    ("MRI BRAIN W/ CONTRAST", "MR"),
    ("XRAY CHEST PA AND LATERAL", "DX"),
    # ... 27 more hardcoded tuples
]

_cached_study_description = None
_cached_modality = None

def _generate_study_and_modality():
    global _cached_study_description, _cached_modality
    if _cached_study_description is None:
        _cached_study_description, _cached_modality = random.choice(study_modality_pairs)
    return _cached_study_description, _cached_modality

def faker_study_description():
    desc, _ = _generate_study_and_modality()
    return desc

def faker_modality():
    _, mod = _generate_study_and_modality()
    return mod
```

### Refactored Implementation (ExamSpec-Aware)

```python
# app/util/faker_parser.py
from typing import Optional
from app.catalog.factory import get_exam_factory
from app.models.exam_spec import ExamSpec

# Global cache for current exam in template processing
_current_exam: Optional[ExamSpec] = None

def set_current_exam(exam: ExamSpec):
    """Set exam context for template processing"""
    global _current_exam
    _current_exam = exam

def get_current_exam() -> Optional[ExamSpec]:
    """Get current exam context"""
    return _current_exam

def clear_exam_context():
    """Clear exam cache (call after template processing)"""
    global _current_exam
    _current_exam = None

# Faker functions now read from ExamSpec
def faker_study_description() -> str:
    """Get study description from current ExamSpec"""
    if _current_exam:
        return _current_exam.description
    else:
        # Fallback for backwards compatibility (deprecated)
        logger.warning("No ExamSpec context - using random fallback")
        factory = get_exam_factory()
        exam = factory.get_random_exam()
        return exam.description

def faker_modality() -> str:
    """Get modality from current ExamSpec"""
    if _current_exam:
        return _current_exam.modality
    else:
        logger.warning("No ExamSpec context - using random fallback")
        factory = get_exam_factory()
        exam = factory.get_random_exam()
        return exam.modality

def faker_body_part() -> str:
    """Get body part from current ExamSpec"""
    if _current_exam:
        return _current_exam.body_part
    return "BODY"

def faker_laterality() -> str:
    """Get laterality from current ExamSpec"""
    if _current_exam:
        return _current_exam.laterality.value
    return ""

def faker_procedure_code() -> str:
    """Get CPT code from current ExamSpec"""
    if _current_exam and _current_exam.procedure_codes:
        return _current_exam.procedure_codes[0].code
    return "99999"

def faker_indication() -> str:
    """Get clinical indication from current ExamSpec"""
    from app.catalog.vocabulary import get_vocabulary
    if _current_exam:
        vocab = get_vocabulary()
        return vocab.generate_indication(_current_exam)
    return "Clinical indication not specified"
```

### Updated Template Format

```
MSH|^~\&|{{FAKER:system_name}}|{{FAKER:hospital_name}}|PACS|RADIOLOGY|{{FAKER:timestamp}}||ORM^O01|{{FAKER:message_id}}|P|2.5
PID|1||{{FAKER:mrn}}^^^{{FAKER:hospital_id}}^MR||{{FAKER:last_name}}^{{FAKER:first_name}}^{{FAKER:middle_name}}||{{FAKER:dob}}|{{FAKER:sex}}||||||||||{{FAKER:ssn}}
ORC|NW|{{FAKER:accession_number}}|{{FAKER:accession_number}}|||||||{{FAKER:timestamp}}
OBR|1|{{FAKER:accession_number}}|{{FAKER:accession_number}}|{{FAKER:procedure_code}}^{{FAKER:study_description}}^CPT||NW|{{FAKER:timestamp}}|||||||{{FAKER:indication}}||||||||{{FAKER:modality}}||||^^^{{FAKER:timestamp}}||||
ZDS|{{FAKER:body_part}}|{{FAKER:laterality}}|||
```

### Template Processing Flow

```python
# app/util/simulation_runner.py
def handle_generate_hl7(self, step_config, run_context):
    """Generate HL7 with ExamSpec context"""
    
    # Select exam
    exam = self._select_exam(step_config, run_context)
    
    # Check if using template or direct generation
    use_template = step_config.get('use_template', False)
    
    if use_template:
        # Legacy path: process template with ExamSpec context
        template_name = step_config['template']
        hl7_message = self._generate_from_template(
            template_name, 
            exam, 
            run_context
        )
    else:
        # New path: direct generation
        hl7_message = self._build_hl7_from_exam(
            exam, 
            run_context['patient'], 
            run_context['accession_number'],
            run_context.get('indication')
        )
    
    # Store exam in context
    run_context['exam'] = exam
    return hl7_message

def _generate_from_template(self, template_name: str, 
                              exam: ExamSpec, 
                              run_context: Dict) -> str:
    """Process HL7 template with ExamSpec context"""
    
    # Set exam context for faker functions
    faker_parser.set_current_exam(exam)
    
    try:
        # Load template
        template_path = f'templates/{template_name}'
        with open(template_path) as f:
            template = f.read()
        
        # Process faker placeholders
        hl7_message = faker_parser.process_faker_string(
            template,
            run_context['patient']
        )
        
        return hl7_message
    
    finally:
        # Clear exam context
        faker_parser.clear_exam_context()
```

## Database Schema Updates

### SimulationStep Model Changes

```python
# app/models.py
class SimulationStep(db.Model):
    __tablename__ = 'simulation_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('simulation_templates.id'))
    step_number = db.Column(db.Integer, nullable=False)
    step_type = db.Column(db.String(50), nullable=False)
    
    # DEPRECATED: Old template-based approach
    template_file = db.Column(db.String(255), nullable=True)
    
    # NEW: ExamSpec-based approach
    use_exam_spec = db.Column(db.Boolean, default=True)
    exam_id = db.Column(db.String(100), nullable=True)  # e.g., "MR-KNEE-RIGHT-WO"
    exam_selection_mode = db.Column(db.String(20), default='random')  # 'explicit', 'random', 'cpt'
    exam_filters = db.Column(db.JSON, nullable=True)  # {"modality": "CT", "setting": "emergency"}
    
    # Step configuration
    config = db.Column(db.JSON, nullable=True)
    wait_after = db.Column(db.Integer, default=0)
```

### Migration Script

```python
# migrations/migrate_simulation_templates.py
def migrate_templates_to_exam_spec():
    """Convert old template-based steps to ExamSpec format"""
    from app import db
    from app.models import SimulationStep
    
    # Find all steps using old template format
    legacy_steps = SimulationStep.query.filter(
        SimulationStep.template_file.isnot(None),
        SimulationStep.use_exam_spec.is_(False)
    ).all()
    
    for step in legacy_steps:
        logger.info(f"Migrating step {step.id}: {step.template_file}")
        
        # Infer exam selection based on template name
        if 'ct' in step.template_file.lower():
            step.exam_filters = {'modality': 'CT'}
        elif 'mr' in step.template_file.lower():
            step.exam_filters = {'modality': 'MR'}
        elif 'xray' in step.template_file.lower() or 'dx' in step.template_file.lower():
            step.exam_filters = {'modality': 'DX'}
        else:
            step.exam_filters = {}  # Random any modality
        
        step.use_exam_spec = True
        step.exam_selection_mode = 'random'
        
        db.session.add(step)
    
    db.session.commit()
    logger.info(f"Migrated {len(legacy_steps)} simulation steps")
```

## UI Updates

### Simulation Template Editor

**Old UI:**
```
┌─ Step Configuration ─────────────┐
│ Step Type: GENERATE_HL7          │
│ Template File: [dropdown]        │
│   - orm_radiology_template.txt   │
│   - orm_cardiology_template.txt  │
│ Wait After: [0] seconds          │
└──────────────────────────────────┘
```

**New UI:**
```
┌─ Step Configuration ──────────────────────┐
│ Step Type: GENERATE_HL7                   │
│                                            │
│ Exam Selection: ⦿ Random  ○ Specific      │
│                                            │
│ [If Random]                                │
│ Modality: [dropdown: All, CT, MR, DX...] │
│ Setting:  [dropdown: All, Outpatient...] │
│ Body Part: [optional]                     │
│                                            │
│ [If Specific]                              │
│ Exam ID: [autocomplete: MR-KNEE-RIGHT...] │
│                                            │
│ Wait After: [0] seconds                   │
└───────────────────────────────────────────┘
```

### Frontend Component Changes

```jsx
// src/components/SimulationTemplateEditor.jsx
function StepConfigurationForm({ step, onChange }) {
  const [selectionMode, setSelectionMode] = useState(step.exam_selection_mode || 'random');
  
  return (
    <div className="step-config">
      <label>Exam Selection:</label>
      <RadioGroup value={selectionMode} onChange={setSelectionMode}>
        <Radio value="random">Random (with filters)</Radio>
        <Radio value="explicit">Specific Exam</Radio>
        <Radio value="cpt">By CPT Code</Radio>
      </RadioGroup>
      
      {selectionMode === 'random' && (
        <RandomExamFilters 
          filters={step.exam_filters || {}}
          onChange={(filters) => onChange({...step, exam_filters: filters})}
        />
      )}
      
      {selectionMode === 'explicit' && (
        <ExamIdAutocomplete
          examId={step.exam_id}
          onChange={(examId) => onChange({...step, exam_id: examId})}
        />
      )}
      
      {selectionMode === 'cpt' && (
        <CptCodeInput
          cptCode={step.config?.cpt_code}
          onChange={(code) => onChange({
            ...step, 
            config: {...step.config, cpt_code: code}
          })}
        />
      )}
    </div>
  );
}
```

## Implementation Checklist

- [x] Refactor `faker_parser.py` to use ExamSpec context
- [x] Add `set_current_exam()`, `get_current_exam()`, `clear_exam_context()` functions
- [x] Update faker functions: `faker_study_description()`, `faker_modality()`, etc.
- [ ] Add `use_exam_spec` and `exam_id` fields to SimulationStep model
- [ ] Create database migration script
- [ ] Update `handle_generate_hl7()` to support both paths
- [ ] Update existing HL7 templates with new faker placeholders
- [ ] Update frontend SimulationTemplateEditor component
- [ ] Add ExamIdAutocomplete component (calls `/api/exams/search`)
- [ ] Create API endpoint `/api/exams/search?q=knee` for autocomplete
- [ ] Run migration on existing templates: `python migrations/migrate_simulation_templates.py`
- [ ] Test legacy template path with ExamSpec context
- [ ] Test new direct generation path
- [ ] Update user documentation
- [ ] Remove deprecated `study_modality_pairs` array after 1 month

## Backwards Compatibility

### Deprecation Timeline

- **Week 1-2:** Deploy refactored code, both paths functional
- **Week 3-4:** Migrate all templates in database
- **Week 5-8:** Monitor usage, fix issues
- **Month 3:** Remove template files, mark old path as deprecated
- **Month 6:** Delete deprecated code entirely

### Deprecation Warnings

```python
def faker_study_description():
    if _current_exam:
        return _current_exam.description
    else:
        warnings.warn(
            "faker_study_description() called without ExamSpec context. "
            "This fallback behavior is deprecated and will be removed in v2.0. "
            "Use set_current_exam() before processing templates.",
            DeprecationWarning,
            stacklevel=2
        )
        # Fallback logic...
```

## Testing Strategy

### Unit Tests

```python
# tests/test_faker_parser.py
def test_faker_with_exam_context():
    from app.models.exam_spec import ExamSpec
    from app.util import faker_parser
    
    exam = ExamSpec(
        id="TEST-CT-HEAD",
        modality="CT",
        description="CT HEAD W/O CONTRAST",
        body_part="HEAD",
        # ... minimal fields
    )
    
    faker_parser.set_current_exam(exam)
    
    assert faker_parser.faker_modality() == "CT"
    assert faker_parser.faker_study_description() == "CT HEAD W/O CONTRAST"
    assert faker_parser.faker_body_part() == "HEAD"
    
    faker_parser.clear_exam_context()
```

### Integration Tests

```python
# tests/test_simulation_runner_migration.py
def test_template_with_exam_spec_context(client, test_user):
    """Verify legacy templates work with ExamSpec context"""
    template = create_test_template(
        steps=[
            {
                'step_type': 'GENERATE_HL7',
                'use_template': True,
                'template': 'orm_radiology_template.txt',
                'exam_filters': {'modality': 'MR'}
            }
        ]
    )
    
    # Run simulation
    run = start_simulation_run(template.id, patient_count=1)
    
    # Verify HL7 contains MR modality
    events = SimulationRunEvent.query.filter_by(run_id=run.id).all()
    hl7_event = next(e for e in events if 'ORM^O01' in e.event_data)
    assert 'OBR|' in hl7_event.event_data
    assert '|MR|' in hl7_event.event_data  # Modality field
```

## Next Steps

See [EXAMGEN-6.0: Validation & Testing](EXAMGEN-6.0-Validation-Testing.md) for comprehensive testing strategy.
