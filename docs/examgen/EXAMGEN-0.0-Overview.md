# EXAMGEN-0.0: Exam Generation Feature Overview

**Status:** Planning  
**Created:** 2025-11-18  
**Owner:** TBD

## Executive Summary

The Exam Generation subsystem creates synthetic radiology orders and DICOM studies for simulation workflows. Current implementation produces inconsistent metadata (e.g., "MRI KNEE" orders paired with US modality DICOM files), making downstream validation impossible and polluting test data.

This feature track replaces the ad-hoc Faker string generation with a structured, catalog-driven approach that ensures consistency across HL7 messages, DICOM Modality Worklists, and generated DICOM instances.

## Goals

1. **Eliminate modality/description mismatches** by enforcing a single source of truth for each simulated exam.
2. **Expand exam variety** from ~30 hard-coded templates to hundreds of realistic procedure types using open medical vocabularies.
3. **Improve metadata fidelity** with proper CPT/LOINC codes, laterality, contrast flags, series protocols, and patient demographic constraints.
4. **Enable extensibility** via data-driven catalog files that can be updated without code changes.
5. **(Optional) Add LLM enhancement** for generating realistic clinical indications and radiologist impressions.

## Non-Goals

- Generating actual diagnostic-quality images (pixel data remains synthetic)
- Full RIS/PACS feature parity (focus is on simulation/testing use cases)
- Real-time modification of running simulations (catalog changes apply to new runs only)

## Success Metrics

- **Zero modality mismatches** in CI regression tests (10k+ generated exams)
- **>90% catalog coverage** of common outpatient and inpatient imaging procedures
- **<5% fallback rate** (percentage of exams that couldn't resolve from catalog)
- **<200ms p99 latency** for exam spec selection and metadata generation
- **100% HL7 template compliance** (no hardcoded modality strings without context references)

## Work Packages

| ID | Title | Status | Dependencies |
|----|-------|--------|--------------|
| [EXAMGEN-1.0](EXAMGEN-1.0-Current-Architecture.md) | Current Architecture Analysis | Complete | - |
| [EXAMGEN-1.1](EXAMGEN-1.1-Root-Cause-Analysis.md) | Root Cause Analysis | Complete | EXAMGEN-1.0 |
| [EXAMGEN-2.0](EXAMGEN-2.0-ExamSpec-Schema.md) | ExamSpec Schema Design | Complete | EXAMGEN-1.1 |
| [EXAMGEN-2.1](EXAMGEN-2.1-Catalog-Data-Model.md) | Catalog Data Model & Storage | In Progress | EXAMGEN-2.0 |
| [EXAMGEN-2.2](EXAMGEN-2.2-Factory-API.md) | Factory API Design | Complete | EXAMGEN-2.1 |
| [EXAMGEN-3.0](EXAMGEN-3.0-Catalog-Population.md) | Initial Catalog Population | Not Started | EXAMGEN-2.1 |
| [EXAMGEN-3.1](EXAMGEN-3.1-Vocabulary-Integration.md) | RadLex/LOINC Vocabulary Integration | Not Started | EXAMGEN-3.0 |
| [EXAMGEN-4.0](EXAMGEN-4.0-Runner-Integration.md) | SimulationRunner Integration | In Progress | EXAMGEN-2.2 |
| [EXAMGEN-4.1](EXAMGEN-4.1-Faker-Parser-Refactor.md) | Faker Parser Refactor | Not Started | EXAMGEN-4.0 |
| [EXAMGEN-4.2](EXAMGEN-4.2-DICOM-Generator-Update.md) | DICOM Generator Update | Not Started | EXAMGEN-4.0 |
| [EXAMGEN-5.0](EXAMGEN-5.0-Template-Migration.md) | HL7 Template Migration | In Progress | EXAMGEN-4.1 |
| [EXAMGEN-5.1](EXAMGEN-5.1-Template-Linting.md) | Template Linting & CI Checks | Not Started | EXAMGEN-5.0 |
| [EXAMGEN-6.0](EXAMGEN-6.0-Validation-Guard.md) | Pre-Generation Validation Guard | Not Started | EXAMGEN-4.2 |
| [EXAMGEN-7.0](EXAMGEN-7.0-Testing-Strategy.md) | Testing Strategy & Regression Suite | Not Started | EXAMGEN-6.0 |
| [EXAMGEN-8.0](EXAMGEN-8.0-Telemetry.md) | Telemetry & Observability | Not Started | EXAMGEN-7.0 |
| [EXAMGEN-9.0](EXAMGEN-9.0-LLM-Enhancement.md) | Optional LLM Enhancement (Feature Flag) | Not Started | EXAMGEN-8.0 |
| [EXAMGEN-10.0](EXAMGEN-10.0-Documentation.md) | User Documentation & Migration Guide | Not Started | EXAMGEN-9.0 |

## Timeline Estimate

- **Phase 1 (Schema & Catalog):** EXAMGEN-2.x, EXAMGEN-3.x → ~2-3 weeks
- **Phase 2 (Integration):** EXAMGEN-4.x, EXAMGEN-5.x → ~2-3 weeks
- **Phase 3 (Validation & Testing):** EXAMGEN-6.0, EXAMGEN-7.0, EXAMGEN-8.0 → ~1-2 weeks
- **Phase 4 (Polish & Docs):** EXAMGEN-9.0, EXAMGEN-10.0 → ~1 week

**Total:** 6-9 weeks for core feature, +1 week for optional LLM enhancement.

## Related Documents

- [Original RFC](../exam-generation-overhaul.md) - Initial conversation capture
- [Faker Parser Implementation](../../app/util/faker_parser.py)
- [SimulationRunner](../../app/util/simulation_runner.py)
- [DICOM Generator](../../app/util/dicom_generator.py)
