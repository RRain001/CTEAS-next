# S4-R1c9i — real NOAA hour-two full G14 negative transaction

## Purpose

The preceding R1c9h fixed global WATER ZICONV lifetime and obtained
313,650/313,650 original-vs-native second-hour field comparisons within
the frozen tolerance. That does not mean hour-two state or clocks may
be published. This change exercises the existing scheduler-owned
advance_with_fresh_physics transaction with a newly owned
second-hour 17-stage G26A/G26B executor, then intentionally rejects its
P6F precommit.

## Authority and scope

- Frozen selected NOAA case: 2022-06-01 01:00–07:00 UTC, 82x85x9,
  2 surface stations, 1 upper station, 63 WATER cells.
- Original Fortran authority: CALMET 6.5.0 local read-only
  /home/lhy/CTEAS, exact-source hashes in R1c9h report.
- The actor consumes only genuine native P1–P5 inputs and G14 hour-one
  committed ZI/ZICONV/DPTT and published AA/BB/CGAMMA.
- It executes all 17 native stages, checks P6F candidate against a
  separately staged source-native second-hour result, then throws
  G65_EXPECTED_SECOND_HOUR_PRECOMMIT_ROLLBACK.
- G14 must remain at exactly one committed hour, with bitwise identical
  previous ZI/ZICONV/DPTT and unchanged published station clocks.
  Postcommit callback must not execute. The exception is expected only
  after P6F and clock preflight; all other errors fail closed.

## Acceptance boundary

This is a negative transaction regression, not a positive second-hour
commit. The external original 45-field comparison remains a separately
executed scoped audit and is not fed into the native actor. A subsequent
positive hour-two commit must require reviewed original same-input
science and a transactional clock publication gate. Hour 3–6 and
general-purpose P6/P7 remain NOT_ACCEPTED. No threshold changes or
restricted assets are included.

## Evidence

- Native C++ compile/link: PASS, Ubuntu GCC 12, CMake Release. Binary SHA256 bc67ea45b5773ab467480614e04d40720883ec2c99708ea0e240c43c01520c55.
- Actual NOAA full-17-stage forced rollback: PASS_ROLLBACK_ONLY, real source inputs, exit 0, source-native P6F candidate equality, injection only after stage16/clock preflight. Unoptimized host build also exited 0, but is not the release evidence.
- Local stdout/stderr: /home/lhy/dev/CTEAS-next/local-science/s4-r1c9i-rollback-20261024/release.stdout.log and release.stderr.log; actual source commit SHA to be recorded at commit. Inputs are the same fixed SHA as R1c9h.
- Docker full on this NEW commit: NOT_RUN
- Independent scientific review: NOT_RUN
