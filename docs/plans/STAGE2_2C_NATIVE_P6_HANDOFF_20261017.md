# S2-2C — P3/P4/P5 → native P6 handoff implementation gate (2026-10-17)

## Exact scope
Frozen Hefei 2022 / 50×50×9 / 100 m / WGS84 UTM50N / 1 surface + 1 upper-air station (58424) / no precipitation / selected 143-hour C1 science only. Parent [#16](https://github.com/RRain001/CTEAS-next/issues/16), work item [#25](https://github.com/RRain001/CTEAS-next/issues/25). **This Draft is NOT P6 execution acceptance.**

## Actually inspected
`native_cpp/modules/p6_calmet/src/native_hourly_driver_main.cpp` uses `--case` and frozen relative paths:
- `geo/makegeo/geo.dat` — output of unchanged native P3, consuming the accepted native P1/P2 file-format adapters.
- `met/upperair/final/up_58424.dat` — P4 source station 58424 native READ62 selected writer output (Python source prep remains explicit).
- `met/surface/final/surf.dat` — P5 selected SMERGE native C++ output.
- `run/met/met.inp` — original locked case control card, *not* a model-generated meteorology field.
- `run/met/met.dat` — frozen original reference formerly required by P6D/P6E; this must NOT silently satisfy a genuinely independent P6 production-run requirement.

P6 provides `--p6e-source-builder` (GEO+deck metadata-only), `--p6f-writer`, and `--p6f-direct-hourly` experimental routing; its emitted `native_cpp_hourly_manifest.json` always reports `scientific_45_field_pass=false` (correctly no inferred physics PASS). A separate independent original-CALMET numerical gate remains mandatory.

## First landed code: read-only file integrity preflight
`native_cpp.orchestration.handoff_gate` checks explicit SHA256, sizes, frozen case labels, exact file roles and producer *assertions*, rejects symlinks/incorrect source and produces **INPUT_INTEGRITY_VERIFIED_ONLY** (never `ready_to_execute=true`). This is a pre-execution engineering gate, NOT trusted producer authentication, numerical acceptance, 143h run evidence or a means of bypassing P6's reference dependency. S2-2D also uses the same manifest schema with roles `p6_met` and `p7_control`; the `run/met/native_met.dat` staging name is a proposed future handoff, not an existing P6 output.

Unit invocation (Python + PyYAML, no P6 or G5 execution):

```bash
python3 -m unittest native_cpp.orchestration.tests.test_handoff_gate -v
```

## Required subsequent steps before PR Ready
1. Authentic P3/P4/P5 fresh output producer manifests with binary hashes, source/executable SHA, timestamp and effective-station semantics. Asserted `producer` string alone is insufficient to authenticate provenance; cross-check with independent log and actual launcher.
2. New scratch-only accepted-case staging adapter, explicit `case.yaml` profile check, station/time coverage validation and immutability of checked-in frozen reference.
3. Native P6 full-hour executable invocation (1h/6h/143h) via already reviewed source kernels, no original MET dependency in physics; fail closed otherwise. Enforce hour continuity and prior-hour COMP state.
4. Independently parse/check final CALMET file records, 45 field gates and genuine original same-input run at locked source; deterministic rerun and negative tests.
5. No G5, no `project/current`, no original/vendor redistribution, no general wind or wet physics claim.

Status: `S2_2C=IN_PROGRESS_CONTRACT_ONLY`; full numerical status `NOT_RUN` until authentic execution logs exist.
