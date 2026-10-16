# CTEAS-next

Clean-history successor workspace for the CTEAS P1–P7 C++20 reconstruction.

This repository is **private** and contains the first tracked-file P1–P7 migration for review. The original research repository remains at [RRain001/CTEAS](https://github.com/RRain001/CTEAS), with its full Git history, pull requests, original scientific evidence, and archival branches preserved.

## Source provenance

- Source repository: `RRain001/CTEAS`
- Starting reviewed integration commit: `dfad99a78ed84d655e21411c9d25eb0d2583bf13` (merged PR [#75](https://github.com/RRain001/CTEAS/pull/75)).
- The Ubuntu implementer must fetch `origin/main`, record the actual upstream SHA, and explicitly report any difference from the above reference before migration.
- The first code migration must use a **tracked-file export of the exact source revision**, not a copy of the old `.git` history or a local working tree containing untracked files.

## Scientific scope

A clean Git history **does not** recertify physics. Existing reference-case P6/P7 143-hour acceptance and its limitations must remain explicit. Generic P6/P7 runs, arbitrary sites and periods, and full G5 P1–P7 native execution are not automatically accepted. No silent fallback to old Fortran in a new claimed-native execution path.

## Working agreement

- ChatGPT: plan, independently review code/evidence, report decisions in pull requests.
- Ubuntu Codex: implement, run real builds/tests, push branches, post logs and blockers on its PR.
- Initial migration: use a feature branch and **Draft PR** against `main`; do not directly overwrite this bootstrap baseline.
- Do not copy secrets, temporary outputs, caches, virtual environments, compiled binaries, or `.git`.
- Review font redistribution rights, third-party vendor licensing, and test data provenance before copying bundled assets into the new repository; retain required verification dependencies with explicit notices, and report any exclusion that breaks a test.
- Do not modify accepted physics or numerical thresholds as part of history cleanup. Preserve the old CTEAS repository intact.

See the initial migration issue for the staged execution contract.

## Ubuntu build and software checks

Prerequisites: Ubuntu 22.04 x86_64, CMake >=3.20, GCC >=12 (C++20),
GFortran >=11 for original-source parity tests, GDAL development headers,
and Python >=3.11. The host default CXX/FC may point to older MPI compilers;
select the tools explicitly. No Docker is needed for this C++ build.

```bash
sudo apt-get install cmake g++-12 gfortran-11 libgdal-dev
./bootstrap_venv.sh
.venv/bin/python scripts/migration/verify_snapshot.py
CXX=/usr/bin/g++-12 FC=/usr/bin/gfortran-11 .venv/bin/python \
  scripts/migration/validate_ubuntu.py --out /tmp/cteas-next-validation --jobs 2
.venv/bin/python -m unittest discover -s engine/gui_g5/tests -p 'test_*.py' -v
QT_QPA_PLATFORM=offscreen .venv/bin/python -m engine.gui_g5
```

The validation script builds **nine separate upstream CMake projects**;
`cmake -S native_cpp` alone builds only input contracts, not all P1–P7.
It retains Debug assertions, upstream warnings and numerical tolerances.
The full local software regression needs the external assets restored first:

```bash
.venv/bin/python scripts/migration/configure_external_assets.py --source-repo /path/to/authorized/CTEAS
.venv/bin/python scripts/migration/configure_external_assets.py --check
```

For a clean checkout without those assets, add `--portable` to the validation
command. That builds every native target and runs an explicitly enumerated
software subset; other registered tests are recorded as NOT_RUN. New CI uses
this mode and never fetches or publishes excluded third-party assets.
Its two excluded historical P7 receptor diagnostics and the complete C1/C2
143h scientific workflows are **NOT_RUN** by this software-check command.
See [migration evidence and limitations](docs/migration/INITIAL_MIGRATION.md),
[asset rights and provenance](docs/migration/THIRD_PARTY_ASSETS.md), and
[the full scientific rerun plan](docs/migration/SCIENTIFIC_RERUN_PLAN.md).

`project/cases/` contains **frozen tracked reference fixtures**, including
original model results used as immutable test oracles. It is not a publication
of the old machine's untracked case workspace. These bytes remain in their
upstream paths because CMake and scientific harnesses refer to them directly;
new case outputs stay ignored. Large full terrain datasets and native runtime
executables are not included. Original vendor Fortran and CGIAR terrain crops are local external dependencies;
they are excluded from Git and verified against the source manifest. Desktop
font assets are omitted pending license documentation; Qt uses system fonts.

The independent G5 launcher is `./cteas-g5gui`. Its generic P6 (`met`), P7
(`puff`) and `all` stages remain fail-closed. Only the documented reference
cases have prior 143h scientific acceptance; migration does not extend it to
arbitrary grids, stations, sites, or a continuous year. Historical acceptance
documents retain their original dates and conclusions and are not new test results.
