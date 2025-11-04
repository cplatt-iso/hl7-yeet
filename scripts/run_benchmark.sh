#!/usr/bin/env bash
# Run a HL7 Yeeter simulation benchmark and archive stats.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/run_benchmark.sh <template_id> [patients] [output_dir] [poll_seconds]

Requires:
  - python3 (to invoke scripts/yeeter_cli.py)
  - jq (to parse JSON output from the CLI)
  - HL7 Yeeter CLI already configured with credentials (JWT or API key).

Arguments:
  template_id   Simulation template identifier to execute (required).
  patients      Number of patient iterations to simulate (default: 1).
  output_dir    Directory where stats artifacts are saved (default: benchmarks).
  poll_seconds  Poll interval passed to `yeeter_cli runs watch` (default: 5).
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  echo "[error] Missing required template_id argument." >&2
  usage
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "[error] jq is required for parsing CLI output." >&2
  exit 1
fi

TEMPLATE_ID=$1
PATIENTS=${2:-1}
OUTPUT_DIR=${3:-benchmarks}
POLL_SECONDS=${4:-5}

mkdir -p "$OUTPUT_DIR"

START_JSON=$(python3 scripts/yeeter_cli.py runs start --template-id "$TEMPLATE_ID" --patients "$PATIENTS" --output json)
RUN_ID=$(echo "$START_JSON" | jq -r '.run_id // empty')

if [[ -z "$RUN_ID" ]]; then
  echo "[error] Unable to determine run_id from CLI output:" >&2
  echo "$START_JSON" >&2
  exit 1
fi

echo "[info] Run $RUN_ID launched (template=$TEMPLATE_ID patients=$PATIENTS)."

echo "[info] Monitoring run $RUN_ID (poll ${POLL_SECONDS}s)..."
python3 scripts/yeeter_cli.py runs watch "$RUN_ID" --interval "$POLL_SECONDS"

STAMP=$(date +%Y%m%dT%H%M%S)
STATS_JSON_PATH="$OUTPUT_DIR/run_${RUN_ID}_${STAMP}.json"
STATS_CSV_PATH="$OUTPUT_DIR/run_${RUN_ID}_${STAMP}.csv"

python3 scripts/yeeter_cli.py runs stats "$RUN_ID" --format json > "$STATS_JSON_PATH"
python3 scripts/yeeter_cli.py runs stats "$RUN_ID" --format csv > "$STATS_CSV_PATH"

echo "[info] Stats exported to:"
echo "       JSON -> $STATS_JSON_PATH"
echo "       CSV  -> $STATS_CSV_PATH"
