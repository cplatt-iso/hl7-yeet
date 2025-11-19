# --- START OF FILE app/catalog/factory.py ---
"""Public factory interface for retrieving :class:`ExamSpec` objects."""

from __future__ import annotations

import logging
import random
from typing import Dict, Optional

from app.catalog import ExamCatalog, get_catalog
from app.exam_spec import ExamSpec, Laterality

LOGGER = logging.getLogger(__name__)


class ExamFactory:
    """Facade around :class:`ExamCatalog` with higher-level helpers."""

    def __init__(
        self,
        catalog: Optional[ExamCatalog] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._catalog = catalog or get_catalog()
        self._rng = rng or random.Random()

    def get_exam_by_id(self, exam_id: str) -> ExamSpec:
        exam = self._catalog.get_by_id(exam_id)
        if exam is None:
            raise ValueError(f"Exam ID '{exam_id}' not found in catalog")
        LOGGER.info("ExamFactory selected exam by ID: %s", exam_id)
        return exam

    def get_exam_by_cpt_code(self, cpt_code: str) -> ExamSpec:
        exam = self._catalog.get_by_cpt_code(cpt_code)
        if exam is None:
            raise ValueError(f"CPT code '{cpt_code}' not found in catalog")
        LOGGER.info("ExamFactory selected exam by CPT: %s -> %s", cpt_code, exam.id)
        return exam

    def get_exams_by_modality(self, modality: str) -> list[ExamSpec]:
        return sorted(self._catalog.get_by_modality(modality.upper()), key=lambda e: e.name)

    def get_available_modalities(self) -> list[str]:
        return self._catalog.list_modalities()

    def list_exams(
        self,
        *,
        modality: Optional[str] = None,
        body_part: Optional[str] = None,
        setting: Optional[str] = None,
        laterality: Optional[Laterality | str] = None,
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
    ) -> list[ExamSpec]:
        filters = any(
            value is not None
            for value in (modality, body_part, setting, laterality, patient_age, patient_sex)
        )
        if not filters:
            return self._catalog.exams
        return self._catalog.filter_exams(
            modality=modality,
            body_part=body_part,
            setting=setting,
            laterality=laterality,
            patient_age=patient_age,
            patient_sex=patient_sex,
        )

    def get_catalog_metadata(self) -> Dict[str, object]:
        return dict(self._catalog.metadata)

    def get_random_exam(
        self,
        *,
        modality: Optional[str] = None,
        body_part: Optional[str] = None,
        laterality: Optional[Laterality | str] = None,
        setting: Optional[str] = None,
        patient_age: Optional[int] = None,
        patient_sex: Optional[str] = None,
    ) -> ExamSpec:
        laterality_filter: Optional[str] = None
        if laterality:
            laterality_filter = laterality.value if isinstance(laterality, Laterality) else laterality
        exam = self._catalog.get_random_exam(
            modality=modality,
            body_part=body_part,
            setting=setting,
            laterality=laterality_filter,
            patient_age=patient_age,
            patient_sex=patient_sex,
            rng=self._rng,
        )
        LOGGER.info(
            "ExamFactory random selection -> %s (filters=%s)",
            exam.id,
            self._describe_filters(
                modality=modality,
                body_part=body_part,
                laterality=laterality_filter,
                setting=setting,
                patient_age=patient_age,
                patient_sex=patient_sex,
            ),
        )
        return exam

    def resolve_template_string(self, template: str, **context: object) -> ExamSpec:
        template = template.strip()
        if template.startswith("exam_id:"):
            return self.get_exam_by_id(template.split(":", 1)[1])
        if template.startswith("random"):
            modality = template.split(":", 1)[1] if ":" in template else None
            modality = modality or None
            return self.get_random_exam(
                modality=modality,
                patient_age=self._as_int(context.get("patient_age")),
                patient_sex=self._as_str(context.get("patient_sex")),
            )
        if template.startswith("cpt:"):
            return self.get_exam_by_cpt_code(template.split(":", 1)[1])
        LOGGER.warning("ExamFactory using legacy exam identifier: %s", template)
        return self.get_exam_by_id(template)

    @staticmethod
    def _describe_filters(**filters: Optional[str | int]) -> Dict[str, Optional[str | int]]:
        return {key: value for key, value in filters.items() if value is not None}

    @staticmethod
    def _as_int(value: object) -> Optional[int]:
        return value if isinstance(value, int) else None

    @staticmethod
    def _as_str(value: object) -> Optional[str]:
        return value if isinstance(value, str) else None


_factory_instance: Optional[ExamFactory] = None


def get_exam_factory() -> ExamFactory:
    """Return singleton :class:`ExamFactory`."""

    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ExamFactory()
    return _factory_instance


# --- END OF FILE app/catalog/factory.py ---
