"""Tests for ExamSpec-aware faker parser helpers."""

from __future__ import annotations

from typing import Any, Dict

from app.exam_spec import ExamSpec, Laterality, ProcedureCode, SeriesProtocol
from app.util import faker_parser


def build_minimal_exam(**overrides: Any) -> ExamSpec:
    base: Dict[str, Any] = {
        "id": "TEST-CT-HEAD",
        "modality": "CT",
        "name": "Test CT Head",
        "description": "CT HEAD W/O CONTRAST",
        "body_part": "HEAD",
        "laterality": Laterality.UNPAIRED,
        "procedure_codes": [
            ProcedureCode(  # type: ignore[call-arg]
                system="CPT",
                code="70450",
                display="CT head w/o",
            )
        ],
        "series": [
            SeriesProtocol(  # type: ignore[call-arg]
                protocol_name="HEAD_STD",
                series_description="HEAD STD",
                instances=30,
            )
        ],
        "estimated_duration_min": 5.0,
        "indication_template": "Head trauma",
    }
    base.update(overrides)
    return ExamSpec(**base)  # type: ignore[arg-type]


def test_exam_context_helpers_consume_exam_spec():
    exam = build_minimal_exam(
        description="MRI SHOULDER LEFT W/O CONTRAST",
        modality="MR",
        body_part="SHOULDER",
        laterality=Laterality.LEFT,
        procedure_codes=[
            ProcedureCode(  # type: ignore[call-arg]
                system="CPT",
                code="73221",
                display="MRI shoulder w/o",
            )
        ],
        indication_template="Chronic shoulder pain",
    )

    faker_parser.set_current_exam(exam)
    try:
        assert faker_parser.faker_modality() == "MR"
        assert faker_parser.faker_study_description() == "MRI SHOULDER LEFT W/O CONTRAST"
        assert faker_parser.faker_body_part() == "SHOULDER"
        assert faker_parser.faker_laterality() == Laterality.LEFT.value
        assert faker_parser.faker_procedure_code() == "73221"
        assert faker_parser.faker_indication() == "Chronic shoulder pain"
    finally:
        faker_parser.clear_exam_context()


def test_process_faker_string_prefers_exam_metadata():
    exam = build_minimal_exam(
        description="DX FOOT 3 VIEWS LEFT",
        modality="DX",
        body_part="FOOT",
        laterality=Laterality.LEFT,
    )
    context = {
        "patient": {"mrn": "12345", "last_name": "Doe", "first_name": "Jane"},
        "exam_spec": exam.dict(),
    }

    rendered = faker_parser.process_faker_string(
        "Study={$Faker.Order.StudyDescription}|Mod={$Faker.Order.Modality}",
        context,
    )

    assert "Study=DX FOOT 3 VIEWS LEFT" in rendered
    assert "Mod=DX" in rendered
    # Order context should now include the ExamSpec metadata for downstream steps.
    assert context["order"]["body_part"] == "FOOT"
    assert context["order"]["laterality"] == Laterality.LEFT.value
