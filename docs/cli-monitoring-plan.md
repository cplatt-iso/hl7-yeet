# HL7 Yeeter CLI & Benchmarking Plan

## Objectives

- Provide repeatable command-line workflows for simulator runs, monitoring, and benchmarking.
- Keep existing UI workflows functional; any backend change must maintain compatibility or be paired with a UI update.
- Enable QA to launch large runs, capture performance data, and regress behavior without manual UI steps.

## High-Level Strategy

1. **Expose Simulator Control via CLI**
   - Build a standalone script (e.g., `scripts/yeeter_cli.py`) using `click` + `requests` that authenticates, starts runs, and monitors progress through the public API.
   - Optionally mirror commands as Flask CLI entrypoints for pod-level maintenance tasks.

2. **Augment Backend for Automation**
   - Ensure existing simulator endpoints accept all necessary parameters; add endpoints only if the CLI requires functionality not yet exposed.
   - Provide summary/metrics endpoints that return aggregated run statistics for QA.
   - Maintain API compatibility for the React UI; coordinate any breaking changes with concurrent frontend updates.

3. **Benchmarking Workflow**
   - Add CLI subcommands for structured outputs (`runs stats`, `runs export --format csv/json`).
   - Store CLI auth tokens securely (e.g., `~/.yeeter/config.json`) for QA use.
   - Document usage in `README.md` so new testers can run benchmarks quickly.

## Proposed CLI Command Surface

| Command | Purpose |
| ------- | ------- |
| `yeeter-cli login --username --password` | Obtain and cache JWT token for subsequent commands. |
| `yeeter-cli api-key --value <key>` | Store an API key generated in the UI for tokenless automation. |
| `yeeter-cli runs start --template-id <id> --patients <n>` | Kick off a simulation run through the API. |
| `yeeter-cli runs watch --run-id <id> [--follow]` | Stream run status updates by polling `/api/simulator/runs/<id>`. |
| `yeeter-cli runs stats --run-id <id> --format {json,csv}` | Retrieve performance metrics once the run completes. |
| `yeeter-cli runs cancel --run-id <id>` | Cancel an in-flight run via the new cancellation endpoint. |
| `yeeter-cli templates list [--output json]` | Inspect available templates (IDs/names) before launching runs. |
| `scripts/run_benchmark.sh <template_id> [patients]` | Automate start/watch/stats capture and save JSON/CSV artifacts. |

## Backend Support Checklist

- [x] Identify simulator API endpoints used by the CLI (start run, get run status, list events, fetch stats). ✅ `/api/simulator/run`, `/api/simulator/runs`, `/api/simulator/runs/<id>` already cover start/history/detail flows.
- [x] Add new endpoints only if necessary; ensure they’re versioned and UI-compatible. ✅ Added `POST /api/simulator/runs/<id>/cancel` without breaking existing UI flows.
- [x] Extend schemas/tests for any new API payloads. ✅ Added `SimulationRunStatsResponse` schema with unit tests for aggregation helper.
- [x] Provide aggregated metrics endpoint (e.g., `/api/simulator/runs/<id>/stats`). ✅ Implemented `GET /api/simulator/runs/<id>/stats` returning structured counts, durations, and per-step breakdowns.
- [ ] Confirm socket events remain unchanged or update the frontend simultaneously.

### API Capability Audit (2025-11-01)

| CLI Need | Current Endpoint | Status | Notes |
| -------- | ---------------- | ------ | ----- |
| Start simulation run | `POST /api/simulator/run` | ✅ Available | Accepts `template_id` and optional `patient_count`; returns `run_id`. |
| List recent runs | `GET /api/simulator/runs` | ✅ Available | Returns runs for authenticated user; excludes events. |
| Fetch run details/events | `GET /api/simulator/runs/<id>` | ✅ Available | Includes event list; sufficient for watch mode polling. |
| Cancel run | `POST /api/simulator/runs/<id>/cancel` | ✅ Available | Runner now honors cancellation requests and returns `CANCELLED` status. |
| Aggregated metrics/statistics | `GET /api/simulator/runs/<id>/stats` | ✅ Available | Returns aggregated counts/durations + per-step breakdown (requires further QA validation). |
| Stream updates | SocketIO `simulation_event` | ✅ Available | CLI will poll REST first; streaming extension optional. |

## CLI Implementation Checklist

- [x] Choose CLI approach (stand-alone script preferred for QA; Flask CLI optional). ✅ Implemented `scripts/yeeter_cli.py` with `click` + `requests`.
- [x] Implement authentication helper (handles token caching and refresh). ✅ Stores JWT in `~/.yeeter/config.json` with API URL metadata.
- [x] Implement `start`, `watch`, and `stats` commands using `requests`. ✅ Commands available under `yeeter-cli runs ...` group.
- [x] Add structured output options (pretty table, JSON, CSV). ✅ `runs stats` supports `--format table|json|csv`.
- [x] Include error handling for non-200 responses and timeouts. ✅ Centralized in `YeeterClient.request`.
- [x] Provide unit tests or integration tests using mocked API responses. ✅ Pytest suite covers stats helper and CLI flows via stubs.
- [x] Update documentation (`README`, internal wiki) with usage examples. ✅ README includes CLI usage and configuration overrides.
- [x] Support API key storage for headless automation. ✅ `yeeter-cli api-key` configures the CLI to send `X-API-Key` headers.

## QA / Benchmark Process

- [ ] Define benchmark templates (patient count, step configuration) and store IDs for reference.
- [x] Script baseline benchmarks (e.g., `scripts/run_benchmark.sh` calling the CLI) for CI/nightly runs. ✅ Helper added to orchestrate runs end-to-end.
- [x] Capture outputs and archive results (CSV/JSON) for trend analysis. ✅ Benchmark script saves timestamped JSON/CSV payloads.
- [ ] Add guidance for analyzing results (e.g., thresholds for acceptable performance).

## Compatibility & Regression Safeguards

- [ ] For every backend change, run frontend integration tests (or manual smoke tests) to ensure UI flows still function.
- [ ] Document API changes and notify frontend developers if adjustments are required.
- [ ] Provide feature flags or versioned endpoints when introducing breaking behavior.
- [ ] Update simulator UI only when necessary, keeping CLI and UI behavior aligned.

## Next Steps

1. ~~Confirm CLI tool surface and authentication approach.~~ ✅ Standalone `scripts/yeeter_cli.py` using `click` + `requests` will authenticate via `/api/auth/login` and cache tokens locally.
2. ~~Audit current API capabilities vs. CLI requirements; note any gaps.~~ ✅ See "API Capability Audit" table; metrics and cancellation gaps resolved.
3. ~~Plan backend metrics endpoint and ensure it doesn’t disrupt existing UI functionality.~~ ✅ `/api/simulator/runs/<id>/stats` added with schema-backed response.
4. Prototype CLI with start/watch commands and validate against staging environment.
5. Automate nightly benchmark scripts leveraging the CLI and publish metrics for QA review.
   - `scripts/run_benchmark.sh` now available; remaining work is scheduling + analysis guidance.
6. Document benchmark workflow for QA (see `docs/benchmark-guide.md`) and capture the list of staging-friendly templates once they exist.
