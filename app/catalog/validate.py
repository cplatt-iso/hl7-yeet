# --- START OF FILE app/catalog/validate.py ---
"""Utility helpers for validating exam catalog files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from app.catalog import CATALOG_FILENAME, CATALOG_SCHEMA_VERSION
from app.exam_spec import ExamSpec

_DEFAULT_PATH = Path(__file__).with_name(CATALOG_FILENAME)


def validate_catalog(path: Optional[Path] = None) -> List[str]:
    """Validate catalog JSON file and return a list of errors."""

    resolved = Path(path) if path else _DEFAULT_PATH
    errors: List[str] = []

    if not resolved.exists():
        return [f"Catalog file not found: {resolved}"]

    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]

    schema_version = payload.get("schema_version")
    if schema_version != CATALOG_SCHEMA_VERSION:
        errors.append(
            f"Unsupported schema_version={schema_version!r}; expected {CATALOG_SCHEMA_VERSION}"
        )

    exams = payload.get("exams", [])
    seen_ids: set[str] = set()
    for idx, entry in enumerate(exams):
        try:
            exam = ExamSpec(**entry)
        except ValidationError as exc:
            errors.append(f"Exam index {idx} invalid: {exc}")
            continue

        if exam.id in seen_ids:
            errors.append(f"Duplicate exam ID detected: {exam.id}")
        else:
            seen_ids.add(exam.id)

    metadata = payload.get("metadata", {})
    expected_count = metadata.get("total_exams")
    if expected_count is not None and expected_count != len(exams):
        errors.append(
            f"metadata.total_exams={expected_count} does not match actual count {len(exams)}"
        )

    return errors


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an EXAMGEN catalog file")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=_DEFAULT_PATH,
        help="Path to exams.json (defaults to bundled catalog)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    errors = validate_catalog(args.path)
    if errors:
        print("Catalog validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"✓ Catalog valid ({args.path})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

# --- END OF FILE app/catalog/validate.py ---
