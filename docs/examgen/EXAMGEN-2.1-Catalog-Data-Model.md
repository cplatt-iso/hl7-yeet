# EXAMGEN-2.1: Catalog Data Model & Storage

**Status:** In Progress  
**Created:** 2025-11-18  
**Previous:** [EXAMGEN-2.0](EXAMGEN-2.0-ExamSpec-Schema.md)  
**Next:** [EXAMGEN-2.2](EXAMGEN-2.2-Factory-API-Design.md)

## Purpose

Define how ExamSpec instances are organized, stored, loaded, and maintained as a centralized catalog with version control and extensibility.

## Storage Architecture

### File System Layout

```
app/catalog/
├── __init__.py                  # Catalog loader and registry
├── exams.json                   # Main exam catalog (all specs)
├── vocabulary/                  # External terminology mappings
│   ├── cpt_codes.json          # CPT → ExamSpec mappings
│   ├── loinc_codes.json        # LOINC → ExamSpec mappings
│   ├── radlex_mappings.json    # RadLex RID → body part mappings
│   └── icd10_indications.json  # ICD-10 → indication templates
├── modality_groups/            # Organized by modality (optional)
│   ├── ct.json
│   ├── mr.json
│   ├── dx.json
│   └── us.json
└── custom/                      # Organization-specific overrides
    └── hospital_protocols.json
```

### Consolidated vs. Modular Storage

**Option A: Single File (`exams.json`)**
- Pro: Atomic updates, simple versioning
- Pro: Easy to search/filter in one pass
- Con: Large file size (~500KB for 200+ exams)
- Con: Merge conflicts in multi-contributor environments

**Option B: Modality-Specific Files**
- Pro: Parallel editing, smaller diffs
- Pro: Cleaner organization for large catalogs
- Con: Cross-modality queries require multiple reads
- Con: Duplication risk (e.g., CT/MR spine exams)

**Recommendation:** Start with single file, add modality split if catalog exceeds 300 exams.

## Catalog Schema

### Top-Level Structure

```json
{
  "schema_version": "1.0",
  "catalog_version": "2025.1",
  "last_updated": "2025-01-15T10:30:00Z",
  "metadata": {
    "total_exams": 187,
    "modalities": ["CT", "MR", "DX", "US", "NM", "MG"],
    "maintainer": "HL7 Yeeter Project",
    "license": "MIT"
  },
  "exams": [
    { /* ExamSpec 1 */ },
    { /* ExamSpec 2 */ },
    ...
  ]
}
```

### Index Structures (In-Memory)

```python
from typing import Dict, List, Set
from app.models.exam_spec import ExamSpec

class ExamCatalog:
    """Runtime catalog with optimized lookups"""
    
    def __init__(self):
        # Primary storage
        self._exams: List[ExamSpec] = []
        
        # Indexes for fast queries
        self._by_id: Dict[str, ExamSpec] = {}
        self._by_modality: Dict[str, List[ExamSpec]] = {}
        self._by_body_part: Dict[str, List[ExamSpec]] = {}
        self._by_laterality: Dict[str, List[ExamSpec]] = {}
        self._by_cpt_code: Dict[str, ExamSpec] = {}
        self._by_setting: Dict[str, List[ExamSpec]] = {}
        
        # Weighted selection pool (for random sampling)
        self._weighted_pool: List[tuple[ExamSpec, float]] = []
        
    def load_from_file(self, path: str):
        """Parse JSON catalog and build indexes"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        for exam_dict in data['exams']:
            exam = ExamSpec(**exam_dict)
            self._exams.append(exam)
            
            # Build indexes
            self._by_id[exam.id] = exam
            self._by_modality.setdefault(exam.modality, []).append(exam)
            self._by_body_part.setdefault(exam.body_part, []).append(exam)
            self._by_laterality.setdefault(exam.laterality.value, []).append(exam)
            self._by_setting.setdefault(exam.setting[0], []).append(exam)
            
            for code in exam.procedure_codes:
                if code.system == "CPT":
                    self._by_cpt_code[code.code] = exam
            
            # Build weighted pool
            self._weighted_pool.append((exam, exam.frequency_weight))
    
    def get_by_id(self, exam_id: str) -> Optional[ExamSpec]:
        return self._by_id.get(exam_id)
    
    def get_by_modality(self, modality: str) -> List[ExamSpec]:
        return self._by_modality.get(modality, [])
    
    def get_random_exam(self, modality: Optional[str] = None, 
                        body_part: Optional[str] = None,
                        setting: Optional[str] = None) -> ExamSpec:
        """Select exam using frequency weights and filters"""
        candidates = self._exams
        
        if modality:
            candidates = [e for e in candidates if e.modality == modality]
        if body_part:
            candidates = [e for e in candidates if e.body_part == body_part]
        if setting:
            candidates = [e for e in candidates if setting in e.setting]
        
        if not candidates:
            raise ValueError("No exams match filters")
        
        # Weighted random selection
        weights = [e.frequency_weight for e in candidates]
        return random.choices(candidates, weights=weights)[0]
```

## Query API

### Common Use Cases

```python
# 1. Template-based selection (from simulation step)
exam = catalog.get_by_id("MR-BRAIN-WO")

# 2. Random exam with constraints
exam = catalog.get_random_exam(modality="CT", setting="emergency")

# 3. Modality-specific list (for UI dropdowns)
ct_exams = catalog.get_by_modality("CT")

# 4. CPT code lookup (from RIS integration)
exam = catalog.get_by_cpt_code("70450")

# 5. Filter by demographic constraints
exam = catalog.find_matching(
    patient_age=42, 
    patient_sex="F", 
    modality="MR"
)
```

### Filter Chaining

```python
class ExamCatalog:
    def filter(self, **kwargs) -> 'ExamCatalog':
        """Return new catalog with filtered exams"""
        filtered = ExamCatalog()
        filtered._exams = [
            e for e in self._exams 
            if self._matches(e, **kwargs)
        ]
        filtered._rebuild_indexes()
        return filtered
    
    def _matches(self, exam: ExamSpec, **criteria) -> bool:
        if 'modality' in criteria and exam.modality != criteria['modality']:
            return False
        if 'min_weight' in criteria and exam.frequency_weight < criteria['min_weight']:
            return False
        if 'laterality' in criteria and exam.laterality != criteria['laterality']:
            return False
        return True

# Usage
urgent_ct_exams = catalog.filter(
    modality="CT", 
    setting="emergency", 
    min_weight=0.5
)
selected = urgent_ct_exams.get_random_exam()
```

## Catalog Maintenance

### Version Control Strategy

```bash
# Git LFS for large catalogs (if >10MB)
git lfs track "app/catalog/*.json"

# Commit hooks for validation
.git/hooks/pre-commit:
#!/bin/bash
python -m app.catalog.validate app/catalog/exams.json
```

### Validation Tool

```python
# app/catalog/validate.py
def validate_catalog(path: str) -> List[str]:
    """Check for errors in catalog file"""
    errors = []
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Schema validation
    if data['schema_version'] != "1.0":
        errors.append("Unsupported schema version")
    
    # Load all exams
    seen_ids = set()
    for idx, exam_dict in enumerate(data['exams']):
        try:
            exam = ExamSpec(**exam_dict)
            
            # Check for duplicate IDs
            if exam.id in seen_ids:
                errors.append(f"Duplicate exam ID: {exam.id}")
            seen_ids.add(exam.id)
            
            # Check modality consistency
            if exam.modality not in exam.series[0].protocol_name:
                errors.append(f"{exam.id}: Modality mismatch in series")
            
        except ValidationError as e:
            errors.append(f"Exam {idx}: {str(e)}")
    
    return errors

if __name__ == "__main__":
    errors = validate_catalog("app/catalog/exams.json")
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print(f"✓ Catalog valid")
```

### Adding New Exams

```bash
# CLI tool for adding exams
$ python -m app.catalog.add_exam \
  --modality MR \
  --name "MRI Shoulder Left With Contrast" \
  --body-part SHOULDER \
  --laterality L \
  --contrast IV \
  --cpt-code 73222

# Interactive mode
$ python -m app.catalog.add_exam --interactive
Modality [CT/MR/DX/US/MG/NM]: MR
Body part: SHOULDER
Laterality [R/L/B/-]: L
Contrast [none/IV/oral]: IV
...
```

### Bulk Import from CSV

```python
# app/catalog/import_csv.py
def import_from_csv(csv_path: str, catalog_path: str):
    """Convert CSV of exam codes to ExamSpec entries"""
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        exams = []
        
        for row in reader:
            exam = ExamSpec(
                id=_generate_id(row),
                modality=row['Modality'],
                name=row['Exam Name'],
                description=row['Description'],
                body_part=row['Body Part'],
                laterality=Laterality(row.get('Laterality', '')),
                procedure_codes=[
                    ProcedureCode(
                        system="CPT",
                        code=row['CPT Code'],
                        display=row['CPT Description']
                    )
                ],
                series=_generate_default_series(row['Modality']),
                estimated_duration_min=float(row.get('Duration', 15))
            )
            exams.append(exam.dict())
    
    # Merge with existing catalog
    with open(catalog_path, 'r+') as f:
        catalog = json.load(f)
        catalog['exams'].extend(exams)
        catalog['metadata']['total_exams'] = len(catalog['exams'])
        catalog['last_updated'] = datetime.now().isoformat()
        f.seek(0)
        json.dump(catalog, f, indent=2)
        f.truncate()
```

## Singleton Pattern

```python
# app/catalog/__init__.py
_catalog_instance: Optional[ExamCatalog] = None

def get_catalog() -> ExamCatalog:
    """Lazy-loaded singleton"""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = ExamCatalog()
        catalog_path = os.path.join(
            os.path.dirname(__file__), 
            'exams.json'
        )
        _catalog_instance.load_from_file(catalog_path)
    return _catalog_instance

def reload_catalog():
    """Force reload (for testing or hot-swap)"""
    global _catalog_instance
    _catalog_instance = None
    return get_catalog()
```

## Performance Considerations

### Startup Time
- **Cold load:** ~50ms for 200 exams (JSON parse + index build)
- **Cached:** <1ms after first load (singleton pattern)

### Memory Footprint
- **200 ExamSpecs:** ~2-3MB in memory
- **Indexes:** +500KB overhead
- **Total:** <5MB (negligible for modern systems)

### Search Performance
- **By ID:** O(1) via dictionary lookup
- **By modality:** O(1) index lookup + filter
- **Weighted random:** O(n) but typically <100 candidates after filtering

## Implementation Checklist

- [x] Create `app/catalog/` directory structure (`ExamCatalog`, loader, singleton)
- [x] Implement `ExamCatalog` class with indexes (ID, modality, body part, laterality, setting, CPT, weighted random helper)
- [x] Write `validate_catalog()` function (`app/catalog/validate.py` + CLI `python -m app.catalog.validate`)
- [x] Add `get_catalog()` singleton in `app/catalog/__init__.py`
- [x] Create initial `exams.json` with representative CT/MR entries (seeded for tests; to be expanded in EXAMGEN-3.0)
- [x] Write unit tests for query API & validator (`tests/test_exam_catalog.py`)
- [ ] Document CSV import format
- [ ] Add pre-commit hook for validation
- [ ] Expand seed catalog to 20+ exams

## Current Implementation Snapshot (2025-11-18)

- `ExamCatalog` now exposes `get_by_setting`, `get_by_laterality`, `get_by_cpt_code`, and `filter_exams` helpers so SimulationRunner can request constrained exams before EXAMGEN-2.2’s factory work begins.
- `get_random_exam()` reuses the shared filter routine, supporting modality/body-part/setting/laterality plus demographic filters (`patient_age`, `patient_sex`).
- `app/catalog/validate.py` performs schema version checks, duplicate ID detection, metadata count verification, and full ExamSpec validation. It is covered by new pytest cases.
- `tests/test_exam_catalog.py` now contains deterministic fixtures for CT/MR/MG exams and exercises the new query/validation API surface.
- Remaining action items for this work package: flesh out CSV/import tooling, wire validation into pre-commit CI, and scale the catalog contents (tracked for EXAMGEN-3.0).

## Next Steps

See [EXAMGEN-2.2: Factory API Design](EXAMGEN-2.2-Factory-API-Design.md) for the public interface to exam selection logic.
