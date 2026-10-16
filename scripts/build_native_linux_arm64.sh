#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="cteas-fortran:debian12-arm64"
TARGETS="${*:-}"

docker build --platform linux/arm64 -t "$IMAGE_NAME" -f "$ROOT_DIR/docker/fortran/Dockerfile" "$ROOT_DIR"

docker run --rm \
  --platform linux/arm64 \
  -e TARGETS="$TARGETS" \
  -v "$ROOT_DIR:/work" \
  -w /work \
  "$IMAGE_NAME" \
  bash -lc '
set -euo pipefail
mkdir -p bin/linux-arm64
COMMON_FFLAGS="-std=legacy -ffixed-line-length-none -fno-automatic -fno-align-commons -fallow-argument-mismatch -O0"
LEGACY72_FFLAGS="-std=legacy -ffixed-line-length-72 -fno-automatic -fno-align-commons -fallow-argument-mismatch -O0"
PUFF_FFLAGS="-std=legacy -ffixed-line-length-72 -fno-automatic -fno-align-commons -fallow-argument-mismatch -fdec-format-defaults -O0"
read -r -a REQUESTED <<< "${TARGETS:-}"

should_build() {
  local out="$1"
  if [ "${#REQUESTED[@]}" -eq 0 ]; then
    return 0
  fi
  local target
  for target in "${REQUESTED[@]}"; do
    if [ "$target" = "$out" ]; then
      return 0
    fi
  done
  return 1
}

build_with_flags() {
  local out="$1"
  local flags="$2"
  shift 2
  if ! should_build "$out"; then
    return 0
  fi
  echo "[BUILD] $out"
  gfortran $flags "$@" -o "bin/linux-arm64/${out}.x"
}

build_with_flags terrel "$COMMON_FFLAGS" \
  engine/vendor/src/TERREL_v7.0.0_L141010/TERREL.FOR

build_with_flags ctgproc "$LEGACY72_FFLAGS" \
  engine/vendor/src/CTGPROC_v7.0.0_L150211/ctgproc.for

build_with_flags makegeo "$LEGACY72_FFLAGS" \
  engine/vendor/src/MAKEGEO_V3.2_L110401/makegeo.for

build_with_flags read62 "$LEGACY72_FFLAGS" \
  engine/vendor/src/READ62_v5.661_L110225/read62.for

build_with_flags smerge "$LEGACY72_FFLAGS" \
  engine/vendor/src/SMERGE_v5.7.0_L121203/smerge.for

build_with_flags met "$COMMON_FFLAGS" \
  engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for

build_with_flags puff "$PUFF_FFLAGS" \
  engine/vendor/src/CALPUFF_v7.2.1_L150618/modules.for \
  engine/vendor/src/CALPUFF_v7.2.1_L150618/calpuff.for

if should_build terrel || should_build ctgproc || should_build makegeo || should_build read62 || should_build smerge || should_build met || should_build puff; then
  chmod +x bin/linux-arm64/*.x
  file bin/linux-arm64/*.x
fi
'
