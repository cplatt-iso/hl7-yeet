# RabbitMQ Deployment Guide

This guide explains how to deploy RabbitMQ into the `yeeter` namespace of the k3s cluster and verify connectivity for the HL7 Yeeter simulator.

## Prerequisites

- Working k3s cluster with kubectl access.
- `yeeter` namespace created (`kubectl apply -f k8s/namespace.yaml`).
- Local Docker image workflow already configured (see `.github/copilot-instructions.md`).

## Manifests

| File | Purpose |
| ---- | ------- |
| `k8s/rabbitmq-secret.yaml` | Stores default RabbitMQ credentials (`yeeter` / `tCAHnKsSmp66Obn_MknxeFXn`). |
| `k8s/rabbitmq.yaml` | StatefulSet + Service exposing AMQP (5672) and management UI (15672). |

> **Security Reminder:** Replace the default password before deploying to any shared or production environment.

## Deployment Steps

1. **Create/Update Secrets**

   ```bash
   kubectl apply -f k8s/rabbitmq-secret.yaml
   ```

   To customize credentials, edit the file and base64 encode the new values:

   ```bash
   echo -n "myuser" | base64
   echo -n "strong-password" | base64
   ```

1. **Deploy RabbitMQ**

   ```bash
   kubectl apply -f k8s/rabbitmq.yaml
   kubectl -n yeeter rollout status statefulset/rabbitmq
   ```

1. **Verify Pods & Services**

   ```bash
   kubectl -n yeeter get pods -l app=rabbitmq
   kubectl -n yeeter get svc rabbitmq
   ```

1. **Access Management UI (optional)**

   ```bash
   kubectl -n yeeter port-forward svc/rabbitmq 15672:15672
   ```

   Then open `http://localhost:15672/` and log in with the secret credentials.

## Next Steps

- Backend deployment now sources `RABBITMQ_URL` from `yeeter-secrets`; implement publishing/consuming logic next.
- Add queue provisioning logic or definitions if needed for simulator jobs.
- Integrate publishing/consuming logic in the backend and worker services per the massive throughput plan.
