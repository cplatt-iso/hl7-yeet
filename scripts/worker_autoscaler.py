#!/usr/bin/env python3
"""Simple RabbitMQ-backed autoscaler for yeeter-worker deployment.

This utility polls the RabbitMQ management API to determine the backlog of
`yeeter.simulation.orders` jobs and adjusts the number of Kubernetes worker
replicas accordingly. It requires `kubectl` access to the target cluster and
credentials for the RabbitMQ management endpoint.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from typing import Optional
from urllib.parse import quote

import requests

DEFAULT_MANAGEMENT_URL = os.environ.get("RABBITMQ_MANAGEMENT_URL", "http://rabbitmq.yeeter.svc.cluster.local:15672")
DEFAULT_QUEUE = os.environ.get("RABBITMQ_ORDER_QUEUE", "yeeter.simulation.orders")
DEFAULT_NAMESPACE = os.environ.get("YEETER_NAMESPACE", "yeeter")
DEFAULT_DEPLOYMENT = os.environ.get("WORKER_DEPLOYMENT", "yeeter-worker")
DEFAULT_TARGET_PER_WORKER = int(os.environ.get("WORKER_TARGET_QUEUE", "50"))
DEFAULT_INTERVAL = float(os.environ.get("AUTOSCALER_INTERVAL", "15"))


class AutoscalerError(RuntimeError):
    """Raised when the autoscaler cannot continue."""


class KubernetesInterface:
    """Thin wrapper around kubectl for scaling deployments."""

    def __init__(self, namespace: str, deployment: str, kubectl_bin: str = "kubectl") -> None:
        self.namespace = namespace
        self.deployment = deployment
        self.kubectl_bin = kubectl_bin

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        cmd = [self.kubectl_bin, *args, "-n", self.namespace]
        try:
            return subprocess.run(cmd, check=True, text=True, capture_output=True)
        except subprocess.CalledProcessError as exc:  # pragma: no cover - external failure
            raise AutoscalerError(f"kubectl command failed: {' '.join(cmd)}\n{exc.stderr}") from exc

    def get_replicas(self) -> int:
        result = self._run([
            "get",
            "deployment",
            self.deployment,
            "-o",
            "jsonpath={.spec.replicas}",
        ])
        output = result.stdout.strip() or "0"
        try:
            return int(output)
        except ValueError as exc:  # pragma: no cover - defensive
            raise AutoscalerError(f"Failed to parse replica count from output: '{output}'") from exc

    def scale(self, replicas: int) -> None:
        self._run([
            "scale",
            "deployment",
            self.deployment,
            f"--replicas={replicas}",
        ])


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autoscale yeeter-worker deployment based on RabbitMQ queue depth.")
    parser.add_argument("--mgmt-url", default=DEFAULT_MANAGEMENT_URL, help="RabbitMQ management base URL.")
    parser.add_argument("--username", default=os.environ.get("RABBITMQ_USERNAME", "yeeter"), help="RabbitMQ management username.")
    parser.add_argument("--password", default=os.environ.get("RABBITMQ_PASSWORD"), help="RabbitMQ management password.")
    parser.add_argument("--queue", default=DEFAULT_QUEUE, help="Queue name to inspect for backlog.")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE, help="Kubernetes namespace hosting the worker deployment.")
    parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT, help="Name of worker deployment to scale.")
    parser.add_argument("--kubectl", default=os.environ.get("KUBECTL_BIN", "kubectl"), help="Path to kubectl binary.")
    parser.add_argument("--min-replicas", type=int, default=int(os.environ.get("WORKER_MIN_REPLICAS", "1")), help="Minimum worker replicas.")
    parser.add_argument("--max-replicas", type=int, default=int(os.environ.get("WORKER_MAX_REPLICAS", "10")), help="Maximum worker replicas.")
    parser.add_argument(
        "--target-messages",
        type=int,
        default=DEFAULT_TARGET_PER_WORKER,
        help="Approximate number of queued messages each worker should handle before scaling up.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help="Polling interval in seconds.",
    )
    parser.add_argument("--once", action="store_true", help="Run a single evaluation cycle and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Compute desired replicas without issuing kubectl commands.")

    args = parser.parse_args(argv)
    if not args.password:
        parser.error("RabbitMQ password is required (set --password or RABBITMQ_PASSWORD).")
    if args.min_replicas < 1:
        parser.error("--min-replicas must be >= 1")
    if args.max_replicas < args.min_replicas:
        parser.error("--max-replicas must be >= --min-replicas")
    if args.target_messages <= 0:
        parser.error("--target-messages must be > 0")
    if args.poll_interval <= 0:
        parser.error("--poll-interval must be > 0")
    return args


def fetch_queue_depth(mgmt_url: str, queue: str, username: str, password: str) -> int:
    encoded_queue = quote(queue, safe="")
    url = f"{mgmt_url.rstrip('/')}/api/queues/%2F/{encoded_queue}"
    try:
        response = requests.get(url, auth=(username, password), timeout=5)
    except requests.RequestException as exc:
        raise AutoscalerError(f"Failed to query RabbitMQ management API: {exc}") from exc

    if response.status_code == 404:
        raise AutoscalerError(f"Queue '{queue}' not found at {url}")
    if response.status_code >= 400:
        raise AutoscalerError(f"RabbitMQ management API returned {response.status_code}: {response.text}")

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise AutoscalerError(f"Unexpected response from RabbitMQ management API: {response.text}") from exc

    return int(data.get("messages", 0))


def compute_desired_replicas(
    queue_depth: int,
    current_replicas: int,
    *,
    min_replicas: int,
    max_replicas: int,
    target_messages: int,
) -> int:
    if queue_depth <= 0:
        return min_replicas

    required = math.ceil(queue_depth / target_messages)
    desired = max(min_replicas, min(required, max_replicas))

    # Avoid unnecessary scale-down jitter: only scale down if backlog is well under capacity.
    if desired < current_replicas and queue_depth > 0:
        if queue_depth >= (desired * target_messages) * 0.5:
            return current_replicas
    return desired


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    kube = KubernetesInterface(namespace=args.namespace, deployment=args.deployment, kubectl_bin=args.kubectl)

    while True:
        try:
            queue_depth = fetch_queue_depth(args.mgmt_url, args.queue, args.username, args.password)
            current = kube.get_replicas()
            desired = compute_desired_replicas(
                queue_depth,
                current,
                min_replicas=args.min_replicas,
                max_replicas=args.max_replicas,
                target_messages=args.target_messages,
            )
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"[{timestamp}] queue={queue_depth} messages | current={current} replicas | desired={desired}",
                flush=True,
            )

            if desired != current:
                if args.dry_run:
                    print(f"[dry-run] would scale {args.deployment} to {desired}")
                else:
                    kube.scale(desired)
                    print(f"Scaled {args.deployment} to {desired} replicas")
        except AutoscalerError as exc:
            print(f"[error] {exc}", file=sys.stderr)

        if args.once:
            break
        time.sleep(args.poll_interval)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
