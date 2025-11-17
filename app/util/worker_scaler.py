# --- START OF FILE app/util/worker_scaler.py ---
"""Worker autoscaler that adjusts the async worker deployment based on queue depth."""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
from urllib.parse import quote, urlparse

import requests
from requests.auth import HTTPBasicAuth

from ..extensions import db
from .. import crud

try:  # pragma: no cover - dependency optional outside Kubernetes
    from kubernetes import client, config as k8s_config  # type: ignore[import]
    from kubernetes.client import ApiException  # type: ignore[import]
except ImportError:  # pragma: no cover - fallback when kubernetes client missing
    client = None  # type: ignore[assignment]
    k8s_config = None  # type: ignore[assignment]

    class ApiException(Exception):  # type: ignore[override]
        pass

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from kubernetes.client import AppsV1Api  # type: ignore[import]

AUTOSCALE_METADATA_KEY = "worker_autoscaler_config"


@dataclass
class AutoscaleState:
    """Holds live state for status reporting."""

    last_queue_depth: Optional[int] = None
    last_queue_check_at: Optional[datetime] = None
    last_scale_at: Optional[datetime] = None
    last_scale_action: Optional[str] = None
    last_error: Optional[str] = None
    kubernetes_connected: bool = False
    current_replicas: Optional[int] = None
    target_replicas: Optional[int] = None


DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "min_replicas": 1,
    "max_replicas": 3,
    "scale_up_threshold": 10,  # messages per worker before scaling up
    "scale_up_step": 1,
    "scale_down_threshold": 3,  # messages per worker to stay above before scaling down
    "scale_down_step": 1,
    "scale_down_cooldown_seconds": 180,
    "poll_interval_seconds": 15,
    "management_port": 15672,
    "queue_name": None,
}


class WorkerAutoscaler:
    """Monitors RabbitMQ queue depth and scales the worker deployment via Kubernetes."""

    def __init__(self, app):
        self.app = app
        self.namespace = app.config.get("K8S_NAMESPACE", "default")
        self.deployment_name = app.config.get("WORKER_DEPLOYMENT_NAME", "yeeter-worker")
        self._config_lock = threading.Lock()
        self._config: Dict[str, Any] = self._load_config_from_db()
        self._state = AutoscaleState()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_queue_above_down_threshold = time.monotonic()
        self._manual_override: Optional[int] = None
        self._manual_override_at: Optional[datetime] = None
        self._queue_url: Optional[str] = None
        self._queue_auth: Optional[HTTPBasicAuth] = None

        self._apps_v1: Optional["AppsV1Api"] = None  # type: ignore[assignment]
        self._load_kubernetes_client()
        self._apply_queue_settings()

    # --- Initialization helpers ---

    def _load_kubernetes_client(self) -> None:
        if client is None or k8s_config is None:
            logging.warning("WorkerAutoscaler: kubernetes client not available; scaling disabled")
            self._state.kubernetes_connected = False
            return
        try:
            if self.app.config.get("KUBERNETES_SERVICE_HOST") or self.app.config.get("IN_CLUSTER", True):
                k8s_config.load_incluster_config()
            else:
                k8s_config.load_kube_config()
            self._apps_v1 = client.AppsV1Api()
            self._state.kubernetes_connected = True
            logging.info(
                "WorkerAutoscaler: Kubernetes client initialized for deployment %s in namespace %s",
                self.deployment_name,
                self.namespace,
            )
        except Exception as exc:  # pragma: no cover - depends on cluster environment
            logging.exception("WorkerAutoscaler: failed to initialize Kubernetes client: %s", exc)
            self._apps_v1 = None
            self._state.kubernetes_connected = False
            self._state.last_error = f"kubernetes client init failed: {exc}"

    def _apply_queue_settings(self) -> None:
        rabbitmq_url = self.app.config.get("RABBITMQ_URL")
        queue_name = self._config.get("queue_name") or self.app.config.get("RABBITMQ_ORDER_QUEUE")

        if not rabbitmq_url or not queue_name:
            self._queue_url = None
            self._queue_auth = None
            logging.warning("WorkerAutoscaler: RabbitMQ URL or queue missing; queue depth checks disabled")
            return

        parsed = urlparse(rabbitmq_url)
        management_port = int(self._config.get("management_port") or DEFAULT_CONFIG["management_port"])
        host = parsed.hostname or "localhost"
        vhost = parsed.path[1:] if parsed.path else ""
        if not vhost:
            vhost = "/"

        encoded_vhost = quote(vhost, safe="")
        encoded_queue = quote(queue_name, safe="")
        self._queue_url = f"http://{host}:{management_port}/api/queues/{encoded_vhost}/{encoded_queue}"

        if parsed.username:
            self._queue_auth = HTTPBasicAuth(parsed.username, parsed.password or "")
        else:
            self._queue_auth = None
        logging.info("WorkerAutoscaler: monitoring queue '%s' on %s", queue_name, host)

    # --- Configuration persistence ---

    def _load_config_from_db(self) -> Dict[str, Any]:
        with self.app.app_context():
            metadata = crud.get_metadata(db, AUTOSCALE_METADATA_KEY)
        loaded: Dict[str, Any] = DEFAULT_CONFIG.copy()
        if metadata:
            try:
                payload = json.loads(metadata.value)
                if isinstance(payload, dict):
                    loaded.update({k: payload[k] for k in payload if k in DEFAULT_CONFIG})
            except json.JSONDecodeError:
                logging.warning("WorkerAutoscaler: invalid autoscaler config JSON; using defaults")
        return self._sanitize_config(loaded)

    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = DEFAULT_CONFIG.copy()
        sanitized.update(config)
        sanitized["enabled"] = bool(sanitized.get("enabled"))
        sanitized["min_replicas"] = max(1, int(sanitized.get("min_replicas", 1)))
        sanitized["max_replicas"] = max(sanitized["min_replicas"], int(sanitized.get("max_replicas", sanitized["min_replicas"])))
        sanitized["scale_up_threshold"] = max(1, int(sanitized.get("scale_up_threshold", 1)))
        sanitized["scale_up_step"] = max(1, int(sanitized.get("scale_up_step", 1)))
        sanitized["scale_down_threshold"] = max(0, int(sanitized.get("scale_down_threshold", 0)))
        sanitized["scale_down_step"] = max(1, int(sanitized.get("scale_down_step", 1)))
        sanitized["scale_down_cooldown_seconds"] = max(0, int(sanitized.get("scale_down_cooldown_seconds", 0)))
        sanitized["poll_interval_seconds"] = max(5, int(sanitized.get("poll_interval_seconds", 5)))
        sanitized["management_port"] = int(sanitized.get("management_port", DEFAULT_CONFIG["management_port"]))
        queue_name = sanitized.get("queue_name") or self.app.config.get("RABBITMQ_ORDER_QUEUE")
        sanitized["queue_name"] = queue_name
        if sanitized["min_replicas"] > sanitized["max_replicas"]:
            sanitized["max_replicas"] = sanitized["min_replicas"]
        return sanitized

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        with self._config_lock:
            merged = self._sanitize_config({**self._config, **new_config})
            self._config = merged
            with self.app.app_context():
                crud.set_metadata(db, AUTOSCALE_METADATA_KEY, json.dumps(merged))
            self._apply_queue_settings()
        logging.info("WorkerAutoscaler: configuration updated: %s", merged)
        # Ensure bounds immediately respected
        self._ensure_bounds()
        return merged

    def get_config(self) -> Dict[str, Any]:
        with self._config_lock:
            return dict(self._config)

    # --- Lifecycle ---

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, name="worker-autoscaler", daemon=True)
        self._thread.start()
        logging.info("WorkerAutoscaler: monitor thread started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logging.info("WorkerAutoscaler: monitor thread stopped")

    # --- Scaling helpers ---

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            config = self.get_config()
            poll_interval = config.get("poll_interval_seconds", DEFAULT_CONFIG["poll_interval_seconds"])

            try:
                if config.get("enabled") and self._apps_v1:
                    self._perform_control_loop(config)
            except Exception as exc:  # pragma: no cover - defensive logging
                logging.exception("WorkerAutoscaler: control loop error: %s", exc)
                self._state.last_error = str(exc)
            finally:
                # Sleep with stop-event awareness
                self._stop_event.wait(poll_interval)

    def _perform_control_loop(self, config: Dict[str, Any]) -> None:
        queue_depth = self._fetch_queue_depth()
        now = datetime.now(timezone.utc)
        self._state.last_queue_depth = queue_depth
        self._state.last_queue_check_at = now

        if queue_depth is None:
            return

        current_replicas = self._refresh_current_replicas()
        if current_replicas is None or current_replicas <= 0:
            return

        messages_per_worker = queue_depth / max(current_replicas, 1)
        if messages_per_worker > config["scale_down_threshold"]:
            self._last_queue_above_down_threshold = time.monotonic()

        if self._manual_override is not None:
            desired = int(self._manual_override)
            if desired != current_replicas:
                success, error = self._set_replicas(desired)
                if success:
                    self._record_scale("manual", desired)
                else:
                    self._state.last_error = error
            else:
                self._manual_override = None
            return

        # Scale up logic
        if (
            messages_per_worker > config["scale_up_threshold"]
            and current_replicas < config["max_replicas"]
        ):
            computed = math.ceil(queue_depth / max(config["scale_up_threshold"], 1))
            desired = min(
                config["max_replicas"],
                max(current_replicas + config["scale_up_step"], computed),
            )
            if desired > current_replicas:
                success, error = self._set_replicas(desired)
                if success:
                    self._record_scale("scale_up", desired)
                else:
                    self._state.last_error = error
                return

        # Scale down logic
        if (
            messages_per_worker <= config["scale_down_threshold"]
            and current_replicas > config["min_replicas"]
        ):
            cooldown = config["scale_down_cooldown_seconds"]
            if time.monotonic() - self._last_queue_above_down_threshold >= cooldown:
                desired = max(config["min_replicas"], current_replicas - config["scale_down_step"])
                if desired < current_replicas:
                    success, error = self._set_replicas(desired)
                    if success:
                        self._record_scale("scale_down", desired)
                        # Reset cooldown timer so we don't scale down repeatedly too fast
                        self._last_queue_above_down_threshold = time.monotonic()
                    else:
                        self._state.last_error = error

    def _record_scale(self, action: str, desired: int) -> None:
        now = datetime.now(timezone.utc)
        self._state.last_scale_action = action
        self._state.last_scale_at = now
        self._state.target_replicas = desired
        logging.info("WorkerAutoscaler: %s to %s replicas", action, desired)

    def _fetch_queue_depth(self) -> Optional[int]:
        url = self._queue_url
        if not url:
            return None
        try:
            response = requests.get(url, auth=self._queue_auth, timeout=5)
            if response.status_code != 200:
                self._state.last_error = f"rabbitmq api {response.status_code}"
                return None
            payload = response.json()
            depth = int(payload.get("messages", 0))
            self._state.last_error = None
            return depth
        except Exception as exc:  # pragma: no cover - network variability
            logging.warning("WorkerAutoscaler: failed to fetch queue depth: %s", exc)
            self._state.last_error = str(exc)
            return None

    def _refresh_current_replicas(self) -> Optional[int]:
        if not self._apps_v1:
            self._state.kubernetes_connected = False
            return None
        try:
            scale = self._apps_v1.read_namespaced_deployment_scale(
                name=self.deployment_name,
                namespace=self.namespace,
            )
            current = int(scale.status.replicas or scale.spec.replicas or 0)
            self._state.current_replicas = current
            self._state.kubernetes_connected = True
            self._state.last_error = None
            return current
        except ApiException as exc:  # pragma: no cover - depends on cluster state
            logging.error("WorkerAutoscaler: failed to read deployment scale: %s", exc)
            self._state.kubernetes_connected = False
            self._state.last_error = f"cant read deployment scale: {exc}"
            return None
        except Exception as exc:  # pragma: no cover - broader network/config errors
            logging.error("WorkerAutoscaler: unexpected error reading deployment scale: %s", exc, exc_info=True)
            self._state.kubernetes_connected = False
            self._state.last_error = str(exc)
            return None

    def _set_replicas(self, replicas: int) -> Tuple[bool, Optional[str]]:
        if not self._apps_v1:
            return False, "kubernetes client unavailable"
        try:
            body = {"spec": {"replicas": int(replicas)}}
            self._apps_v1.patch_namespaced_deployment_scale(
                name=self.deployment_name,
                namespace=self.namespace,
                body=body,
            )
            # Update cached replicas after successful patch
            self._state.current_replicas = int(replicas)
            self._state.last_error = None
            return True, None
        except ApiException as exc:  # pragma: no cover - depends on cluster state
            logging.error("WorkerAutoscaler: failed to scale deployment: %s", exc)
            self._state.last_error = str(exc)
            return False, str(exc)
        except Exception as exc:  # pragma: no cover - broader network/config errors
            logging.error("WorkerAutoscaler: unexpected error during scaling: %s", exc, exc_info=True)
            self._state.last_error = str(exc)
            return False, str(exc)

    def _ensure_bounds(self) -> None:
        current = self._refresh_current_replicas()
        if current is None:
            return
        config = self.get_config()
        desired = current
        if current < config["min_replicas"]:
            desired = config["min_replicas"]
        elif current > config["max_replicas"]:
            desired = config["max_replicas"]
        if desired != current:
            success, error = self._set_replicas(desired)
            if success:
                self._record_scale("bounds", desired)
            else:
                self._state.last_error = error

    # --- Public API ---

    def get_status_payload(self) -> Dict[str, Any]:
        config = self.get_config()
        state_dict = {
            "current_replicas": self._state.current_replicas,
            "queue_depth": self._state.last_queue_depth,
            "last_queue_check_at": self._state.last_queue_check_at.isoformat() if self._state.last_queue_check_at else None,
            "last_scale_at": self._state.last_scale_at.isoformat() if self._state.last_scale_at else None,
            "last_scale_action": self._state.last_scale_action,
            "last_error": self._state.last_error,
            "kubernetes_connected": self._state.kubernetes_connected,
            "manual_override_active": self._manual_override is not None,
            "manual_override_replicas": self._manual_override,
            "manual_override_at": self._manual_override_at.isoformat() if self._manual_override_at else None,
        }
        return {"config": config, "status": state_dict}

    def apply_manual_scale(self, replicas: int) -> Tuple[bool, Optional[str]]:
        replicas = int(replicas)
        if replicas <= 0:
            return False, "replicas must be greater than zero"
        self._manual_override = replicas
        self._manual_override_at = datetime.now(timezone.utc)
        success, error = self._set_replicas(replicas)
        if success:
            self._record_scale("manual", replicas)
            return True, None
        return False, error

    def clear_manual_override(self) -> None:
        self._manual_override = None
        self._manual_override_at = None


_autoscaler: Optional[WorkerAutoscaler] = None


def init_worker_autoscaler(app) -> WorkerAutoscaler:
    global _autoscaler
    if app.config.get("WORKER_AUTOSCALER_ENABLED", True) is False:
        logging.info("WorkerAutoscaler: disabled via configuration")
        return _autoscaler or WorkerAutoscaler(app)

    if _autoscaler is None:
        _autoscaler = WorkerAutoscaler(app)
        _autoscaler.start()
        logging.info("WorkerAutoscaler: initialized and running")
    return _autoscaler


def get_worker_autoscaler() -> Optional[WorkerAutoscaler]:
    return _autoscaler

# --- END OF FILE app/util/worker_scaler.py ---
