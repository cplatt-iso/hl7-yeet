# Frontend Metrics Integration Notes

## Context Recap
- Backend now exposes per-run metrics at `/api/simulator/runs/<id>/metrics` returning aggregate stats plus individual worker job entries.
- Socket events available today: `sim_log_update`, `sim_run_status_update`, and `simulation_async_job_queued`; additional real-time metrics streaming is still TBD on the backend.
- Metrics persistence requires the new `simulation_run_stats` and `worker_job_metrics` tables—ensure the DB migration is applied before attempting UI work.

## Immediate UI Tasks
- Add a simulator run detail view section (likely a new tab or accordion) that fetches the metrics endpoint once a run reaches `WAITING_ON_WORKERS` or `COMPLETED`.
- Render high-level aggregates (orders/sec, wall-clock, queue depth peaks, DICOM totals) as summary cards so users can scan performance quickly.
- Display worker job history in a virtualized table with sortable columns for duration, outcome, and timestamps; include failure highlighting.
- Provide CSV export from the browser using the metrics payload until backend CSV endpoints exist.

## Pending Backend Dependencies
- Global `/api/metrics/*` endpoints are still planned; design the frontend assuming future filters for date range, template, and user.
- Real-time metrics streaming via Socket.IO is listed on the TODO. Build UI components so they can accept live updates (e.g., via context/provider) once the events land.

## UX Considerations
- Keep HL7/IHE compliance front and center: surface modality, accession, and MPPS context alongside metrics where it helps validate workflows.
- Ensure metrics views respect auth scopes: reuse existing guards based on `isAuthenticated` and admin status for run ownership checks.
- Favor dark theme styling consistent with current Tailwind palette; use the existing toast system for load failures.

## Implementation Notes
- Create a dedicated hook (`useRunMetrics(runId)`) that handles fetching, polling, and state (loading/error/data). Reuse for both detail view and future dashboards.
- Extend the simulator router to link directly to `/runs/:id/metrics`. Consider lazy loading charts (e.g., `react-chartjs-2`) once we lock in visualization needs.
- Coordinate with autoscaler UI work so worker counts and queue snapshots use consistent terminology across tabs.
