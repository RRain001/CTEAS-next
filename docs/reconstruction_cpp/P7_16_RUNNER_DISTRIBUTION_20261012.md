# P7 — all 13 managed runners are eligible (2026-10-12)

## Root cause: GitHub Actions label mismatch

Runners `lhy-desktop-4` through `lhy-desktop-16` were created intentionally **without `self-hosted`**. They have `cteas-managed`, `Linux`, `X64`, plus `cteas-light` (4–11), `cteas-compute` (12–14) or `cteas-reserve` (15–16), and unique labels `cteas-r04` … `cteas-r16`. Thus the older P7 `runs-on: [self-hosted, Linux, X64]` **could not dispatch jobs to 13 of the 16 registered runner instances**. Raising `max-parallel` from 4 to 16 without changing labels does not solve scheduling.

## Placement of 14 independent source parity shards

| Lane | Required runner label / capacity | Previously validated source tests |
| --- | --- | --- |
| `release-inject` | `cteas-r04` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `step-bookkeeping` | `cteas-r05` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `advection` | `cteas-r06` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `dispersion` | `cteas-r07` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `sigma-update` | `cteas-r08` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `terrain-constraints` | `cteas-r09` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `terrain-relief` | `cteas-r10` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `valley-width` | `cteas-r11` (light) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `plume-rise` | `cteas-r12` (compute) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `receptor-sampling` | `cteas-r13` (compute) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `vertical-coupling` | `cteas-r14` (compute) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `ctsg-kernels` | `cteas-r15` (reserve) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `dry-removal` | `cteas-r16` (reserve) | Mandatory CTest registration + REAL*4 / original Fortran parity |
| `wind-step-output` | `cteas-light` (overflow) | Mandatory CTest registration + REAL*4 / original Fortran parity |

The first thirteen lanes have **unique labels**, ensuring the GitHub scheduler cannot concentrate them on just a few registered workers; the fourteenth `wind-step-output` lane uses the light overflow pool and starts on the next available light worker. The full P7 case continues using its existing `lhy-desktop-3` workflow; P6 runners `lhy-desktop` and `lhy-desktop-2` are not touched by the managed P7 fan-out.

Two independent jobs route to named pools: precision/type audit → `cteas-light`; original COMP order + first-hour native motion and original output structure → `cteas-compute`. The new **6h/143h full DGM regeneration** uses `cteas-reserve` and no longer needs another job to complete before scheduling. All routing is constrained by `cteas-managed`, **not** `self-hosted`.

Hardware observed/provided: two Xeon Platinum 8273CL processors, 56 physical cores / 112 hardware threads, ~125 GiB RAM, two NUMA nodes. The earlier per-host **four-task flock lock was removed**: 14 matrix jobs compile `--parallel 1` and run source tests individually; 56 real cores are ample for this conservative maximum. Every job prints its `RUNNER_NAME` and host. `strategy.max-parallel=16` for source lanes remains. Monitor actual online/idle and concurrent job evidence: **queued 17 jobs** ≠ **17 tasks executing**, and unique runner labels may queue behind P6 if already assigned.

All 33 original source-parity tests still require explicit CTest registration and individual success; no test or module was omitted. The extra 6h/143h validation remains oracle-fed; **full native CALPUFF COMP/lifecycle, WROUT1 and puff.con concentration parity are still unaccepted**. PR #41 remains Draft.
