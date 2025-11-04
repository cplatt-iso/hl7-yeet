from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import cast

from pytest import approx

from app import crud, models


def _make_event(step_order: int, iteration: int, status: str, timestamp: datetime, details: str) -> SimpleNamespace:
    return SimpleNamespace(
        step_order=step_order,
        iteration=iteration,
        status=status,
        timestamp=timestamp,
        details=details,
    )


def _make_run(events, started_at=None, completed_at=None, status="COMPLETED"):
    base_started = started_at or datetime(2025, 1, 1, 12, 0, 0)
    return SimpleNamespace(
        id=101,
        user_id=7,
        template_id=3,
        patient_count=2,
        status=status,
        started_at=base_started,
        completed_at=completed_at,
        events=list(events),
    )


def test_calculate_simulation_run_stats_counts_and_steps():
    started_at = datetime(2025, 1, 1, 12, 0, 0)
    completed_at = started_at + timedelta(seconds=12)
    events = [
        _make_event(1, 1, "INFO", started_at + timedelta(seconds=1), "iteration start"),
        _make_event(1, 1, "SUCCESS", started_at + timedelta(seconds=2), "step finished"),
        _make_event(2, 1, "FAILURE", started_at + timedelta(seconds=3), "socket timeout"),
        _make_event(2, 1, "WARN", started_at + timedelta(seconds=4), "retrying"),
        _make_event(2, 1, "DEBUG", started_at + timedelta(seconds=5), "payload bytes"),
    ]
    run = _make_run(events, started_at=started_at, completed_at=completed_at)

    stats = crud.calculate_simulation_run_stats(cast(models.SimulationRun, run))

    assert stats["run_id"] == 101
    assert stats["total_events"] == 5
    assert stats["success_events"] == 1
    assert stats["failure_events"] == 1
    assert stats["warning_events"] == 1
    assert stats["info_events"] == 1  # INFO + fallback for unknown statuses
    assert stats["debug_events"] == 1
    assert stats["duration_seconds"] == approx(12.0)
    assert stats["unique_steps"] == 2
    assert stats["max_iteration"] == 1
    assert "socket timeout" in (stats["last_failure"] or "")

    step_stats = {step["step_order"]: step for step in stats["steps"]}
    assert step_stats[1]["total_events"] == 2
    assert step_stats[1]["success_events"] == 1
    assert step_stats[1]["info_events"] == 1
    assert step_stats[2]["total_events"] == 3
    assert step_stats[2]["failure_events"] == 1
    assert step_stats[2]["warning_events"] == 1


def test_calculate_simulation_run_stats_when_no_events():
    run = _make_run(events=[], started_at=None, completed_at=None, status="PENDING")

    stats = crud.calculate_simulation_run_stats(cast(models.SimulationRun, run))

    assert stats["total_events"] == 0
    assert stats["duration_seconds"] is None
    assert stats["first_event_at"] is None
    assert stats["last_event_at"] is None
    assert stats["steps"] == []
    assert stats["last_failure"] is None


