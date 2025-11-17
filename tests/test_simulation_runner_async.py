from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

from app import models
from app.util.simulation_runner import SimulationRunner


class DummyAppContext:
    def __call__(self):
        class _Ctx:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Ctx()


def test_queue_async_order_job_success(monkeypatch):
    runner = SimulationRunner(run_id=42, app_context=DummyAppContext())
    runner._log_event = MagicMock()
    runner._emit_async_queue_event = MagicMock()
    runner.run_context = {
        "order": {"accession_number": "ACC123"},
        "patient": {"mrn": "999"},
    }
    runner._template_id = 7
    runner._template_name = "Async Template"
    remaining_step = cast(
        models.SimulationStep,
        SimpleNamespace(
            id=11,
            step_order=4,
            step_type="SEND_DICOM",
            parameters={"endpoint_id": 55, "label": "Send DICOM"},
        ),
    )
    runner._template_steps = [remaining_step]
    runner._patient_count = 3
    runner._rabbitmq_enabled = True

    publisher_mock = MagicMock()
    publisher_mock.publish_order_job.return_value = True
    publisher_mock.order_queue = "yeeter.simulation.orders"
    monkeypatch.setattr("app.util.simulation_runner.get_rabbitmq_publisher", lambda: publisher_mock)
    monkeypatch.setattr("app.crud.record_queue_publish_metric", lambda *args, **kwargs: None)

    step = cast(
        models.SimulationStep,
        SimpleNamespace(parameters={"queue_async": True, "queue_metadata": {"priority": "STAT"}}, step_order=3),
    )

    assert runner._queue_async_order_job(step, 1, 1, "HL7|MSG") is True
    publisher_mock.publish_order_job.assert_called_once()
    payload = publisher_mock.publish_order_job.call_args.args[0]
    assert payload["job_id"] == payload["job"]["job_id"]
    assert payload["job"]["run_id"] == 42
    assert payload["job"]["template_id"] == 7
    assert payload["job"]["patient_iteration"] == 1
    assert payload["job"]["total_patients"] == 3
    assert payload["hl7_message"] == "HL7|MSG"
    assert payload["queue"] == "yeeter.simulation.orders"
    assert payload["metadata"] == {"priority": "STAT"}
    assert payload["retry_policy"] == {
        "attempt": 1,
        "max_attempts": 3,
        "retry_delay_ms": 5000,
    }
    assert payload["run_context"]["patient"]["mrn"] == "999"
    assert payload["remaining_steps"] == [
        {
            "id": 11,
            "order": 4,
            "type": "SEND_DICOM",
            "parameters": {"endpoint_id": 55, "label": "Send DICOM"},
            "description": "Send DICOM",
        }
    ]
    runner._log_event.assert_called_once()
    runner._emit_async_queue_event.assert_called_once()
    assert runner._queued_jobs == 1


def test_queue_async_order_job_skipped_when_flag_missing(monkeypatch):
    runner = SimulationRunner(run_id=42, app_context=DummyAppContext())
    runner._log_event = MagicMock()
    monkeypatch.setattr("app.util.simulation_runner.get_rabbitmq_publisher", lambda: MagicMock())

    step = cast(models.SimulationStep, SimpleNamespace(parameters={}, step_order=1))
    assert runner._queue_async_order_job(step, 1, 1, "HL7|MSG") is False
    runner._log_event.assert_not_called()
