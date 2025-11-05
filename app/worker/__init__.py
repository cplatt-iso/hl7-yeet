"""RabbitMQ worker entrypoint for simulation fan-out tasks."""
from __future__ import annotations

import argparse
import logging
import os
from typing import Optional

from .. import create_app
from ..util.rabbitmq_client import DEFAULT_ORDER_QUEUE
from .consumer import WorkerConsumer


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HL7 Yeeter worker service")
    parser.add_argument(
        "--amqp-url",
        default=os.environ.get("RABBITMQ_URL"),
        help="RabbitMQ connection URL (default: RABBITMQ_URL)",
    )
    parser.add_argument(
        "--queue",
        default=os.environ.get("RABBITMQ_ORDER_QUEUE", DEFAULT_ORDER_QUEUE),
        help="Queue name to consume (default: RABBITMQ_ORDER_QUEUE or yeeter.simulation.orders)",
    )
    parser.add_argument(
        "--prefetch",
        type=int,
        default=int(os.environ.get("WORKER_PREFETCH", "1")),
        help="Number of messages to prefetch (default: 1)",
    )
    parser.add_argument(
        "--requeue-on-error",
        action="store_true",
        help="Requeue messages when processing fails (default: ack failures)",
    )
    args = parser.parse_args(argv)
    if not args.amqp_url:
        parser.error("RabbitMQ URL is required (pass --amqp-url or set RABBITMQ_URL)")
    return args


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    logging.info(
        "Starting worker with queue '%s', prefetch=%s, requeue_on_error=%s",
        args.queue,
        args.prefetch,
        args.requeue_on_error,
    )

    app = create_app()
    consumer = WorkerConsumer(
        app=app,
        amqp_url=args.amqp_url,
        queue_name=args.queue,
        prefetch_count=args.prefetch,
        requeue_on_error=args.requeue_on_error,
    )
    consumer.start()


if __name__ == "__main__":
    main()
