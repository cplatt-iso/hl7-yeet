from types import SimpleNamespace
from unittest.mock import MagicMock

from app.worker.consumer import WorkerConsumer


class DummyApp:
    class _Ctx:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    def app_context(self):  # noqa: D401 - simple stub
        return self._Ctx()


def test_handle_payload_success(monkeypatch):
    app = DummyApp()
    consumer = WorkerConsumer(
        app=app,
        amqp_url="amqp://guest:guest@localhost/",
        queue_name="test-queue",
    )

    run_record = SimpleNamespace(id=7, status="WAITING_ON_WORKERS", completed_at=None)

    def fake_get_run(db_obj, run_id):
        assert run_id == 7
        return run_record

    dummy_session = MagicMock()
    dummy_db = SimpleNamespace(session=dummy_session)

    monkeypatch.setattr("app.worker.consumer.crud.get_simulation_run_by_id", fake_get_run)
    monkeypatch.setattr("app.worker.consumer.db", dummy_db)

    socket_emits = []

    def fake_emit(event, payload, to=None):
        socket_emits.append((event, payload, to))

    monkeypatch.setattr("app.worker.consumer.socketio.emit", fake_emit)

    runner_calls = []

    class StubRunner:
        def __init__(self, run_id, app_context):
            self.run_id = run_id
            self.app_context = app_context
            self.run_context = {}
            self._template_id = None
            self._template_name = None
            self._patient_count = 0
            self._template_steps = []
            self._iteration_delegated = False
            self._queued_jobs = 0

        def handle_generate_dicom(self, step, patient_iter, repeat_iter):
            runner_calls.append(("generate_dicom", step.step_order, patient_iter, repeat_iter))
            return True

        def handle_send_dicom(self, step, patient_iter, repeat_iter):
            runner_calls.append(("send_dicom", step.step_order, patient_iter, repeat_iter))
            return True

        def _log_event(self, step_order, patient_iter, repeat_iter, level, details):
            runner_calls.append(("log", step_order, level, details))

    monkeypatch.setattr("app.worker.consumer.SimulationRunner", StubRunner)

    payload = {
        "job_id": "job-123",
        "job": {
            "run_id": 7,
            "template_id": 3,
            "patient_iteration": 2,
            "repeat_iteration": 1,
            "total_patients": 5,
        },
        "run_context": {"order": {"accession_number": "ACC1"}},
        "remaining_steps": [
            {"id": 11, "order": 4, "type": "GENERATE_DICOM", "parameters": {"count": 4}},
            {"id": 12, "order": 5, "type": "SEND_DICOM", "parameters": {"endpoint_id": 9}},
        ],
    }

    assert consumer._handle_payload(payload) is True

    assert run_record.status == "COMPLETED"
    assert run_record.completed_at is not None
    dummy_session.commit.assert_called_once()

    assert socket_emits == [("sim_run_status_update", {"run_id": 7, "status": "COMPLETED"}, "run-7")]

    assert any(call[0] == "generate_dicom" for call in runner_calls)
    assert any(call[0] == "send_dicom" for call in runner_calls)
    assert any(call[0] == "log" and "Worker completed job" in call[3] for call in runner_calls)


def test_handle_payload_failure(monkeypatch):
    app = DummyApp()
    consumer = WorkerConsumer(
        app=app,
        amqp_url="amqp://guest:guest@localhost/",
        queue_name="test-queue",
    )

    run_record = SimpleNamespace(id=8, status="WAITING_ON_WORKERS", completed_at=None)

    def fake_get_run(db_obj, run_id):
        assert run_id == 8
        return run_record

    dummy_session = MagicMock()
    dummy_db = SimpleNamespace(session=dummy_session)

    monkeypatch.setattr("app.worker.consumer.crud.get_simulation_run_by_id", fake_get_run)
    monkeypatch.setattr("app.worker.consumer.db", dummy_db)
    monkeypatch.setattr("app.worker.consumer.socketio.emit", MagicMock())

    class StubRunner:
        def __init__(self, run_id, app_context):
            self.run_context = {}

        def handle_generate_dicom(self, step, patient_iter, repeat_iter):
            return False

        def _log_event(self, *args, **kwargs):
            pass

    monkeypatch.setattr("app.worker.consumer.SimulationRunner", StubRunner)

    payload = {
        "job": {
            "run_id": 8,
            "patient_iteration": 1,
        },
        "remaining_steps": [
            {"order": 4, "type": "GENERATE_DICOM", "parameters": {}},
        ],
    }

    assert consumer._handle_payload(payload) is False
    assert run_record.status == "WAITING_ON_WORKERS"
    dummy_session.commit.assert_not_called()