# --- START OF FILE app/catalog/__init__.py ---
"""ExamSpec catalog loading utilities."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from pydantic import ValidationError

from app.exam_spec import ExamSpec, Laterality

LOGGER = logging.getLogger(__name__)
CATALOG_SCHEMA_VERSION = "1.0"
CATALOG_FILENAME = "exams.json"
_DEFAULT_CATALOG_PATH = Path(__file__).with_name(CATALOG_FILENAME)


class CatalogLoadError(RuntimeError):
    """Raised when the catalog JSON cannot be parsed."""


class ExamCatalog:
    """In-memory catalog with useful indexes for ExamSpec lookups."""

    def __init__(self, exams: Sequence[ExamSpec], metadata: Optional[Dict] = None):
        self._exams: List[ExamSpec] = list(exams)
        self.metadata = metadata or {}
        self._index_by_id: Dict[str, ExamSpec] = {}
        self._index_by_modality: Dict[str, List[ExamSpec]] = {}
        self._index_by_body_part: Dict[str, List[ExamSpec]] = {}
        self._index_by_laterality: Dict[str, List[ExamSpec]] = {}
        self._index_by_setting: Dict[str, List[ExamSpec]] = {}
        self._index_by_cpt: Dict[str, ExamSpec] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        for exam in self._exams:
            self._index_by_id[exam.id] = exam
            self._index_by_modality.setdefault(exam.modality, []).append(exam)
            self._index_by_body_part.setdefault(exam.body_part, []).append(exam)
            self._index_by_laterality.setdefault(exam.laterality.value, []).append(exam)

            for setting in exam.setting:
                self._index_by_setting.setdefault(setting, []).append(exam)

            for code in exam.procedure_codes:
                if code.system == "CPT":
                    self._index_by_cpt.setdefault(code.code, exam)

    @property
    def exams(self) -> List[ExamSpec]:
        return list(self._exams)

    def get_by_id(self, exam_id: str) -> Optional[ExamSpec]:
        return self._index_by_id.get(exam_id)

    def get_by_modality(self, modality: str) -> List[ExamSpec]:
        return list(self._index_by_modality.get(modality.upper(), []))

    def get_by_body_part(self, body_part: str) -> List[ExamSpec]:
        return list(self._index_by_body_part.get(body_part.upper(), []))

    def get_by_setting(self, setting: str) -> List[ExamSpec]:
        return list(self._index_by_setting.get(setting, []))

    def get_by_laterality(self, laterality: Laterality | str) -> List[ExamSpec]:
        key = laterality.value if isinstance(laterality, Laterality) else laterality
        return list(self._index_by_laterality.get(key, []))

    def get_by_cpt_code(self, code: str) -> Optional[ExamSpec]:
        return self._index_by_cpt.get(code)

    def list_modalities(self) -> List[str]:
        return sorted(self._index_by_modality.keys())

    def filter_exams(
        self,
        *,
        modality: Optional[str] = None,
        body_part: Optional[str] = None,
        setting: Optional[str] = None,
        laterality: Optional[str] = None,
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
    ) -> List[ExamSpec]:
        """Return exams matching provided constraints."""

        def _matches(exam: ExamSpec) -> bool:
            if modality and exam.modality != modality.upper():
                return False
            if body_part and exam.body_part != body_part.upper():
                return False
            if setting and setting not in exam.setting:
                return False
            if laterality:
                laterality_key = laterality if isinstance(laterality, str) else laterality.value
                if exam.laterality.value and exam.laterality.value != laterality_key:
                    return False
            if patient_age is not None:
                if exam.min_age is not None and patient_age < exam.min_age:
                    return False
                if exam.max_age is not None and patient_age > exam.max_age:
                    return False
            if patient_sex and exam.required_sex and exam.required_sex != patient_sex.upper():
                return False
            return True

        return [exam for exam in self._exams if _matches(exam)]

    def get_random_exam(
        self,
        *,
        modality: Optional[str] = None,
        body_part: Optional[str] = None,
        setting: Optional[str] = None,
        laterality: Optional[str] = None,
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
        rng: Optional[random.Random] = None,
    ) -> ExamSpec:
        """Return a weighted random exam that matches filters."""

        rng = rng or random
        candidates = self.filter_exams(
            modality=modality,
            body_part=body_part,
            setting=setting,
            laterality=laterality,
            patient_age=patient_age,
            patient_sex=patient_sex,
        )
        if not candidates:
            raise ValueError("No exams match the requested filters")
        weights = [exam.frequency_weight for exam in candidates]
        return rng.choices(candidates, weights=weights, k=1)[0]


def load_catalog(path: Optional[Path] = None) -> ExamCatalog:
    """Load a catalog file from JSON into an ExamCatalog instance."""

    resolved = Path(path) if path else _DEFAULT_CATALOG_PATH
    if not resolved.exists():
        raise CatalogLoadError(f"Catalog file not found: {resolved}")

    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    schema_version = payload.get("schema_version")
    if schema_version != CATALOG_SCHEMA_VERSION:
        raise CatalogLoadError(
            f"Unsupported catalog schema version: {schema_version}"
        )

    raw_exams = payload.get("exams", [])
    exams: List[ExamSpec] = []
    for idx, entry in enumerate(raw_exams):
        try:
            exams.append(ExamSpec(**entry))
        except ValidationError as exc:
            raise CatalogLoadError(f"Exam entry {idx} invalid: {exc}") from exc

    metadata = payload.get("metadata", {})
    catalog = ExamCatalog(exams, metadata=metadata)
    LOGGER.info(
        "Loaded %s exam specs from %s (modalities=%s)",
        len(exams),
        resolved,
        catalog.list_modalities(),
    )
    return catalog


_catalog_instance: Optional[ExamCatalog] = None


def get_catalog(refresh: bool = False) -> ExamCatalog:
    """Return a cached ExamCatalog instance."""

    global _catalog_instance
    if _catalog_instance is None or refresh:
        _catalog_instance = load_catalog()
    return _catalog_instance


__all__ = [
    "CatalogLoadError",
    "ExamCatalog",
    "get_catalog",
    "load_catalog",
    "CATALOG_SCHEMA_VERSION",
    "CATALOG_FILENAME",
]

# --- END OF FILE app/catalog/__init__.py ---