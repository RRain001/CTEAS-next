# syntax=docker/dockerfile:1
# P1-P7 bounded C++20 research subset. No vendor original source/terrain.
ARG BASE_IMAGE=python:3.11-slim-bookworm

# This stage is shared by both paths and compiles exactly once for each build
# cache key. It intentionally performs NO CTest/Python/G5 regression execution.
FROM ${BASE_IMAGE} AS builder
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CXX=/usr/bin/g++-12 \
    FC=/usr/bin/gfortran-12
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      ca-certificates cmake g++-12 gfortran-12 make libgdal-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN python scripts/migration/validate_ubuntu.py \
      --out /tmp/cteas-software --jobs 2 --portable --build-only

# Development / CI gate: reuse builder outputs, run portable CTest + Python + G5.
# Unlike runtime, this target installs test-only GUI/Python dependencies.
FROM builder AS verification
ENV QT_QPA_PLATFORM=offscreen
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      libegl1 libopengl0 libgl1 libxkbcommon-x11-0 \
      libxcb-cursor0 libdbus-1-3 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# ARM64 does not offer upstream PySide6==6.11.0 on PyPI. This explicit
# Docker-verification-only substitute does not change the upstream requirements.
RUN set -eux; \
    if [ "$(dpkg --print-architecture)" = "arm64" ]; then \
      sed 's/^PySide6==6[.]11[.]0$/PySide6==6.8.0.2/' requirements.txt > /tmp/requirements-container.txt; \
      grep -qx 'PySide6==6.8.0.2' /tmp/requirements-container.txt; \
    else \
      cp requirements.txt /tmp/requirements-container.txt; \
    fi; \
    python -m pip install --no-cache-dir -r /tmp/requirements-container.txt; \
    python -m pip show PySide6 | grep '^Version:'
RUN sh scripts/container/verify.sh

FROM ${BASE_IMAGE} AS runtime
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision="${SOURCE_REVISION}" \
      org.opencontainers.image.title="CTEAS-next scoped C++20 runtime"
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/cteas/bin:${PATH}
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      ca-certificates libgdal32 libssl3 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
# Explicit, scoped standalone CLIs; intentionally no reference fixtures, GUI
# runtime, original Fortran binaries, or automatic all-stages orchestrator.
COPY --from=builder /tmp/cteas-software/build-inputs/cteas_p2_gen_fraction /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-inputs/cteas_p2_glc_raw /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-inputs/cteas_p2_glcc_raw /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p1/cteas_p1_terrain /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p3/cteas_p3_makegeo /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p4/cteas_p4_read62 /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p5/cteas_p5_smerge /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p6/cteas_p6_realcase_wind_field /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p6/cteas_p6_native_hourly_driver /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p6f/cteas_p6f_calmet_dat21_writer /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p7/cteas_p7_calmet21_inspect /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p7/cteas_p7_native_met_hours /opt/cteas/bin/
COPY --from=builder /tmp/cteas-software/build-p7/cteas_p7_2022_case_ledger /opt/cteas/bin/
COPY docker/cpp/entrypoint.sh /usr/local/bin/cteas-entrypoint
RUN chmod 0755 /usr/local/bin/cteas-entrypoint \
    && mkdir -p /cases /results /work \
    && chown -R 10001:10001 /cases /results /work
USER 10001:10001
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/cteas-entrypoint"]
