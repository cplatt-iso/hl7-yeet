# Worker Autoscaling Guide

This document explains how to scale the `yeeter-worker` deployment automatically based on RabbitMQ queue depth.

## Overview

- Script: `scripts/worker_autoscaler.py`
- Metric source: RabbitMQ management API (`/api/queues/%2F/<queue>`)
- Scaling target: Kubernetes deployment `yeeter-worker` in namespace `yeeter`
- Scaling logic: maintain roughly `target-messages` queued jobs per worker replica (default: 50)

The script runs out-of-cluster (or from an ops pod) and issues `kubectl scale` commands when the queue size drifts beyond configured thresholds.

## Prerequisites

- RabbitMQ management API enabled on port 15672 (the `k8s/rabbitmq.yaml` manifest includes this).
- Credentials stored in the `yeeter-secrets` secret (`username: yeeter`, `password` matches `RABBITMQ_PASSWORD`).
- `kubectl` context pointed at the cluster where the `yeeter` namespace lives.
- Python 3 with the `requests` library available (already part of the project requirements).

## Running the Autoscaler

```bash
# Activate the project's virtualenv (optional but recommended)
source venv/bin/activate

# Export RabbitMQ management credentials (or pass via CLI flags)
export RABBITMQ_USERNAME=yeeter
export RABBITMQ_PASSWORD="<management-password>"

# Run a single evaluation (dry run)
python scripts/worker_autoscaler.py --once --dry-run

# Start continuous autoscaling, checking every 15 seconds
python scripts/worker_autoscaler.py --poll-interval 15
```

Key options:

- `--min-replicas` / `--max-replicas`: clamp worker deployment between these replica counts (defaults: 1 and 10).
- `--target-messages`: approximate number of queued jobs each worker should handle before scaling (default: 50).
- `--queue`: queue name to monitor (defaults to `yeeter.simulation.orders`).
- `--mgmt-url`: RabbitMQ management endpoint (`http://rabbitmq.yeeter.svc.cluster.local:15672`).
- `--once`: perform one evaluation cycle and exit.
- `--dry-run`: show target replicas without invoking `kubectl scale`.

## Example: Burst of 10,000 patients

1. Submit the async-enabled simulation template with `queue_async = true` for 10,000 patients.
2. Launch the autoscaler with `--min-replicas 2 --max-replicas 40 --target-messages 250`.
3. The script scales `yeeter-worker` up to keep roughly 250 queued jobs per worker (about 40 workers for the full backlog).
4. As the queue drains, the autoscaler gradually reduces replicas back toward the minimum.

## Scheduling the Autoscaler

For long-running environments, consider running the script as a Kubernetes CronJob or a dedicated Deployment (with a service account that has `kubectl scale` permissions). Mount the RabbitMQ credentials via environment variables or Kubernetes Secrets.

```bash
# Example systemd service snippet (runs autoscaler on login)
python /home/yeeter/hl7-yeet/scripts/worker_autoscaler.py \
  --min-replicas 2 \
  --max-replicas 40 \
  --target-messages 200 \
  --poll-interval 10
```

Current logic acts on total queue depth. Future enhancements could integrate with KEDA or Horizontal Pod Autoscaler custom metrics for fully in-cluster scaling.
