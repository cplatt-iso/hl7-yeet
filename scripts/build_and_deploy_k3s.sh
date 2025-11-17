#!/usr/bin/env bash
set -euo pipefail

# Minimal helper script to build local images and load them into a k3s cluster.

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
K8S_NAMESPACE=${K8S_NAMESPACE:-yeeter}
KUBECTL_BIN=${KUBECTL:-kubectl}
SUDO_BIN=${SUDO_BIN:-sudo}

declare -a BUILD_COMPONENTS=()
declare -A SEEN_COMPONENTS=()

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
  local canonical_image="${image}"
  local -a save_refs=("${image}")
  local tarball

  # Ensure we also tag/save the fully qualified docker.io reference so that
  # containerd matches the tag Kubernetes resolves when pulling.
  if [[ "${canonical_image}" != */* ]]; then
    canonical_image="docker.io/library/${canonical_image}"
    if ! docker image inspect "${canonical_image}" >/dev/null 2>&1; then
      log "Tagging ${image} as ${canonical_image} for containerd import"
      docker tag "${image}" "${canonical_image}"
    fi
    # Include both references so the imported archive carries both tags.
    save_refs=("${canonical_image}" "${image}")
  fi

  tarball=$(mktemp "${TMPDIR:-/tmp}/k3s-image-XXXXXX.tar")

  log "Saving ${save_refs[*]} to ${tarball}";
  docker save "${save_refs[@]}" -o "${tarball}"

  if command -v k3s >/dev/null 2>&1; then
    log "Importing ${image} into local k3s (containerd)"
    ${SUDO_BIN} k3s ctr images import "${tarball}"
  elif command -v nerdctl >/dev/null 2>&1; then
    log "Importing ${image} via nerdctl"
    ${SUDO_BIN} nerdctl --namespace k8s.io load -i "${tarball}"
  else
    log "Neither k3s nor nerdctl found for image import"
    rm -f "${tarball}"
    exit 1
  fi

  if [[ -n "${EXTRA_IMPORT_NODES:-}" ]]; then
    for node in ${EXTRA_IMPORT_NODES}; do
      log "Importing ${image} on remote node ${node}"
      local remote_tmp="/tmp/$(basename "${tarball}")"
      scp "${tarball}" "${node}:${remote_tmp}"
      ssh "${node}" "${SUDO_BIN} k3s ctr images import '${remote_tmp}' && rm -f '${remote_tmp}'"
    done
  fi

  rm -f "${tarball}"
}

rollout_restart() {
  local deploy="$1"
  log "Restarting deployment ${deploy}"
  ${KUBECTL_BIN} -n "${K8S_NAMESPACE}" rollout restart "deployment/${deploy}"
  ${KUBECTL_BIN} -n "${K8S_NAMESPACE}" rollout status "deployment/${deploy}"
}

add_component() {
  local name="$1"
  local dockerfile="$2"
  local image="$3"
  local deployment="$4"

  if [[ -z "${name}" || -z "${dockerfile}" || -z "${image}" ]]; then
    return
  fi

  if [[ -n "${SEEN_COMPONENTS["${name}"]+_}" ]]; then
    return
  fi

  if [[ ! -f "${dockerfile}" ]]; then
    log "Skipping component '${name}' (Dockerfile missing: ${dockerfile})"
    return
  fi

  SEEN_COMPONENTS["${name}"]=1
  BUILD_COMPONENTS+=("${name}|${dockerfile}|${image}|${deployment}")
}

collect_components() {
  # Backend (primary API)
  add_component \
    backend \
    "${PROJECT_ROOT}/Dockerfile" \
    "${BACKEND_IMAGE:-docker.io/library/hl7-yeeter:latest}" \
    "${DEPLOYMENT_BACKEND:-yeeter-app}"

  # Discover all Dockerfile.* variants (frontend, worker, etc)
  for dockerfile in "${PROJECT_ROOT}"/Dockerfile.*; do
    [[ -f "${dockerfile}" ]] || continue

    local suffix
    suffix="${dockerfile##*.}"

    # Normalize component name (e.g., foo-bar)
    local component
    component="${suffix//./-}" 

  local env_key
  env_key="${component^^}"
  env_key="${env_key//-/_}"

  local env_image_var="IMAGE_${env_key}"
  local env_deploy_var="DEPLOYMENT_${env_key}"

    local default_image
    case "${component}" in
      frontend)
        default_image="docker.io/library/hl7-yeeter-frontend:latest"
        ;;
      worker)
        default_image="docker.io/library/hl7-yeeter-worker:latest"
        ;;
      backend)
        default_image="docker.io/library/hl7-yeeter:latest"
        ;;
      *)
        default_image="docker.io/library/hl7-yeeter-${component}:latest"
        ;;
    esac

    local image_override="${!env_image_var:-}" 
    local image="${image_override:-${default_image}}"

    local default_deployment
    case "${component}" in
      frontend)
        default_deployment="yeeter-frontend"
        ;;
      worker)
        default_deployment="yeeter-worker"
        ;;
      backend)
        default_deployment="yeeter-app"
        ;;
      *)
        default_deployment="yeeter-${component//_/-}"
        ;;
    esac

    local deployment_override="${!env_deploy_var:-}"
    local deployment="${deployment_override:-${default_deployment}}"

    add_component "${component}" "${dockerfile}" "${image}" "${deployment}"
  done
}

main() {
  require_cmd docker
  require_cmd ${KUBECTL_BIN}
  if [[ -n "${EXTRA_IMPORT_NODES:-}" ]]; then
    require_cmd ssh
    require_cmd scp
  fi

  collect_components

  if [[ ${#BUILD_COMPONENTS[@]} -eq 0 ]]; then
    log "No components discovered. Nothing to build."
    return
  fi

  declare -a deployments_to_restart=()

  for entry in "${BUILD_COMPONENTS[@]}"; do
    IFS='|' read -r name dockerfile image deployment <<<"${entry}"

    log "Building ${name} image ${image} (Dockerfile: ${dockerfile##*/})"
    docker build -t "${image}" -f "${dockerfile}" "${PROJECT_ROOT}"

    import_image "${image}"

    if [[ -n "${deployment}" ]]; then
      deployments_to_restart+=("${deployment}")
    fi
  done

  # Restart unique deployments once
  declare -A restarted=()
  for deployment in "${deployments_to_restart[@]}"; do
    if [[ -n "${restarted["${deployment}"]+_}" ]]; then
      continue
    fi
    restarted["${deployment}"]=1
    rollout_restart "${deployment}"
  done

  log "Completed build and deploy to k3s"
}

main "$@"
