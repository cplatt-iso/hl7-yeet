# --- START OF FILE app/exam_spec/__init__.py ---
"""Pydantic models describing structured radiology exam metadata.

These schemas back the EXAMGEN catalog, providing a single source of truth
for HL7, DMWL, and DICOM generation.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, validator

MODALITY_CODES = {
    "AR", "AS", "BD", "BI", "BL", "CD", "CF", "CP", "CR", "CS",
    "CT", "DD", "DG", "DM", "DS", "DX", "EC", "ES", "FA", "FC",
    "FD", "FS", "GM", "HC", "HD", "IO", "IR", "IV", "LS", "MA",
    "MG", "MR", "MS", "NM", "OT", "PT", "PX", "RF", "RG", "RT",
    "SC", "SM", "SR", "TG", "US", "XA",
}

SETTING_CHOICES = {"outpatient", "inpatient", "emergency", "screening"}


class Laterality(str, Enum):
    """DICOM laterality helper."""

    RIGHT = "R"
    LEFT = "L"
    BILATERAL = "B"
    UNILATERAL = "U"
    UNPAIRED = ""


class ContrastType(str, Enum):
    """Enumerates contrast administration modes."""

    NONE = "none"
    INTRAVENOUS = "intravenous"
    ORAL = "oral"
    RECTAL = "rectal"
    INTRATHECAL = "intrathecal"


class SeriesProtocol(BaseModel):
    """Defines how a single series within a study should appear."""

    protocol_name: str = Field(..., description="Scanner protocol identifier")
    series_description: str = Field(..., description="SeriesDescription tag")
    instances: int = Field(..., gt=0, description="Instance count in series")
    acquisition_duration_sec: Optional[float] = Field(
        None, gt=0, description="Approximate scan duration"
    )
    sequence_name: Optional[str] = Field(
        None, description="SequenceName / pulse sequence descriptor"
    )
    matrix: Optional[Tuple[int, int]] = Field(
        None, description="Pixel matrix (rows, cols)"
    )
    slice_thickness_mm: Optional[float] = Field(
        None, gt=0, description="Slice thickness metadata"
    )
    spacing_between_slices_mm: Optional[float] = Field(
        None, gt=0, description="Spacing between slices"
    )
    pixel_profile: Optional[str] = Field(
        None,
        description="Override for pixel rendering pipeline",
    )
    realism_level: Literal["low", "medium", "high"] = Field(
        "medium", description="Rendering fidelity hint"
    )

    @validator("matrix")
    def validate_matrix(cls, value: Optional[Tuple[int, int]]):
        if value is None:
            return value
        rows, cols = value
        if rows <= 0 or cols <= 0:
            raise ValueError("Matrix dimensions must be positive")
        return value


class ProcedureCode(BaseModel):
    """Standardized procedure identifiers (CPT/LOINC/etc)."""

    system: Literal["CPT", "LOINC", "SNOMED", "ICD10PCS", "CUSTOM"] = Field(
        "CPT", description="Coding scheme"
    )
    code: str = Field(..., min_length=1, description="Code value")
    display: str = Field(..., min_length=1, description="Human-readable text")


class ExamSpec(BaseModel):
    """Complete specification for a radiology exam workflow."""

    id: str = Field(..., min_length=3, description="Unique identifier")
    version: str = Field("1.0", description="Schema version for the entry")
    modality: str = Field(..., description="DICOM modality code")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="StudyDescription text")
    body_part: str = Field(..., description="BodyPartExamined")
    laterality: Laterality = Field(
        Laterality.UNPAIRED, description="Laterality requirement"
    )
    indication_template: Optional[str] = Field(
        None, description="Reusable clinical indication text"
    )
    contrast: ContrastType = Field(ContrastType.NONE)
    contrast_agent: Optional[str] = Field(None)
    contrast_volume_ml: Optional[float] = Field(None, gt=0)
    procedure_codes: List[ProcedureCode] = Field(
        ..., min_length=1, description="Standardized codes"
    )
    series: List[SeriesProtocol] = Field(
        ..., min_length=1, description="Series composing the study"
    )
    estimated_duration_min: float = Field(
        ..., gt=0, description="Total exam duration"
    )
    min_age: Optional[int] = Field(None, ge=0)
    max_age: Optional[int] = Field(None, ge=0)
    required_sex: Optional[Literal["M", "F"]] = Field(None)
    frequency_weight: float = Field(
        1.0, gt=0, description="Relative frequency for weighted sampling"
    )
    setting: List[Literal["outpatient", "inpatient", "emergency", "screening"]] = (
        Field(default_factory=lambda: ["outpatient"])
    )
    custom_metadata: Dict[str, str] = Field(default_factory=dict)

    @validator("modality")
    def validate_modality(cls, value: str) -> str:
        value = value.upper()
        if value not in MODALITY_CODES:
            raise ValueError(f"Unsupported modality '{value}'")
        return value

    @validator("body_part")
    def normalize_body_part(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("body_part may not be empty")
        return value

    @validator("setting")
    def validate_settings(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("At least one setting is required")
        invalid = [item for item in value if item not in SETTING_CHOICES]
        if invalid:
            raise ValueError(f"Invalid setting(s): {', '.join(invalid)}")
        return value

    @validator("max_age")
    def validate_age_range(cls, value: Optional[int], values):
        min_age = values.get("min_age")
        if value is not None and min_age is not None and value < min_age:
            raise ValueError("max_age must be >= min_age")
        return value

    @validator("procedure_codes", "series")
    def ensure_non_empty(cls, value: List) -> List:
        if not value:
            raise ValueError("List must contain at least one item")
        return value

    @validator("custom_metadata")
    def ensure_metadata_keys_are_strings(cls, value: Dict[str, str]) -> Dict[str, str]:
        for key in value.keys():
            if not isinstance(key, str):
                raise TypeError("custom_metadata keys must be strings")
        return value


__all__ = [
    "ContrastType",
    "ExamSpec",
    "Laterality",
    "ProcedureCode",
    "SeriesProtocol",
    "SETTING_CHOICES",
    "MODALITY_CODES",
]

# --- END OF FILE app/exam_spec/__init__.py ---
