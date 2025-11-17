# HL7 Yeeter High-Throughput Simulation Plan

## Goals

- Support bursts of 1,000+ orders per run without blocking on downstream work.
- Decouple HL7 order emission from DICOM generation, transmission, and other follow-on steps.
- Preserve per-run observability (SimulationRunEvent logs, socket updates) while work fans out.
- Allow horizontal scaling of worker capacity by deploying more replicas.

## Architectural Overview

1. **Order Producer (existing simulator runner)**
   - Continues to orchestrate patient loops and run metadata.
   - Generates ORM messages in sequence and publishes them over MLLP.
   - After each message, packages order context into a message and publishes it to a queue (RabbitMQ).
   - Marks run status transitions (e.g., `RUNNING` → `WAITING_ON_WORKERS`).
2. **Worker Pool (new service)**
   - Stateless processes consuming RabbitMQ jobs.
   - For each job, rebuilds run/patient context, executes queued simulation steps (e.g., GENERATE_DICOM, SEND_DICOM).
   - Produces SimulationRunEvent entries, emits socket events, and signals completion back to the DB.
3. **Message Bus (RabbitMQ)**
   - Provides durable queues for `generate_dicom`, `send_dicom`, etc.
   - Enables fan-out across multiple worker pods with visibility, acknowledgments, dead-letter support.
4. **Monitoring & Back-pressure**
   - Custom metrics logged from producer/worker (queue depth, job latency) with optional RabbitMQ management snapshots.
   - Worker autoscaling targets queue length / CPU.

## Work Breakdown

### Phase 0 – Prerequisites

- [x] Add `docs/` folder to repo.
- [ ] Confirm existing simulator logic for GENERATE_HL7 is stable at scale (load test single-threaded path).

### Phase 1 – RabbitMQ Infrastructure

- [x] Add manifest for RabbitMQ cluster in `k8s/rabbitmq.yaml`.
- [x] Create `Secret` with credentials (`RABBITMQ_URL`, user, password).
- [x] Update ConfigMap/Secrets with connection string for app/worker deployments.
- [x] Document `kubectl` workflow for deploying RabbitMQ and verifying connectivity (`docs/rabbitmq-deployment.md`).

### Phase 2 – Publisher Integration (Simulator Runner)

- [x] Implement a small AMQP client utility (`app/util/rabbitmq_client.py`) using Pika.
- [x] Extend `SimulationRunner.handle_generate_hl7` to optionally publish order jobs after context extraction (`queue_async` flag).
  - Payload includes: `run_id`, `step_id`, `patient_context`, `order_context`, template IDs, any timing overrides.
- [x] Update run lifecycle: after all orders queued, mark run status `WAITING_ON_WORKERS`.
- [x] Emit socket event indicating queued job count.

> **New configuration:** Set `queue_async: true` (and optional `queue_metadata`) on a `GENERATE_HL7` step to emit an order job. The publisher uses `RABBITMQ_URL` plus optional `RABBITMQ_ORDER_QUEUE` (defaults to `yeeter.simulation.orders`).

### Phase 3 – Worker Service

- [x] Create new module `app/worker/` with CLI entrypoint (run via `python -m app.worker`).
- [x] Implement consumer loop with manual ACK and optional requeue-on-error flag (future: add exponential backoff).
- [x] Reuse existing helper functions (`SimulationRunner` handlers wrap `create_study_files`, `perform_c_store`, etc.).
- [x] On success/failure, log `SimulationRunEvent` rows and emit socket updates (via existing Socket.IO integration).
- [x] Package worker container (Dockerfile.worker) and add new k8s deployment `yeeter-worker` (scalable replicas).

### Phase 4 – Step Orchestration Refinements

- [ ] Allow generator templates to specify which steps are "queued" vs "inline".
- [ ] Adjust SimulationStep model and schemas to store queue name / job type metadata.
- [x] Modify frontend simulator UI to show queue-driven progress (orders queued, workers processing, completions).
- [ ] Provide admin controls to scale worker replicas from UI (optional).
- [x] Script a RabbitMQ-backed autoscaler to scale `yeeter-worker` replicas based on queue depth.

### Phase 5 – Reliability & Observability

- [ ] Add retry/dead-letter queues for failed jobs.
- [ ] Integrate metrics (queue depth, worker throughput) into existing monitoring stack.
- [ ] Document operational playbooks for clearing stuck jobs / scaling workers / draining queues.

### Phase 6 – Performance Qualification

- [ ] Create load test suite that launches runs with 1,000 orders and validates end-to-end completion.
- [ ] Measure throughput (orders/sec, DICOM/sec) with varying worker counts.
- [ ] Tune RabbitMQ prefetch counts, worker concurrency, and DB transaction patterns.

## Open Questions / Follow-ups

- How should jobs be partitioned when steps have dependencies (e.g., `generate_dicom` must finish before `send_dicom`)? Separate queues or sequential worker logic?
- Do we need per-run isolation (dedicated queues) or can a shared queue suffice with run_id filtering?
- Should workers stream progress back via Socket.IO or pollable REST endpoint?
- Are there other simulation step types that benefit from asynchronous fan-out (e.g., MPPS updates)?

## Immediate Next Steps

- [x] Finalize RabbitMQ deployment approach and credentials management.
- [x] Draft AMQP publisher helper and local integration test (publish → consume → ack).
- [ ] Prototype worker that consumes jobs and executes a pared-down DICOM generation flow.
