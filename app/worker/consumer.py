"""RabbitMQ worker that consumes queued simulation jobs and finishes deferred steps."""
from __future__ import annotations

import json
import logging
import signal
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pika

from .. import crud, schemas
from ..extensions import db, socketio
from ..util.metrics import emit_metric
from ..util.rabbitmq_client import get_rabbitmq_publisher
from ..util.simulation_runner import SimulationRunner, STEP_HANDLERS, cleanup_sim_run_artifacts


class WorkerConsumer:
    def __init__(
        self,
        *,
        app,
        amqp_url: str,
        queue_name: str,
        prefetch_count: int = 1,
        requeue_on_error: bool = False,
    ) -> None:
        self.app = app
        self.app_context = app.app_context
        self.amqp_url = amqp_url
        self.queue_name = queue_name
        self.prefetch_count = max(prefetch_count, 1)
        self.requeue_on_error = requeue_on_error
        self._connection: pika.BlockingConnection | None = None
        self._channel: Any = None

    # --- connection management ---
    def start(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_stop_signal)
        signal.signal(signal.SIGINT, self._handle_stop_signal)
        logging.info("Worker connecting to RabbitMQ at %s", self._mask_url(self.amqp_url))

        parameters = pika.URLParameters(self.amqp_url)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()
        if not self._channel:
            raise RuntimeError("Failed to open RabbitMQ channel")
        self._channel.queue_declare(queue=self.queue_name, durable=True)
        self._channel.basic_qos(prefetch_count=self.prefetch_count)
        self._channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_message)
        logging.info("Worker consuming queue '%s'", self.queue_name)

        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            logging.info("Worker stopping after keyboard interrupt")
        finally:
            self._cleanup()

    def _handle_stop_signal(self, signum, frame):  # type: ignore[override]
        logging.info("Worker received signal %s; shutting down", signum)
        if self._channel and self._channel.is_open:
            self._channel.stop_consuming()

    def _cleanup(self) -> None:
        if self._channel and self._channel.is_open:
            try:
                self._channel.close()
            except Exception:  # pragma: no cover
                pass
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except Exception:  # pragma: no cover
                pass

    @staticmethod
    def _mask_url(url: str) -> str:
        if "@" not in url:
            return url
        scheme, rest = url.split("://", 1)
        host = rest.split("@", 1)[1]
        return f"{scheme}://***@{host}"

    # --- message handling ---
    def _on_message(self, channel, method, properties, body):  # type: ignore[override]
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            logging.error("Worker received non-JSON payload: %s", exc)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        result: dict[str, Any] | bool
        try:
            result = self._handle_payload(payload)
        except Exception as exc:  # pragma: no cover - unexpected error
            logging.exception("Worker failed to process job: %s", exc)
            result = {"success": False}

        success = False
        retrying = False
        if isinstance(result, dict):
            success = bool(result.get("success"))
            retrying = bool(result.get("retrying"))
        else:
            success = bool(result)

        if success or retrying:
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            if self.requeue_on_error:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                channel.basic_ack(delivery_tag=method.delivery_tag)

    def _handle_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_meta = payload.get("job", {})
        job_id = payload.get("job_id") or job_meta.get("job_id")
        run_id = job_meta.get("run_id")
        patient_iter = job_meta.get("patient_iteration", 1)
        repeat_iter = job_meta.get("repeat_iteration", 1)
        remaining_steps = payload.get("remaining_steps") or []
        process_started = time.perf_counter()
        steps_executed = 0
        template_id = job_meta.get("template_id")
        template_name = job_meta.get("template_name")
        queue_name = payload.get("queue") or self.queue_name

        retry_policy = payload.get("retry_policy") or {}

        def _coerce_int(value: Any, default: int, minimum: int) -> int:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                return default
            return parsed if parsed >= minimum else minimum

        attempt = _coerce_int(retry_policy.get("attempt"), default=1, minimum=1)
        max_attempts = _coerce_int(retry_policy.get("max_attempts"), default=1, minimum=1)
        retry_delay_ms = _coerce_int(retry_policy.get("retry_delay_ms"), default=0, minimum=0)

        def _finish(
            success: bool,
            outcome: str,
            *,
            error: str | None = None,
            retrying: bool = False,
            attempt_override: int | None = None,
            max_attempts_override: int | None = None,
        ) -> bool:
            duration_ms = (time.perf_counter() - process_started) * 1000
            outstanding_steps = max(len(remaining_steps) - steps_executed, 0)
            emit_metric(
                "worker_job_processed",
                run_id=run_id,
                template_id=template_id,
                template_name=template_name,
                job_id=job_id,
                queue=queue_name,
                duration_ms=duration_ms,
                success=success,
                outcome=outcome,
                error=error,
                remaining_steps=len(remaining_steps),
                steps_executed=steps_executed,
                patient_iteration=patient_iter,
                repeat_iteration=repeat_iter,
            )
            if run_id:
                with self.app_context():
                    metric = crud.record_worker_job_metric(
                        db,
                        run_id=run_id,
                        job_id=job_id,
                        queue=queue_name,
                        success=success,
                        outcome=outcome,
                        error=error,
                        duration_ms=duration_ms,
                        steps_executed=steps_executed,
                        remaining_steps=outstanding_steps,
                        patient_iteration=patient_iter,
                        repeat_iteration=repeat_iter,
                    )

                    stats_record = crud.get_run_stats_record(db, run_id, create_if_missing=True)
                    run = crud.get_simulation_run_by_id(db, run_id, with_events=False)

                    if run:
                        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
                        if success:
                            if run.status not in {"CANCELLED", "ERROR"}:
                                run.status = "COMPLETED"
                                if not run.completed_at:
                                    run.completed_at = now_naive
                                db.session.commit()
                                try:
                                    crud.update_run_timing_metrics(db, run_id)
                                except Exception:
                                    logging.exception("Failed to update timing metrics for run %s", run_id)
                                socketio.emit(
                                    "sim_run_status_update",
                                    {"run_id": run_id, "status": "COMPLETED"},
                                    to=f"run-{run_id}",
                                )
                        elif not retrying and run.status not in {"CANCELLED", "ERROR"}:
                            run.status = "ERROR"
                            run.completed_at = now_naive
                            db.session.commit()
                            try:
                                crud.update_run_timing_metrics(db, run_id)
                            except Exception:
                                logging.exception("Failed to update timing metrics for run %s", run_id)
                            socketio.emit(
                                "sim_run_status_update",
                                {"run_id": run_id, "status": "ERROR"},
                                to=f"run-{run_id}",
                            )

                    metrics_payload = None
                    if stats_record and run:
                        metrics_dict = crud.build_run_metrics_payload(
                            stats_record,
                            run=run,
                            user=getattr(run, "user", None),
                            template=getattr(run, "template", None),
                        )
                        metrics_payload = (
                            schemas.SimulationRunMetricsResponse
                            .model_validate(metrics_dict)
                            .model_dump(mode="json")
                        )

                    job_payload = (
                        schemas.WorkerJobMetricResponse
                        .model_validate(metric)
                        .model_dump(mode="json")
                    )

                    if attempt_override is not None:
                        job_payload["attempt"] = attempt_override
                    if max_attempts_override is not None:
                        job_payload["max_attempts"] = max_attempts_override
                    job_payload["retrying"] = retrying
                    if error:
                        job_payload.setdefault("error", error)

                    socketio.emit(
                        "simulation_async_job_completed",
                        {
                            "run_id": run_id,
                            "job": job_payload,
                            "metrics": metrics_payload,
                            "retrying": retrying,
                            "retry_attempt": attempt_override,
                            "retry_max_attempts": max_attempts_override,
                        },
                        to=f"run-{run_id}",
                    )
            return success

        try:
            if not run_id:
                logging.warning("Worker payload missing run_id; acking job %s", job_id)
                _finish(True, "skipped_missing_run", attempt_override=attempt, max_attempts_override=max_attempts)
                return {"success": True}

            with self.app_context():
                run = crud.get_simulation_run_by_id(db, run_id, with_events=False)
            if not run:
                logging.warning("Worker could not find SimulationRun %s; acking job %s", run_id, job_id)
                _finish(True, "skipped_run_absent", attempt_override=attempt, max_attempts_override=max_attempts)
                return {"success": True}

            runner = SimulationRunner(run_id=run_id, app_context=self.app_context)
            runner.run_context = payload.get("run_context", {})
            runner._template_id = job_meta.get("template_id")
            runner._template_name = job_meta.get("template_name")
            runner._patient_count = job_meta.get("total_patients", 1)
            runner._template_steps = []
            runner._iteration_delegated = False
            runner._queued_jobs = 0

            failure_outcome: str | None = None
            failure_error: str | None = None
            failure_step: SimpleNamespace | None = None

            for step_data in remaining_steps:
                step_obj = SimpleNamespace(
                    id=step_data.get("id"),
                    step_order=step_data.get("order", 0),
                    step_type=step_data.get("type"),
                    parameters=step_data.get("parameters", {}),
                )
                handler_name = STEP_HANDLERS.get(step_obj.step_type)
                if not handler_name:
                    runner._log_event(
                        step_obj.step_order,
                        patient_iter,
                        repeat_iter,
                        "WARN",
                        f"Worker skipping unsupported step type '{step_obj.step_type}'.",
                    )
                    continue

                handler = getattr(runner, handler_name)
                if not handler(step_obj, patient_iter, repeat_iter):
                    runner._log_event(
                        step_obj.step_order,
                        patient_iter,
                        repeat_iter,
                        "FAILURE",
                        f"Worker failed step '{step_obj.step_type}'.",
                    )
                    failure_outcome = "step_failure"
                    failure_error = f"step_failed:{step_obj.step_type}"
                    failure_step = step_obj
                    break
                steps_executed += 1

            if failure_outcome:
                retrying = False
                if attempt < max_attempts:
                    publisher = get_rabbitmq_publisher()
                    if publisher:
                        new_payload = dict(payload)
                        new_retry = dict(retry_policy)
                        new_retry["attempt"] = attempt + 1
                        new_payload["retry_policy"] = new_retry
                        new_job_meta = dict(new_payload.get("job", {}))
                        new_job_meta["retry_attempt"] = attempt + 1
                        new_payload["job"] = new_job_meta
                        retrying = publisher.publish_order_job(new_payload)
                        if retrying:
                            step_order = failure_step.step_order if failure_step else 0
                            runner._log_event(
                                step_order,
                                patient_iter,
                                repeat_iter,
                                "WARN",
                                f"Async job {job_id or 'unknown'} failed (attempt {attempt}/{max_attempts}); requeued for retry.",
                            )
                            if retry_delay_ms > 0:
                                time.sleep(retry_delay_ms / 1000.0)
                        else:
                            logging.error(
                                "Worker failed to republish async job %s for retry; max attempts may be exceeded.",
                                job_id,
                            )
                    else:
                        logging.warning(
                            "Retry requested for async job %s but RabbitMQ publisher is unavailable.",
                            job_id,
                        )

                if not retrying and attempt >= max_attempts:
                    step_order = failure_step.step_order if failure_step else 0
                    runner._log_event(
                        step_order,
                        patient_iter,
                        repeat_iter,
                        "FAILURE",
                        f"Async job {job_id or 'unknown'} exhausted {max_attempts} attempt(s); marking run as ERROR.",
                    )

                _finish(
                    False,
                    failure_outcome,
                    error=failure_error,
                    retrying=retrying,
                    attempt_override=attempt,
                    max_attempts_override=max_attempts,
                )
                if retrying:
                    return {"success": False, "retrying": True}
                return {"success": False}

            runner._log_event(
                999,
                patient_iter,
                repeat_iter,
                "SUCCESS",
                f"Worker completed job {job_id or 'unknown'}.",
            )
            cleanup_ok, cleanup_error = cleanup_sim_run_artifacts(run_id)
            if cleanup_ok:
                runner._log_event(
                    999,
                    patient_iter,
                    repeat_iter,
                    "INFO",
                    "Removed generated DICOM files for this run.",
                )
            elif cleanup_error:
                runner._log_event(
                    999,
                    patient_iter,
                    repeat_iter,
                    "WARN",
                    f"Failed to remove generated DICOM files: {cleanup_error}",
                )
            _finish(True, "completed", attempt_override=attempt, max_attempts_override=max_attempts)
            return {"success": True}
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Worker encountered exception for job %s", job_id)
            _finish(
                False,
                "exception",
                error=str(exc),
                retrying=False,
                attempt_override=attempt,
                max_attempts_override=max_attempts,
            )
            return {"success": False}
