# EXAMGEN-4.2: DICOM Generator Update & Realistic Pixel Data

**Status:** Not Started  
**Created:** 2025-11-18  
**Previous:** [EXAMGEN-4.0](EXAMGEN-4.0-SimulationRunner-Integration.md)  
**Next:** [EXAMGEN-5.0](EXAMGEN-5.0-Template-Migration.md)

## Purpose

Upgrade `app/util/dicom_generator.py` so that simulated DICOM studies contain richer, modality-aware pixel data and metadata, moving beyond "white noise" placeholders. This work ensures downstream PACS, AI, and QA workflows receive images that *look* and *behave* like real-world acquisitions while still remaining synthetic and non-diagnostic.

## Current Limitations

| Area | Problem |
|------|---------|
| Pixel Texture | Uniform random noise with no anatomical structure |
| Dynamic Range | Same 12-bit range regardless of modality or sequence |
| Slice Geometry | Identical spacing/orientation for every exam |
| Metadata Coupling | Pixel pipeline unaware of ExamSpec series parameters |
| Performance | Single-threaded Python loops cause slow generation for large MR/CT studies |

## Design Goals

1. **Anatomy Hints:** Use ExamSpec metadata (body part, laterality, sequence name) to drive phantom selection
2. **Modality Fidelity:** Model modality-specific intensity distributions, noise, artifacts, and slice geometry
3. **Parameterization:** Each `SeriesProtocol` controls acquisition parameters (matrix, slice thickness, TE/TR, view)
4. **Layered Rendering:** Build images via procedural layers (anatomy mask → signal model → noise/artifacts → post-processing)
5. **Performance:** <500 ms per CT/MR series (≤32 slices) on commodity CPU
6. **Extensibility:** Add new phantoms or artifact generators without refactoring call sites

## Architecture Overview

```
ExamSpec.SeriesProtocol
        │
        ▼
SeriesConfigBuilder (derives resolution, orientation, metadata)
        │
        ▼
PixelPipeline (per modality)
    ├── AnatomyGenerator (phantom templates)
    ├── SignalModel (intensity + gradients)
    ├── NoiseGenerator (Poisson/Gaussian/Rician)
    ├── ArtifactComposer (motion, streaks, coil shading)
    └── PostProcessor (window/level, contrast, filtering)
        │
        ▼
Numpy array → assigned to `ds.PixelData`
```

### Key Components

| Component | Responsibility |
|-----------|----------------|
| `SeriesConfigBuilder` | Converts ExamSpec metadata into matrix size, pixel spacing, slice positions |
| `AnatomyGenerator` | Produces coarse anatomical masks from parameterized templates (head, chest, abdomen, extremity, breast, pelvis) |
| `SignalModel` | Applies modality-specific HU/T1/T2/Proton Density curves to anatomy masks |
| `NoiseGenerator` | Adds realistic noise distributions (Poisson for CT, Rician for MR, speckle for US, quantum mottle for DX/MG) |
| `ArtifactComposer` | Optional effects: respiratory motion, metal streaks, coil shading, truncated FOV |
| `PixelRenderer` | Composes layers into final numpy array with appropriate bit depth |

## Modality-Specific Pipelines

### CT
- **Matrix:** 512×512 default, customizable per protocol
- **Anatomy Templates:** Head, chest, abdomen, pelvis, extremity
- **Signal Model:** Map anatomy mask to HU ranges (brain: 30 HU, bone: 1000 HU, lung: -700 HU)
- **Artifacts:** Beam hardening (polynomial HU modulation), motion blur (convolution), streaks (Radon domain manipulations)
- **Noise:** Poisson noise scaled by mAs (simulate dose changes)
- **Slice Geometry:** Derived from `series_protocol.instances`, `slice_thickness`, `spacing_between_slices`

### MRI
- **Matrix:** 256×256 default, optional non-square (e.g., 320×256)
- **Sequence Profiles:** Use `sequence_name` (e.g., `t2_tse_fs_ax`) to select T1/T2 weighting, fat suppression, orientation
- **Signal Model:** Tissue dictionary (WM, GM, CSF, muscle, fat) with T1/T2/PD values; convert to intensity via Bloch approximation for TR/TE
- **Noise:** Rician noise; adjustable SNR per sequence
- **Artifacts:** Coil shading (low-frequency multiplicative field), motion ghosting (Fourier domain line corruption)
- **Multi-Planar:** Adjust orientation vectors based on `protocol_name` keywords (SAG, COR, AX)

### DX / CR
- **Matrix:** 2048×2048 (downsample if necessary)
- **Anatomy:** Use body part (CHEST, ABDOMEN, SPINE) to load silhouette masks
- **Noise:** Quantum mottle + detector readout noise
- **Artifacts:** Grid lines, exposure gradient, anti-scatter grid misalignment, truncated collimation marks
- **Views:** Map to projection geometry (PA, LAT, oblique) for annotation overlays in metadata

### US
- **Matrix:** 640×480
- **Signal Model:** Layered echogenicity regions (tissue, vessels, bone) with gradient along depth
- **Noise:** Multiplicative speckle via Rayleigh distribution + depth-dependent attenuation
- **Artifacts:** Shadowing, enhancement, reverberation lines
- **Dynamic Clips:** Optionally emit multi-frame cine loops (future)

### MG (Mammography)
- **Matrix:** 2560×3328
- **Anatomy:** Breast phantom with glandular/fatty mix ratio and skin line
- **Artifacts:** Compression paddle imprint, detector non-uniformity, stitching seams
- **Noise:** Quantum-limited; mimic low-dose high-resolution detectors

### NM / PET
- **Matrix:** 128×128 or 256×256
- **Signal Model:** Gaussian blobs for uptake regions (bone, myocardium)
- **Noise:** Poisson counts relative to administered activity
- **Artifacts:** Attenuation gradients, limited-angle sampling noise

## Data Sources & Phantoms

1. **Shepp–Logan & Modified Phantoms:** Base for head CT/MR
2. **XCAT Lite (open sections):** Use simplified anatomy coefficients
3. **Public LUTs:** DICOM Window/Level presets from DICOM PS3.3 C.11.2
4. **Open Datasets for Calibration:**
   - TCIA (for histogram statistics)
   - NIH ChestX-ray14 (distribution references)
   - FastMRI (noise envelopes)

All data remains synthetic; only statistical properties extracted.

## Implementation Plan

1. **Refactor Structure (1 week)**
   - Create `app/util/pixel_pipeline/` package with modular generators
   - Update `dicom_generator.create_study_from_exam_spec()` to call pipeline
2. **CT & MR Pipelines (1.5 weeks)**
   - Implement Shepp–Logan-based CT phantom + T1/T2 MRI phantom
   - Add tissue dictionaries & parameter mapping
3. **DX & US Pipelines (1 week)**
   - Develop silhouette-based X-ray renderer
   - Implement speckle/noise model for ultrasound
4. **MG & NM Add-ons (0.5 week)**
   - Specialized phantoms for mammography and nuclear medicine
5. **Performance Optimizations (0.5 week)**
   - Vectorize pipelines with NumPy broadcasting
   - Optional numba acceleration for expensive loops
6. **Configuration Hooks (0.5 week)**
   - Extend `SeriesProtocol` with optional `pixel_profile` overrides
   - Add CLI flags to adjust realism level (high/medium/low)

## API Additions

```python
class SeriesProtocol(BaseModel):
    matrix: Optional[tuple[int, int]] = Field(None, description="Rows, cols")
    slice_thickness_mm: Optional[float] = Field(None)
    spacing_between_slices_mm: Optional[float] = Field(None)
    pixel_profile: Optional[str] = Field(
        None, description="Override default renderer (e.g., 'ct_trauma', 'mr_brain_dwi')"
    )
    realism_level: Literal['low', 'medium', 'high'] = 'medium'
```

```python
# app/util/pixel_pipeline/__init__.py
class PixelPipeline:
    def render(self, exam: ExamSpec, series: SeriesProtocol, instance_number: int) -> np.ndarray:
        raise NotImplementedError

class CTPipeline(PixelPipeline): ...
class MRPipeline(PixelPipeline): ...
# etc.

PIPELINE_REGISTRY = {
    'CT': CTPipeline(),
    'MR': MRPipeline(),
    'DX': DXPipeline(),
    'US': USPipeline(),
    'MG': MGPipeline(),
    'NM': NMPipeline(),
}
```

## Testing & Validation

| Test | Description |
|------|-------------|
| Histogram Comparison | Assert HU/intensity histograms match reference percentiles per modality |
| Noise Profile | Compute SNR/CNR for phantom ROIs and compare to expected ranges |
| Artifact Toggles | Ensure enabling/disabling artifacts changes images deterministically |
| Performance Bench | Generate 100 CT slices < 500 ms on CI runner |
| PACS Compatibility | Validate via `pacs_validator.py` + external DICOM viewers |
| Golden Samples | Store PNG previews for spot-checking regressions |

## Configuration & Tuning

- **Global Settings:** `settings.yml` option `pixel_realism_level: low|medium|high`
- **Per-Series Overrides:** `SeriesProtocol.realism_level`
- **CLI Flags:** `yeeter simulate --pixel-realism high --artifact metal`
- **Random Seeds:** Deterministic generation by seeding numpy RNG per patient/study

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance regressions | Provide `realism_level=low` fast path using legacy renderer |
| QA fatigue (images too realistic) | Watermark overlays + metadata flag `ContentLabel = "SYNTHETIC"` |
| Overfitting to phantom shapes | Parameterize masks + inject random deformations |
| Legal/licensing concerns | Use only procedurally generated phantoms or public-domain references |

## Deliverables

- `app/util/pixel_pipeline/` package with modality-specific renderers
- Updated `dicom_generator.py` hooking into pipeline
- Configurable realism levels + artifact toggles
- Unit & integration tests validating histograms, SNR, performance
- Documentation (`README_pixel_pipeline.md`) with visual samples

## Acceptance Criteria

1. CT, MR, DX, US series produce visual patterns recognizable by modality-trained clinicians
2. Histogram + SNR tests pass with thresholds defined in EXAMGEN-6.0
3. Performance benchmarks meet SLA (<500 ms/series default)
4. Legacy "simple" renderer available behind feature flag for backward compatibility
5. All DICOM tags updated to reflect new geometry (PixelSpacing, SliceThickness, Orientation)

---

Once this work package is complete, proceed to [EXAMGEN-5.0: Template Migration](EXAMGEN-5.0-Template-Migration.md) to align HL7 templates with the enhanced imaging pipeline.
