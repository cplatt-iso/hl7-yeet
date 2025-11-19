import json
import random
from pathlib import Path

import pytest

from app.catalog import CatalogLoadError, ExamCatalog, load_catalog
from app.catalog.validate import validate_catalog
from app.exam_spec import ExamSpec, Laterality, ProcedureCode, SeriesProtocol


def sample_exam(
	modality: str,
	body_part: str,
	exam_id: str,
	*,
	laterality: Laterality = Laterality.UNPAIRED,
	settings: list[str] | None = None,
	min_age: int | None = None,
	max_age: int | None = None,
	required_sex: str | None = None,
	cpt: str = "12345",
) -> ExamSpec:
	return ExamSpec(  # type: ignore[call-arg]
		id=exam_id,
		modality=modality,
		name=f"Sample {modality}",
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
		frequency_weight=2.0 if modality == "CT" else 1.0,
		setting=settings or ["outpatient"],
		min_age=min_age,
		max_age=max_age,
		required_sex=required_sex,
	)


def test_exam_catalog_builds_indexes():
	exams = [sample_exam("CT", "HEAD", "CT-HEAD"), sample_exam("MR", "KNEE", "MR-KNEE")]
	catalog = ExamCatalog(exams)

	ct_exam = catalog.get_by_id("CT-HEAD")
	assert ct_exam is not None
	assert ct_exam.modality == "CT"

	mr_exams = catalog.get_by_modality("MR")
	assert len(mr_exams) == 1

	head_exams = catalog.get_by_body_part("HEAD")
	assert head_exams and head_exams[0].id == "CT-HEAD"

	assert catalog.get_by_setting("outpatient")
	assert catalog.get_by_laterality(Laterality.UNPAIRED)
	assert catalog.get_by_cpt_code("12345") is not None

	rng = random.Random(42)
	assert catalog.get_random_exam(modality="CT", rng=rng).id == "CT-HEAD"


def test_load_catalog_from_json(tmp_path):
	payload = {
		"schema_version": "1.0",
		"catalog_version": "test",
		"metadata": {"total_exams": 1},
		"exams": [
			sample_exam("CT", "CHEST", "CT-CHEST").model_dump(),
		],
	}

	catalog_path = Path(tmp_path) / "catalog.json"
	catalog_path.write_text(json.dumps(payload), encoding="utf-8")

	catalog = load_catalog(catalog_path)
	assert catalog.metadata["total_exams"] == 1
	assert catalog.get_by_id("CT-CHEST") is not None


def test_load_catalog_rejects_bad_schema(tmp_path):
	payload = {"schema_version": "0.9", "exams": []}
	catalog_path = Path(tmp_path) / "catalog.json"
	catalog_path.write_text(json.dumps(payload), encoding="utf-8")

	with pytest.raises(CatalogLoadError):
		load_catalog(catalog_path)


def test_filter_exams_demographics():
	bl_exam = sample_exam(
		"MG",
		"BREAST",
		"MG-BREAST",
		laterality=Laterality.BILATERAL,
		settings=["screening"],
		min_age=40,
		max_age=75,
		required_sex="F",
	)
	ct_exam = sample_exam(
		"CT",
		"CHEST",
		"CT-CHEST",
		settings=["emergency"],
		min_age=0,
	)
	catalog = ExamCatalog([bl_exam, ct_exam])

	result = catalog.filter_exams(
		modality="MG",
		setting="screening",
		patient_age=55,
		patient_sex="F",
	)
	assert result == [bl_exam]

	assert not catalog.filter_exams(
		modality="MG",
		patient_age=30,
	)


def test_get_random_exam_applies_extra_filters():
	exam = sample_exam(
		"CT",
		"ABDOMEN",
		"CT-ABD",
		settings=["inpatient"],
		laterality=Laterality.UNPAIRED,
	)
	catalog = ExamCatalog([exam])

	selected = catalog.get_random_exam(
		modality="CT",
		setting="inpatient",
		patient_age=20,
	)
	assert selected.id == "CT-ABD"


def test_validate_catalog_detects_duplicates(tmp_path):
	record = sample_exam("CT", "CHEST", "CT-1").model_dump()
	payload = {
		"schema_version": "1.0",
		"catalog_version": "test",
		"metadata": {"total_exams": 1},
		"exams": [record, record],
	}
	path = Path(tmp_path) / "catalog.json"
	path.write_text(json.dumps(payload), encoding="utf-8")

	errors = validate_catalog(path)
	assert any("Duplicate exam ID" in err for err in errors)
	assert any("metadata.total_exams" in err for err in errors)


def test_validate_catalog_success(tmp_path):
	payload = {
		"schema_version": "1.0",
		"catalog_version": "test",
		"metadata": {"total_exams": 1},
		"exams": [sample_exam("MR", "BRAIN", "MR-BRAIN").model_dump()],
	}
	path = Path(tmp_path) / "catalog.json"
	path.write_text(json.dumps(payload), encoding="utf-8")

	assert validate_catalog(path) == []
