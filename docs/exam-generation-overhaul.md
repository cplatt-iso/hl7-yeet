# Exam Generation Overhaul Plan

_Last updated: 2025-11-17_

## Motivation

Recent simulation runs highlighted inconsistent exam metadata—for example, an HL7 order describing **“MRI KNEE RIGHT W/O CONTRAST”** while the generated DICOM instances reported modality `US`. These mismatches confuse downstream systems, pollute analytics, and make validation impossible. This document captures the current data flow, shortcomings, and a concrete enhancement plan so we can track work outside of ad‑hoc chat logs.

## Current Pipeline (as of commit `c2d1654`)

1. **Template Faker cues (`app/util/faker_parser.py`)**
   - `{$Faker.Order.StudyDescription}` / `{$Faker.Order.Modality}` call `_generate_study_and_modality()` which returns ~30 hard-coded description+modality pairs.
   - When invoked, the helper stashes both values inside `run_context['order']` for later reuse.
   - Templates that hardcode text instead of calling these cues never populate the cache.

2. **HL7 Order parsing (`SimulationRunner._extract_order_context` in `app/util/simulation_runner.py`)**
   - Reads OBR-4 for the description and OBR-24 / CPT-style prefixes / ZDS AE Titles to guess the modality.
   - Falls back to `_infer_modality_from_description()` (keyword-based) if nothing explicit exists.

3. **DICOM creation (`SimulationRunner.handle_generate_dicom`)**
   - Picks a modality using priority: explicit step param → MWL → order context → description inference → **weighted random fallback**.
   - If the random branch fires, it may overwrite the description with a generic one, or worse, leave the user-supplied description untouched—leading to MRI text paired with US modality.

4. **Pixel + body-part synthesis (`app/util/dicom_generator.py`)**
   - Infers `BodyPartExamined` from the description using keyword lists, then draws modality-specific pixel data.
   - No knowledge of study intent (contrast, laterality, CPT/LOINC, series composition, etc.).

## Root Causes of Bad Metadata

- **No single source of truth.** Study descriptions, modality codes, and body parts are generated (or inferred) in three separate places.
- **Template inconsistencies.** ORM templates often hardcode descriptions and never call the faker helpers, so order context lacks modality info.
- **Random fallback logic.** When inference fails, `handle_generate_dicom` picks a modality at random; nothing reconciles it with existing text.
- **Limited vocabulary.** `_generate_study_and_modality()` ships with a tiny hand-built list, so there is no coverage for many real-world combinations.

## Proposed Improvements

### 1. ExamSpec Catalog & Factory
- Introduce a data-driven catalog (JSON or Python module) of `ExamSpec` objects containing modality, canonical description, body part, laterality, contrast flag, recommended protocol names, CPT/LOINC codes, etc.
- Provide a factory helper (e.g., `exam_factory.pick_exam(profile="outpatient")`) that:
  - Chooses an `ExamSpec` using realistic frequency weights per modality/body part.
  - Stores the full spec at `run_context['exam']`, including convenience mirrors in `run_context['order']`.
  - Exposes helper accessors for HL7 templates, MWL, and DICOM generation.

### 2. Template Integration & Linting
- Update HL7 generator templates to reference context keys like `{$Context.Exam.description}` and `{$Context.Exam.modality}` instead of hardcoded strings.
- Add a simple lint step (script or CI check) that flags templates containing modality keywords without referencing the context provider, preventing regressions.

### 3. Validation Guard Before DICOM Generation
- Implement a guard (can live in the new `app/util/schema_guard.py`) that verifies, before any DICOM files are produced:
  - `run_context['exam']` exists and has modality + description.
  - Description contains the modality keyword (e.g., “MRI …” for MR exams).
  - Body part ↔ modality pairing is allowed (e.g., ultrasound knee only emitted if the catalog explicitly supports it).
  - Patient demographic constraints (e.g., obstetric ultrasounds only for female patients) are satisfied.
- Failing the guard should either regenerate a compatible spec or stop the workflow with a clear log.

### 4. Richer Metadata Emission
- Use the `ExamSpec` to populate:
  - HL7 OBR/OBX codes, ZDS AE titles, and placer/filler order numbers.
  - DICOM tags such as `ProtocolName`, `SeriesDescription`, `PerformedProcedureStepDescription`, `ContrastBolusAgent`, `Laterality`, etc.
  - Worklist entries (Scheduled Procedure Step Sequence) so downstream modalities see coherent data.
- Drive image generation parameters (slice counts, orientations, acquisition times) from the spec’s `series` definitions for more realism.

### 5. Optional Local LLM Enhancement (Feature Flag)
- For higher-fidelity free text (indications, radiologist impressions), integrate a lightweight local model via `ollama`/`llama.cpp` (e.g., `phi3-mini`):
  - Prompt it with the structured `ExamSpec` and demographic context to produce narrative text while enforcing modality/body-part constraints.
  - Cache outputs per spec to keep latency low; fall back to deterministic templates if the model is unavailable.

### 6. Telemetry & Regression Tests
- Instrument the generator to log the chosen `ExamSpec` ID and whether any fallback logic fired.
- Add a unit test that spins up N synthetic exams and asserts `StudyDescription` contains the modality keyword 100% of the time; fail CI otherwise.

## Immediate Next Steps

1. Build the initial `ExamSpec` catalog using open vocabularies (RadLex Playbook, RSNA/LOINC mappings) and wire the factory into `simulation_runner` + `faker_parser`.
2. Refactor existing HL7 templates to consume the new context keys and add linting.
3. Remove the random modality fallback in `handle_generate_dicom`; rely exclusively on the spec.
4. Expand `dicom_generator.create_study_files()` to accept `ExamSpec` metadata for consistent tags and pixel generation.
5. (Optional) Prototype the local LLM enhancer behind a feature flag and measure latency/quality.

## Open Questions

- How many profiles do we need (e.g., outpatient MSK vs inpatient trauma vs cardiology) to cover common demos?
- Should we allow user-defined exam packs and merge them into the catalog at runtime?
- Do we need a lightweight UI for admins to tweak exam weights without redeploying code?

---
Use this document as the canonical reference for exam-generation improvements. Update it as decisions land or when implementation details change.
