# HL7 Yeeter Benchmark Guide

This document describes the current workflow for running automated simulator benchmarks via the CLI.

## Pre-requisites

- API key or JWT configured for the CLI (`python3 scripts/yeeter_cli.py api-key --value ...`).
- `python3`, `jq`, and network access to the Yeeter API host (default `https://yeet.trazen.org`).
- Local workstation with the repository checked out (the helper scripts assume the repo root).

## Discovering Templates

Use the CLI to enumerate templates that exist in the target environment:

```bash
python3 scripts/yeeter_cli.py templates list
python3 scripts/yeeter_cli.py templates list --output json | jq
```

Template metadata is returned directly from `/api/simulator/templates`. For now, the production environment exposes:

- `1` – Order -> MPPS In Progress -> DICOM -> MPPS Complete
- `2` – PACS imaging
- `4` – Study to Axiom
- `5` – Orders only -> Axiom

> **Note:** Templates that send real traffic to external endpoints (Axiom, PACS) will fail if the downstream systems reject the payload (e.g., missing schema columns). For repeatable benchmarks, create templates that rely only on internal steps (`WAIT`, `GENERATE_HL7`, mock endpoints) or point to a staging receiver.

## Running a Benchmark

The helper script orchestrates a full run, watches it to completion, and exports stats:

```bash
# Run template 42 with 10 patients and store artifacts in ./benchmarks
scripts/run_benchmark.sh 42 10 benchmarks 5
```

Outputs are written to `benchmarks/run_<id>_<timestamp>.json` and `.csv`, mirroring the CLI `runs stats` response.

If a run fails (`status != COMPLETED`), inspect the JSON payload for `last_failure` and the event log to understand which step rejected the workflow. Use `python3 scripts/yeeter_cli.py runs watch <run_id>` to replay the log.

## Recommended Next Steps

1. **Define Staging Templates** – Build simulator templates that do not depend on external systems so we can gather repeatable metrics. A simple pattern uses `GENERATE_HL7`, `WAIT`, and logging-only steps.
2. **Schedule Nightly Benchmarks** – Once stable templates exist, wire `scripts/run_benchmark.sh` into cron or CI, and archive the resulting JSON/CSV for trend analysis.
3. **Establish Thresholds** – Decide acceptable ranges for duration, failure counts, or per-step timings; alert when metrics drift.
4. **Cancellation Testing** – Include a template with `WAIT` steps to allow exercising the `runs cancel` workflow end-to-end.

Document updates or new template IDs in this guide to keep the QA team aligned.
