# Scientific validation boundaries and full rerun plan

This migration does not change algorithms, numeric tolerances or scientific
acceptance. Software CTest success and frozen-file identity do not recertify the
complete P6/P7 reference-case pipeline. Historical forensic results carrying
`SCIENTIFIC_ACCEPTANCE=NOT_PASS` retain that meaning.

## Prior evidence, not this migration's test results

- Source: [CTEAS PR #75](https://github.com/RRain001/CTEAS/pull/75), commit
  `dfad99a78ed84d655e21411c9d25eb0d2583bf13`.
- C1: 2022 Hefei single-station original meteorology, strict 143h P7 comparison,
  [run 38846349292](https://github.com/RRain001/CTEAS/actions/runs/38846349292).
- C2: 2024 multi-station 2SS/2US, 12×12×9 at 10 km, strict four-arm 143h
  meteorology/puff comparisons,
  [run 38846032814](https://github.com/RRain001/CTEAS/actions/runs/38846032814).
- Detailed dimensions, field gates and tolerances remain in
  `docs/reconstruction_cpp/P1_P7_INTEGRATION_REHEARSAL_20261016.md` and
  `P7_C1_C2_CALMET_TO_CALPUFF_INTEGRATION_20261015.md`.

The above historical runs are **NOT_RUN in this migration**. Small CTest tests
with “143h” or “8784h” in their name may validate clocks, fixtures or scoped
contracts; their software PASS must not be relabeled as a full scientific run.
G5 still rejects generic `met` (P6), `puff` (P7), and `all`, and retains its
existing restrictions on generic preprocessing/upper-air orchestration. There
is no acceptance for arbitrary grids, sites, station sets or continuous years.

## Full C1 rerun — NOT_RUN

1. Restore and hash-check the local vendor package and CGIAR crop using
   `scripts/migration/configure_external_assets.py`.
2. Use the original command sequence preserved byte-for-byte in
   `historical-workflows/integration-p1-p7-2022-c1-143h.yml.disabled`:
   audit source statements, regenerate the original 143h DGM oracle with
   `native_cpp/modules/p7_calpuff/reference/original_precision_prepare.py`,
   rebuild the P7 native receptor target, then execute the full 143h native
   replay against the pinned 2022 `met.dat`, `puff.inp` and `puff.con`.
3. Preserve all preexisting strict H-3 comparison gates, field checks,
   tolerances, hour counts and intermediate provenance. The workflow's exact
   compiler flags are authoritative; do not substitute a generic optimized
   build or historical forensic-only success.
4. Write new logs/reports outside the checkout. Record current execution SHA,
   machine/toolchain, fixture hashes, original and native results separately.

This is a planned scientific rerun, not a claim the above commands ran here.

## Full C2 rerun — NOT_RUN

Use the source command sequences in
`historical-workflows/integration-p1-p7-143h-science.yml.disabled` and
`historical-workflows/p7-c2-pr63-two-meteorologies-vendor-science.yml.disabled`.
Restore pinned vendor assets; regenerate or retrieve the precisely documented
2024 multistation inputs and original/native meteorologies with their provenance;
execute all four meteorology/solver arms for 143h and retain the existing
6,435-field meteorology gate and strict puff gates. Some old workflows retrieve
artifacts from historical CTEAS run IDs/branches: those are historical **inputs**
that must be explicitly frozen and linked in a future run, never silently
replaced with current CTEAS-next `main` or assumed present in this checkout.
Historical workflow files are archived references and are not enabled CI here.

## Other exclusions

The initial local CTest command explicitly excludes the historical first-hour
H-3 receptor diagnostic and six-hour COMP precision diagnostic. Both are
**NOT_RUN**, not renewed scientific acceptance. Every other registered local
CTest result (including any timeout/failure) is recorded in the migration report.
New portable CI uses an explicit software-test list; tests outside it are
NOT_RUN in that CI mode. It neither restores nor uploads private vendor/terrain
assets. Re-enabling full science automation requires an explicit authorized
asset/artifact provision and a new reviewed workflow; no numerical code changes
are required by this packaging migration.
