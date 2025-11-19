import random

import pytest

from app.catalog import ExamCatalog
from app.catalog.factory import ExamFactory
from app.exam_spec import ContrastType, ExamSpec, Laterality, ProcedureCode, SeriesProtocol


def make_exam(
    exam_id: str,
    *,
    modality: str = "CT",
    body_part: str = "HEAD",
    laterality: Laterality = Laterality.UNPAIRED,
    settings: list[str] | None = None,
    frequency: float = 1.0,
    cpt: str = "70450",
    min_age: int | None = None,
    max_age: int | None = None,
    required_sex: str | None = None,
) -> ExamSpec:
    return ExamSpec(  # type: ignore[arg-type]
        id=exam_id,
        modality=modality,
        name=f"{modality} {body_part}",
        description=f"{modality} {body_part}",
        body_part=body_part,
        laterality=laterality,
        procedure_codes=[
            ProcedureCode(system="CPT", code=cpt, display="Sample"),
        ],
        series=[
            SeriesProtocol(  # type: ignore[call-arg]
                protocol_name="STD",
                series_description="STD",
                instances=5,
            )
        ],
        estimated_duration_min=10.0,
        contrast=ContrastType.NONE,
        frequency_weight=frequency,
        setting=settings or ["outpatient"],
        min_age=min_age,
        max_age=max_age,
        required_sex=required_sex,
    )


def make_factory(exams: list[ExamSpec]) -> ExamFactory:
    catalog = ExamCatalog(exams)
    rng = random.Random(1234)
    return ExamFactory(catalog=catalog, rng=rng)


def test_get_exam_by_id_success():
    factory = make_factory([make_exam("CT-HEAD"), make_exam("MR-KNEE", modality="MR")])
    exam = factory.get_exam_by_id("MR-KNEE")
    assert exam.modality == "MR"


def test_get_exam_by_id_missing():
    factory = make_factory([make_exam("CT-HEAD")])
    with pytest.raises(ValueError, match="not found"):
        factory.get_exam_by_id("MISSING")


def test_get_random_exam_filters_on_setting_and_age():
    ct_head = make_exam("CT-HEAD", settings=["emergency"], min_age=0, max_age=10)
    ct_body = make_exam("CT-BODY", settings=["outpatient"], min_age=20)
    factory = make_factory([ct_head, ct_body])
    exam = factory.get_random_exam(modality="CT", setting="emergency", patient_age=5)
    assert exam.id == "CT-HEAD"


def test_get_exam_by_cpt_code():
    exam = make_exam("CT-HEAD", cpt="12345")
    factory = make_factory([exam])
    assert factory.get_exam_by_cpt_code("12345").id == "CT-HEAD"
    with pytest.raises(ValueError):
        factory.get_exam_by_cpt_code("00000")


def test_get_exams_by_modality_sorted():
    exams = [
        make_exam("CT-B", modality="CT", body_part="B"),
        make_exam("CT-A", modality="CT", body_part="A"),
    ]
    factory = make_factory(exams)
    names = [exam.id for exam in factory.get_exams_by_modality("CT")]
    assert names == ["CT-A", "CT-B"]


def test_get_available_modalities():
    factory = make_factory([make_exam("CT-HEAD"), make_exam("MR-BRAIN", modality="MR")])
    assert factory.get_available_modalities() == ["CT", "MR"]


def test_resolve_template_string_variants():
    exams = [
        make_exam("CT-HEAD", modality="CT"),
        make_exam("MR-BRAIN", modality="MR"),
    ]
    factory = make_factory(exams)
    assert factory.resolve_template_string("exam_id:MR-BRAIN").id == "MR-BRAIN"
    assert factory.resolve_template_string("cpt:70450").id == "CT-HEAD"
    # random without modality falls back to any
    assert factory.resolve_template_string("random:").modality in {"CT", "MR"}
    # legacy path
    assert factory.resolve_template_string("CT-HEAD").id == "CT-HEAD"