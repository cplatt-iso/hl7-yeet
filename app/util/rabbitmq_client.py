# --- START OF FILE app/util/rabbitmq_client.py ---
"""Lightweight RabbitMQ publishing helper for simulator fan-out workflows."""
from __future__ import annotations

import atexit
import json
import logging
import threading
from datetime import datetime
from typing import Any, Optional

import pika
from pika.adapters.blocking_connection import BlockingChannel

DEFAULT_QUEUE_PREFIX = "yeeter.simulation"
DEFAULT_ORDER_QUEUE = f"{DEFAULT_QUEUE_PREFIX}.orders"


def _json_default(value: Any) -> str:
    """Fallback serializer for JSON dumps."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class RabbitMQPublisher:
    """Thread-safe, lazy RabbitMQ publisher wrapper."""

    def __init__(self, amqp_url: str, *, order_queue: str = DEFAULT_ORDER_QUEUE) -> None:
        self.amqp_url = amqp_url
        self.order_queue = order_queue
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[BlockingChannel] = None
        self._lock = threading.Lock()
        atexit.register(self.close)
        logging.info("RabbitMQPublisher configured for %s", self._sanitize_url(amqp_url))

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Hide credentials when logging connection info."""
        if "@" not in url:
            return url
        try:
            scheme, rest = url.split("://", 1)
        except ValueError:  # pragma: no cover - defensive
            return "amqp://***@***"
        host_part = rest.split("@", 1)[1]
        return f"{scheme}://***@{host_part}"

    # --- connection helpers ---
    def _ensure_channel(self) -> Optional[BlockingChannel]:
        """Ensure an open channel is available, connecting on demand."""
        with self._lock:
            if self._channel and self._channel.is_open:
                return self._channel

            self._close_locked()
            try:
                parameters = pika.URLParameters(self.amqp_url)
                self._connection = pika.BlockingConnection(parameters)
                self._channel = self._connection.channel()
                logging.debug("RabbitMQPublisher connected to broker")
                return self._channel
            except Exception as exc:
                logging.error("Failed to connect to RabbitMQ: %s", exc)
                self._close_locked()
                return None

    def publish_json(
        self,
        queue_name: str,
        payload: dict[str, Any],
        *,
        durable: bool = True,
        expiration_ms: int | None = None,
        headers: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Publish a JSON payload to the specified queue."""
        channel = self._ensure_channel()
        if not channel:
            return False

        try:
            channel.queue_declare(queue=queue_name, durable=durable, arguments=None)
            properties = pika.BasicProperties(
                delivery_mode=2 if durable else 1,
                expiration=str(expiration_ms) if expiration_ms else None,
                headers=headers,
                content_type="application/json",
            )
            body = json.dumps(payload, default=_json_default)
            channel.basic_publish(exchange="", routing_key=queue_name, body=body, properties=properties)
            logging.debug("Published message to %s", queue_name)
            return True
        except Exception as exc:
            logging.error("Failed to publish message to %s: %s", queue_name, exc)
            self._reset()
            return False

    def publish_order_job(self, payload: dict[str, Any]) -> bool:
        """Convenience helper for the default order queue."""
        return self.publish_json(self.order_queue, payload)

    def close(self) -> None:
        """Close the channel/connection if they are still open."""
        with self._lock:
            self._close_locked()

    def _reset(self) -> None:
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        if self._channel:
            try:
                self._channel.close()
            except Exception:  # pragma: no cover - best effort
                pass
            finally:
                self._channel = None
        if self._connection:
            try:
                self._connection.close()
            except Exception:  # pragma: no cover - best effort
                pass
            finally:
                self._connection = None


_publisher: Optional[RabbitMQPublisher] = None
_publisher_lock = threading.Lock()


def init_rabbitmq_publisher(amqp_url: Optional[str], *, order_queue: str | None = None) -> None:
    """Configure the global publisher singleton."""
    global _publisher
    with _publisher_lock:
        if not amqp_url:
            _publisher = None
            logging.info("RabbitMQPublisher disabled (no AMQP URL provided)")
            return
        queue_name = order_queue or DEFAULT_ORDER_QUEUE
        _publisher = RabbitMQPublisher(amqp_url, order_queue=queue_name)


def get_rabbitmq_publisher() -> Optional[RabbitMQPublisher]:
    with _publisher_lock:
        return _publisher


def is_rabbitmq_enabled() -> bool:
    return get_rabbitmq_publisher() is not None


# --- END OF FILE app/util/rabbitmq_client.py ---
