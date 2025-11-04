from types import SimpleNamespace
from unittest.mock import MagicMock, ANY

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
    runner.run_context = {
        "order": {"accession_number": "ACC123"},
        "patient": {"mrn": "999"},
    }
    runner._template_id = 7
    runner._template_name = "Async Template"
    runner._rabbitmq_enabled = True

    publisher_mock = MagicMock()
    publisher_mock.publish_order_job.return_value = True
    monkeypatch.setattr("app.util.simulation_runner.get_rabbitmq_publisher", lambda: publisher_mock)

    step = SimpleNamespace(parameters={"queue_async": True}, step_order=3)

    assert runner._queue_async_order_job(step, 1, 1, "HL7|MSG") is True
    publisher_mock.publish_order_job.assert_called_once()
    payload = publisher_mock.publish_order_job.call_args.args[0]
    assert payload["run_id"] == 42
    assert payload["template_id"] == 7
    assert payload["patient_iteration"] == 1
    assert payload["hl7_message"] == "HL7|MSG"
    runner._log_event.assert_called_with(3, 1, 1, 'INFO', ANY)


def test_queue_async_order_job_skipped_when_flag_missing(monkeypatch):
    runner = SimulationRunner(run_id=42, app_context=DummyAppContext())
    runner._log_event = MagicMock()
    monkeypatch.setattr("app.util.simulation_runner.get_rabbitmq_publisher", lambda: MagicMock())

    step = SimpleNamespace(parameters={}, step_order=1)
    assert runner._queue_async_order_job(step, 1, 1, "HL7|MSG") is False
    runner._log_event.assert_not_called()
