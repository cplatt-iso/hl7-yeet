# Backend Benchmarking TODO

## Telemetry & Metrics

- [x] Emit structured JSON metrics from SimulationRunner and WorkerConsumer (queue publish latency, worker processing duration, DICOM send counts, bytes transferred).
- [x] Persist per-run and per-job aggregates in new DB tables (orders/sec, time-to-complete, min/avg/max job latency, queue depth snapshots).
- [ ] Add REST endpoints to fetch metrics (`/api/metrics/runs`, `/api/metrics/workers`) plus CSV export for benchmarking. (Per-run metrics now available at `/api/simulator/runs/<id>/metrics`; still need aggregated endpoints and CSV output.)
- [ ] Stream high-level metrics via Socket.IO (queued jobs count, active workers, average processing time) for the UI.

## Job Lifecycle Enhancements

- [ ] Implement retry + dead-letter queues for async jobs (configurable max attempts, requeue delay).
- [ ] Allow templates to mark steps as `async` vs `inline` along with custom queue names/job type metadata.
- [ ] Extend SimulationStep schema + CRUD to store queue metadata, wire to SimulationRunner and WorkerConsumer.

## API & Visibility

- [ ] Provide `/api/simulator/runs/<id>/metrics` returning aggregate timings and worker throughput summaries.
- [ ] Emit Socket.IO events for async progress (queued jobs count, active workers, remaining queue depth).
- [ ] Add admin endpoint to scale worker deployment (`POST /api/admin/workers/scale`) to back front-end controls.

## Autoscaling & Operations

- [ ] Package autoscaler as a k8s Deployment/CronJob with RBAC and env injection of RabbitMQ creds.
- [ ] Persist scaling decisions (timestamp, queue depth, replicas) for benchmarking audit trail.
- [ ] Document operational playbooks for clearing queues, draining workers, and interpreting metrics dashboards.

## Benchmark Harness

- [ ] Build scripted load driver to run templates at arbitrary patient counts, collecting wall-clock stats.
- [ ] Store benchmark runs + metrics in dedicated table or CSV for sharing with stakeholders.
- [ ] Add CLI flag to `yeeter_cli.py` to capture run metrics automatically after completion.
