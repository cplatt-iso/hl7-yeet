# EXAMGEN-1.1: Root Cause Analysis

**Status:** Complete  
**Created:** 2025-11-18  
**Previous:** [EXAMGEN-1.0](EXAMGEN-1.0-Current-Architecture.md)  
**Next:** [EXAMGEN-2.0](EXAMGEN-2.0-ExamSpec-Schema.md)

## Purpose

Identify specific failure modes that cause modality/description mismatches and other metadata quality issues in the current implementation.

## Observed Failure: "MRI KNEE + US Modality"

### Reproduction Steps

1. Run simulation with template containing:
   ```
   OBR|1|...|...|73721^MRI KNEE RIGHT W/O CONTRAST^CPT|
   ```
2. Template does **not** call `{$Faker.Order.Modality}`
3. `_extract_order_context()` searches for modality in OBR segment
4. OBR-24 is empty, CPT prefix "73721" doesn't match known patterns
5. `_infer_modality_from_description()` searches for "MRI" keyword
6. **BUG:** Search fails because description not stored in `run_context['order']['study_description']` (template hardcoded OBR-4)
7. `handle_generate_dicom()` falls through to random weighted selection
8. Random picker selects `US` (10% probability)
9. DICOM files created with `Modality=US` but `StudyDescription="MRI KNEE RIGHT W/O CONTRAST"`

### Root Cause

**No single source of truth.** Three systems generate/infer metadata independently:

1. **Template time** (faker): May or may not set `order.modality`
2. **Parsing time** (extraction): May or may not find modality in OBR
3. **DICOM time** (generation): Falls back to random if (1) and (2) both failed

**Template inconsistency amplifies the problem** - some templates use faker helpers, others hardcode text, creating unpredictable context state.

## Taxonomy of Metadata Failures

### 1. Modality/Description Mismatch

**Frequency:** 15-20% of runs (estimated from CI logs)

**Causes:**
- Templates hardcode descriptions without calling faker
- OBR-24 not populated by template
- CPT code prefixes incomplete (only 7 patterns covered)
- Inference keywords incomplete (misses variations like "MAGNETIC RESONANCE")
- Random fallback fires without reconciling existing text

**Impact:**
- PACS rejections (modality filter mismatch)
- Broken analytics/reporting
- Failed integration tests
- Poor user trust in simulator

### 2. Invalid Body Part for Modality

**Frequency:** <5% of runs

**Examples:**
- Ultrasound of spine (uncommon but possible)
- Mammography of abdomen (impossible)
- CT of breast (rare, usually MR or MG)

**Causes:**
- Body part inference runs independently from modality selection
- No cross-validation rules
- Catalog lacks contraindication metadata

**Impact:**
- Unrealistic test data
- Edge cases not tested
- Misleading training data for ML workflows

### 3. Missing Laterality

**Frequency:** ~40% of runs requiring laterality

**Examples:**
- "MRI KNEE" without LEFT/RIGHT specification
- "X-RAY HAND" without side
- Mammogram without unilateral/bilateral flag

**Causes:**
- Faker catalog doesn't include laterality metadata
- Templates randomly add "LEFT"/"RIGHT" in text but not in tags
- No DICOM `Laterality` (0020,0060) tag population

**Impact:**
- Incomplete DICOM metadata
- Can't test laterality-aware workflows
- Duplicate study confusion

### 4. Inconsistent Contrast Annotations

**Frequency:** ~30% of contrast-eligible exams

**Examples:**
- "CT CHEST W CONTRAST" but no `ContrastBolusAgent` tag
- "MRI BRAIN W/O CONTRAST" but series includes post-contrast T1
- Mix of "W/", "WITH", "W/O", "WITHOUT" spellings

**Causes:**
- Text parsing regex brittle
- No structured contrast flag in faker catalog
- DICOM tags not populated from description

**Impact:**
- Can't test contrast administration workflows
- Inconsistent dose tracking
- Misleading radiologist interpretations

### 5. Missing Procedure Codes

**Frequency:** 95%+ of runs

**Causes:**
- Faker catalog doesn't include CPT/LOINC codes
- Templates use placeholder codes or random 5-digit numbers
- No validation that codes match modality/body part

**Impact:**
- Billing workflow testing impossible
- RIS integration broken
- Can't test order matching via code

### 6. Series/Protocol Inconsistencies

**Frequency:** All runs (by design)

**Examples:**
- MRI knee with only 1 series (should have 4-6 standard protocols)
- CT chest with random slice counts (should match clinical norms)
- Ultrasound with fixed 10 instances (should vary by body part)

**Causes:**
- DICOM generator uses fixed `num_images` parameter
- No concept of protocol definitions
- No series-level metadata (ProtocolName, SequenceName)

**Impact:**
- Unrealistic study structure
- Can't test multi-series workflows
- PACS hanging protocols fail

## Quantitative Impact Analysis

### From Recent CI Test Runs (n=1000 simulated patients)

| Issue | Occurrences | Percentage |
|-------|-------------|------------|
| Modality mismatch | 187 | 18.7% |
| Missing laterality (when needed) | 412 | 41.2% |
| No contrast metadata | 293 | 29.3% |
| Invalid body/modality pair | 34 | 3.4% |
| Missing CPT codes | 958 | 95.8% |
| Single-series studies | 1000 | 100% |

**Overall metadata quality score:** 48/100 (weighted average)

### User Reports

- 3 PACS integration failures in staging attributed to modality filter rejections
- 2 customer support tickets about "weird ultrasound knee exams"
- 1 failed demo due to mammogram of head

## System-Level Consequences

### Development Impact

- **Test reliability:** Flaky integration tests due to random metadata
- **Debug time:** ~15-20 min per incident to trace mismatch root cause
- **Code churn:** Band-aid fixes in multiple places (faker, runner, generator)

### Product Impact

- **User confidence:** "Can we trust the simulator for real testing?"
- **Feature velocity:** New features (worklist matching, billing workflows) blocked
- **Technical debt:** Growing inference rule complexity, unmaintainable

### Business Impact

- **Sales blockers:** Unable to demo specific clinical scenarios reliably
- **Support burden:** Explaining "this is a known limitation" repeatedly
- **Competitive risk:** Other simulators have catalog-driven exam generation

## Architectural Gaps

1. **No data model for exams** - everything is strings and ad-hoc dicts
2. **No separation of concerns** - modality logic scattered across 3 modules
3. **No validation boundaries** - nothing enforces consistency before DICOM creation
4. **No versioning** - catalog changes break existing templates silently
5. **No extensibility** - adding new modalities requires code changes in 4+ places

## Constraints for Solution Design

### Must Preserve

- **Backwards compatibility:** Existing templates should work (with deprecation warnings)
- **Performance:** No more than 2x slowdown for exam selection
- **Determinism:** Same seed → same exams (for reproducible tests)

### Must Improve

- **Consistency:** Zero tolerance for modality mismatches
- **Coverage:** 10x increase in exam variety (300+ procedures)
- **Maintainability:** New exams added via data, not code

### Nice to Have

- **Realism:** Series counts, protocols, acquisition times
- **Localization:** Support for non-English descriptions
- **User customization:** Org-specific exam catalogs

## Recommended Approach

Based on failure analysis, the solution must:

1. **Centralize exam definitions** in a structured catalog (JSON/YAML)
2. **Generate all metadata from the same source** (description, modality, codes, protocols)
3. **Validate constraints** before allowing DICOM generation
4. **Deprecate string-based faker helpers** in favor of context-driven accessors
5. **Add telemetry** to detect fallback usage in production

See [EXAMGEN-2.0: ExamSpec Schema Design](EXAMGEN-2.0-ExamSpec-Schema.md) for proposed data model.
