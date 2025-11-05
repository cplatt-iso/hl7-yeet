# --- START OF FILE app/util/metrics.py ---
"""Structured metrics emission helpers."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_METRICS_LOGGER = logging.getLogger("yeeter.metrics")


def _default_serializer(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def emit_metric(event: str, **fields: Any) -> None:
    """Log a structured JSON metric entry."""
    record: dict[str, Any] = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    try:
        payload = json.dumps(record, default=_default_serializer, separators=(",", ":"))
    except TypeError:
        record = {"event": event, "timestamp": record["timestamp"], "error": "serialization_failed"}
        payload = json.dumps(record, separators=(",", ":"))
    _METRICS_LOGGER.info(payload)


# --- END OF FILE app/util/metrics.py ---
