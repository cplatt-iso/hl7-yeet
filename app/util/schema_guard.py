# --- START OF FILE app/util/schema_guard.py ---
"""Lightweight schema guards that backfill new columns on startup."""

from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db as _db  # type: ignore F401 (used for typing/IDE hints)

_SIM_STATS_ALTERS: Sequence[str] = (
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS dicom_throughput_sum_mbps DOUBLE PRECISION NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS dicom_throughput_min_mbps DOUBLE PRECISION
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS dicom_throughput_max_mbps DOUBLE PRECISION
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS dicom_throughput_count INTEGER NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS worker_job_duration_sum_ms DOUBLE PRECISION NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS worker_job_duration_min_ms DOUBLE PRECISION
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS worker_job_duration_max_ms DOUBLE PRECISION
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS wall_clock_seconds DOUBLE PRECISION
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS orders_per_second DOUBLE PRECISION
    """,
    """
    ALTER TABLE simulation_run_stats
    ADD COLUMN IF NOT EXISTS step_duration_summary JSONB NOT NULL DEFAULT '{}'::jsonb
    """,
)


def ensure_simulation_run_stats_schema() -> None:
    """Ensure new SimulationRunStats columns exist in legacy deployments."""

    engine = _db.engine

    # SQLite (used in tests) lacks ALTER TABLE ... ADD COLUMN IF NOT EXISTS and
    # the JSONB casts in the statements below, so we simply skip the guard in
    # that environment. The production deployments all run on PostgreSQL where
    # these statements are valid.
    if engine.dialect.name == "sqlite":
        logging.info("Schema guard skipped for SQLite engine")
        return

    with engine.begin() as conn:
        for statement in _SIM_STATS_ALTERS:
            sql = " ".join(line.strip() for line in statement.strip().splitlines())
            try:
                conn.execute(text(sql))
            except SQLAlchemyError as exc:  # pragma: no cover - depends on live DB state
                logging.error("Schema guard failed for statement '%s': %s", sql, exc)
                raise
    logging.info("Schema guard: simulation_run_stats columns verified")


# --- END OF FILE app/util/schema_guard.py ---
