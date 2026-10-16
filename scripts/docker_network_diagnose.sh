#!/usr/bin/env bash
set -euo pipefail

PROXY_HOST="${PROXY_HOST:-host.docker.internal}"
PROXY_PORT="${PROXY_PORT:-7897}"
PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"
AMD64_IMAGE="${AMD64_IMAGE:-debian:12}"
ARM64_IMAGE="${ARM64_IMAGE:-debian:12}"
PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.12-slim-bookworm}"

run_probe() {
  local title="$1"
  shift
  echo "=== ${title} ==="
  "$@" || true
  echo
}

echo "=== Docker version ==="
docker --version
docker buildx version || true
echo

echo "=== Local images ==="
docker images || true
echo

run_probe "Docker Hub image pull" \
  docker pull "${PYTHON_IMAGE}"

run_probe "Platform check: linux/arm64" \
  docker run --rm --platform linux/arm64 "${ARM64_IMAGE}" uname -m

run_probe "Platform check: linux/amd64" \
  docker run --rm --platform linux/amd64 "${AMD64_IMAGE}" uname -m

run_probe "Container network without proxy" \
  docker run --rm --platform linux/amd64 "${AMD64_IMAGE}" bash -lc '
    set -x
    apt-get update
  '

run_probe "Container proxy port reachability" \
  docker run --rm --platform linux/amd64 "${AMD64_IMAGE}" bash -lc "
    set -x
    bash -lc 'exec 3<>/dev/tcp/${PROXY_HOST}/${PROXY_PORT}'
  "

run_probe "Container network with proxy" \
  docker run --rm --platform linux/amd64 \
    -e HTTP_PROXY="${PROXY_URL}" \
    -e HTTPS_PROXY="${PROXY_URL}" \
    -e ALL_PROXY="${PROXY_URL}" \
    -e http_proxy="${PROXY_URL}" \
    -e https_proxy="${PROXY_URL}" \
    -e all_proxy="${PROXY_URL}" \
    "${AMD64_IMAGE}" bash -lc '
      set -x
      apt-get update
    '

run_probe "Python pip source without proxy" \
  docker run --rm --platform linux/amd64 "${PYTHON_IMAGE}" bash -lc '
    set -x
    python -m pip download --no-deps -d /tmp/pip-probe pyyaml
  '

run_probe "Python pip source with proxy" \
  docker run --rm --platform linux/amd64 \
    -e HTTP_PROXY="${PROXY_URL}" \
    -e HTTPS_PROXY="${PROXY_URL}" \
    -e ALL_PROXY="${PROXY_URL}" \
    -e http_proxy="${PROXY_URL}" \
    -e https_proxy="${PROXY_URL}" \
    -e all_proxy="${PROXY_URL}" \
    "${PYTHON_IMAGE}" bash -lc '
      set -x
      python -m pip download --no-deps -d /tmp/pip-probe pyyaml
    '

echo "=== Recommendation ==="
echo "If proxy test succeeds but no-proxy fails, run Docker scripts with:"
echo "PROXY_PORT=${PROXY_PORT} USE_DOCKER_PROXY=1 ./scripts/test_linux_x86_64_runtime_in_docker.sh"
