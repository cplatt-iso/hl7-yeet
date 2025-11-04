#!/usr/bin/env bash
set -euo pipefail

# Minimal helper script to build local images and load them into a k3s cluster.

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_IMAGE=${BACKEND_IMAGE:-hl7-yeeter:latest}
FRONTEND_IMAGE=${FRONTEND_IMAGE:-hl7-yeeter-frontend:latest}
K8S_NAMESPACE=${K8S_NAMESPACE:-yeeter}
KUBECTL_BIN=${KUBECTL:-kubectl}
SUDO_BIN=${SUDO_BIN:-sudo}

log() {
  echo "[k3s-build] $*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

import_image() {
  local image="$1"
  if command -v k3s >/dev/null 2>&1; then
    log "Importing ${image} into k3s (containerd)"
    docker save "${image}" | ${SUDO_BIN} k3s ctr images import -
  elif command -v nerdctl >/dev/null 2>&1; then
    log "Importing ${image} via nerdctl"
    docker save "${image}" | ${SUDO_BIN} nerdctl --namespace k8s.io load
  else
    log "Neither k3s nor nerdctl found for image import"
    exit 1
  fi
}

rollout_restart() {
  local deploy="$1"
  log "Restarting deployment ${deploy}"
  ${KUBECTL_BIN} -n "${K8S_NAMESPACE}" rollout restart "deployment/${deploy}"
  ${KUBECTL_BIN} -n "${K8S_NAMESPACE}" rollout status "deployment/${deploy}"
}

main() {
  require_cmd docker
  require_cmd ${KUBECTL_BIN}

  log "Building backend image ${BACKEND_IMAGE}"
  docker build -t "${BACKEND_IMAGE}" -f "${PROJECT_ROOT}/Dockerfile" "${PROJECT_ROOT}"

  log "Building frontend image ${FRONTEND_IMAGE}"
  docker build -t "${FRONTEND_IMAGE}" -f "${PROJECT_ROOT}/Dockerfile.frontend" "${PROJECT_ROOT}"

  import_image "${BACKEND_IMAGE}"
  import_image "${FRONTEND_IMAGE}"

  rollout_restart "yeeter-app"
  rollout_restart "yeeter-frontend"

  log "Completed build and deploy to k3s"
}

main "$@"
