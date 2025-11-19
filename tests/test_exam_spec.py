from typing import Any, Dict

import pytest
from pydantic import ValidationError

from app.exam_spec import (
    ContrastType,
    ExamSpec,
    Laterality,
    ProcedureCode,
    SeriesProtocol,
)



def build_minimal_exam(**overrides):
    base: Dict[str, Any] = dict(
        id="TEST-CT-HEAD",
        modality="CT",
        name="Test CT Head",
        description="CT HEAD W/O CONTRAST",
        body_part="HEAD",
        laterality=Laterality.UNPAIRED,
        procedure_codes=[
            ProcedureCode(  # type: ignore[call-arg]
                system="CPT",
                code="70450",
                display="CT head w/o",
            )
        ],
        series=[
            SeriesProtocol(  # type: ignore[call-arg]
                protocol_name="HEAD_STD",
                series_description="HEAD STD",
                instances=30,
            )
        ],
        estimated_duration_min=5.0,
    )
    base.update(overrides)
    return ExamSpec(**base)  # type: ignore[arg-type]


def test_exam_spec_accepts_valid_payload():
    exam = build_minimal_exam()
    assert exam.modality == "CT"
    assert exam.body_part == "HEAD"
    assert exam.series[0].instances == 30


def test_exam_spec_rejects_unknown_modality():
    with pytest.raises(ValueError, match="Unsupported modality"):
        build_minimal_exam(modality="ZZ")


def test_exam_spec_requires_series():
    with pytest.raises(ValidationError, match="at least 1 item"):
        build_minimal_exam(series=[])


def test_exam_spec_laterality_enforced():
    exam = build_minimal_exam(laterality=Laterality.RIGHT)
    assert exam.laterality == Laterality.RIGHT


def test_exam_spec_age_range_validation():
    with pytest.raises(ValueError, match="max_age must be >= min_age"):
        build_minimal_exam(min_age=10, max_age=5)


def test_exam_spec_requires_valid_settings():
    with pytest.raises(ValidationError, match="Input should be"):
        build_minimal_exam(setting=["space"])  # type: ignore[list-item]


def test_series_protocol_matrix_validation():
    with pytest.raises(ValueError, match="Matrix dimensions must be positive"):
        SeriesProtocol(  # type: ignore[call-arg]
            protocol_name="BAD",
            series_description="BAD",
            instances=1,
            matrix=(512, 0),
        )


def test_contrast_volume_validation():
    with pytest.raises(ValidationError, match="greater than 0"):
        build_minimal_exam(
            contrast=ContrastType.INTRAVENOUS,
            contrast_volume_ml=0,
        )
