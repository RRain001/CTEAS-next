# CTEAS private Linux self-hosted CI migration — 2026-10-11

Scope: workflow scheduler/toolchain only, no CALMET/CALPUFF physics, no vendor changes. Target runner labels `[self-hosted, Linux, X64]`, tested owner runner `lhy-desktop`. Do not use the runner NAME as a label.

## Invariants

- All existing 13 P1/P2/P6 workflow jobs switch from billable `ubuntu-latest` or `ubuntu-22.04` to private self-hosted Linux/X64. The independent P6D INTER2 PR #16 migrates its own additional workflow (14th) separately.
- Shared read-only composite action `.github/actions/cteas-linux-toolchain/action.yml` enforces `g++ >= 12` (real `std::chrono::sys_seconds` compile), `gfortran >= 11`, CMake and Python. `CXX` exported via job-local `GITHUB_ENV` and `gfortran` shim via `GITHUB_PATH`; no global system alternatives or user dotfile modifications.
- Fortran references never change their original scientific source. Installed CMake build directories in /tmp on persistent runners may preserve stale compilers; run CMake with new job-local build directories if investigating a discrepancy.
- Reject external fork PR jobs on self-hosted runner. Shared private runner must be secured separately by administrator (avoid repo-external PR execution and secret exposure).
- Concurrency is `github.workflow` plus PR number (or branch ref) with `cancel-in-progress: true`. Two different agent PRs do not cancel each other. Existing job commands and original parity numerical tolerances remain intact except dependency preflight/installation.
- Fine-grained `pull_request.paths` trigger routine, **affected** checks only. For reproducible full-regression-before-merge, intentionally add/update `docs/reconstruction_cpp/CI_FULL_REGRESSION_REQUEST.md` **in a dedicated PR commit**. That path explicitly triggers all 13 migrated jobs and, after PR #16 merges, its INTER2 CI must also include it. Do not claim that a green smoke alone proves full P6 readiness. For full 2022 integration run P6B as part of the same gate.
- Workflow-only CI migration PR triggers single smoke job and the two inexpensive C++ contract jobs; the large 2022 full baseline is not triggered merely by altering YAML.
- P6B venv is job-scoped to avoid globally installing Python packages on a research server; GDAL package installation is attempted noninteractively only when required. If privileges/venv packages are missing, stop and request host administrator action.
- Private repository remains private. P6 stage branch and its PR #8 remain isolated from main; P6E PR #11 remains untouched.

## Acceptance gates

1. INTER2 PR #16 independent original CALMET numerical parity must pass **before** merging it.
2. This CI migration PR may merge to the P6 development base only after `cteas-selfhosted-smoke.yml` successfully builds C++20, literal Fortran and runs all current P6 CTests; no unsupported success claims.
3. Trigger an explicit full regression request before a P6 stage acceptance claim. Preserve original-source artifacts, exceptions, JUnit/CTest logs and any real 2022 deficiencies separately.

## Independent self-hosted acceptance (2026-10-11)

CI migration PR head `742ee9411d70c7f51c0409fa81c26b5c5ef73277` received actual self-hosted execution:
- [Runner smoke #38121624741](https://github.com/RRain001/CTEAS/actions/runs/38121624741) **SUCCESS**: HTTPS preflight, private GitHub checkout, shared GCC12+ / gfortran11+ composite selection, literal Fortran compilation, strict P6 C++20 compilation and all P6 CTests passed.
- [P6A C++ contracts #38121624736](https://github.com/RRain001/CTEAS/actions/runs/38121624736) **SUCCESS**.
- [C++ input contracts #38121624744](https://github.com/RRain001/CTEAS/actions/runs/38121624744) **SUCCESS**: C++ input compile/tests, GDAL inspection and immutable crop hashes.

This acceptance **only** validates the self-hosted execution substrate, dependency bootstrap and quick smoke. Changed per-module P6C/P6D work, 2022 143h P6B, and full-rerun gate must still run when their paths/explicit sentinel are exercised. One green smoke is not an end-to-end CALMET P6 PASS.
