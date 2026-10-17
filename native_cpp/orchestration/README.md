# S2-2A1 native case contract — read-only

This module implements **only** a bounded, JSON-producing `dry-run` contract for the frozen Hefei 2022 case. It is *not* a runner, general case planner or claim of numerical/scientific acceptance.

```bash
python -m native_cpp.orchestration.plan --case-yaml project/cases/hefei5km_2022_reference_case_20261011/case.yaml
python -m unittest discover -s native_cpp/orchestration/tests -p 'test_*.py' -v
```

The CLI **only reads the YAML** and prints a JSON object with immutable source-YAML SHA256, known grid/UTC/meteorology/point-source admission, and P1–P7 DAG. The returned status is always `DRY_RUN_ONLY_EXECUTION_BLOCKED` (`ready=false`, no legacy fallback, no files written). Invalid/out-of-scope cases yield exit code 2 and a blocked JSON result. No execution flag exists.

Strictly accepted *schema profile for planning*: exact 2022 Hefei case identity, 50x50x9 @ 100 m, UTM50N WGS84, locked UTC dates/station/source and known dry-deposition-free wet/chemistry switches. Case file SHA is reported, not claimed as independent source provenance. No implicit assumption about a 143-hour execution is made from the inclusive 2022-01-01..2022-01-06 labels.

This intentionally differs from `engine/gui_g5/pipeline.py` and neither imports nor modifies it. Existing C++/Fortran numerical kernels and P3 independent reference outputs remain unmodified. Next: build source-audited TERREL.DAT/LU.DAT writers and test their exact I/O contract before linking P3, then integrate P4/P5, P6/P7 under separately accepted stage permissions.

## S2-2C Draft — opted-in scoped P6 execution (experimental)

`plan.py` above remains exactly **read-only and BLOCKED**; do not conflate it with the new, separately invoked `run_p6.py` for isolated development. The new `handoff_gate.py` checks a separately authored manifest for the known native P3/P4/P5 file roles, byte lengths and SHA256, but producer names/source Git SHA are still self-assertions rather than independent provenance. A valid handoff is `INPUT_INTEGRITY_VERIFIED_ONLY`.

`run_p6.py` builds the existing C++ `cteas_p6_native_hourly_driver` command after an actual `case.yaml` scope check and byte-integrity preflight; it refuses staging that includes original `run/met/met.dat` and **only** chooses `--p6e-source-builder` metadata-only routing. It requires explicit paths to the existing native `p6d/p6e/cgamma/bridge` tools and, for 143h, `p6f-writer` + `--p6f-direct-hourly`. `--hours` is restricted to diagnostic checkpoints **1, 6 or 143**; no other grid/case/physics path is unlocked.

Without `--execute`, `run_p6.py` only prints a launch plan and does not create output. With `--execute`, it runs in a **new scratch** (no default publishing) and verifies the resulting existing C++ manifest and native MET hash. Even when the executable returns success, it emits `P6_EXECUTED_SCIENCE_NOT_ACCEPTED` and `scientific_acceptance=NOT_EVALUATED`. It cannot substitute for real original/native 45-field comparisons, time-axis verification, full P3/P4/P5 producer provenance or independent tests.

Example (only after a real scratch-staged 2022 case and source manifest exist; binaries must already be built):

```bash
python3 -m native_cpp.orchestration.run_p6 \
  --case-yaml /authorized/scratch/hefei5km_2022_reference_case_20261011/case.yaml \
  --manifest /authorized/scratch/s2c-p6-input-manifest.json \
  --work /authorized/scratch/p6-candidate-work \
  --hours 143 \
  --driver /path/to/cteas_p6_native_hourly_driver \
  --p6d /path/to/native_p6d --p6e /path/to/native_p6e \
  --cgamma /path/to/native_cgamma --bridge /path/to/native_bridge \
  --p6e-source-builder /path/to/native_p6e_source_builder \
  --p6f-writer /path/to/native_p6f_writer
# add --execute only when explicitly doing isolated numerical execution
```

The binary placeholders above are intentionally **not authoritative executable filenames**; use paths/target names inspected from the actual P6 CMake/Ubuntu build before any real run. No original Fortran fallback is configured. Current tests only mock subprocess execution:

```bash
python3 -m unittest discover -s native_cpp/orchestration/tests -p 'test_*.py' -v
```

The S2-2C Draft PR tracks real end-to-end integration and an independent 143h scientific gate. G5 `met`/`puff`/`all` remain blocked.
