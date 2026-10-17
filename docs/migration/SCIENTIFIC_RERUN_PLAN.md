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

## Option coverage and input readiness — selected reconstruction only

**Classification:** `ACCEPTED_SCOPED` is limited to the exact frozen scientific
deck(s) already evaluated in upstream CTEAS. `IMPLEMENTED_PARTIAL` means some
code and scoped tests exist but general execution is not validated.
`UNACCEPTED` covers both branches not implemented and branches whose physical
equivalence remains unproven; it must **not** be interpreted as a definitive
source-level inventory of absent routines. Nothing here upgrades the migrated
repository's scientific status.

| Component | Scope with prior evidence (source CTEAS) | Unaccepted generalization / present boundary |
|---|---|---|
| P1–P3 preprocessors | Scoped 50×50, 100 m terrain/GEN/MAKEGEO reference comparisons; no-snow P3 case | Other algorithms, domains, terrain/land-use configurations, missing-data and geospatial choices are not automatically covered. |
| P4 READ62 | Selected sounding format and reference-year original-vs-native tests | Other input formats, arbitrary station/year scheduling and G5 generic publication are not accepted. |
| P5 SMERGE | Selected data-preparation and SURF input contracts / source-derived tests | Not a complete all-option original SMERGE replacement or a general validated precipitation adapter. |
| P6 CALMET | Reference-case 143h single-station C1 and selected 2024 2-surface/2-upper station C2 original-vs-native comparisons; enabled terrain/diagnostic wind/thermal branches are case-specific | General station/layout/time combinations, CALMET optional wind/terrain/overwater/prognostic configurations, all option settings, and verified precipitation fields are **UNACCEPTED**. |
| P7 CALPUFF | Selected continuous single-source Hefei 2022 143h, `METFM=1, MCTADJ=2, MDISP=3, MDRY=1, MTRANS=1, MWET=0`, with original CALPUFF comparison; selected C2 meteorology/solver arms | No all-option equivalence. Other source/dispersion/terrain/plume-rise/deposition settings, multisource, and arbitrary receptor configurations require separate validation. `MWET>0` is **UNACCEPTED**; the accepted reference is dry-only. |
| G5 GUI pipeline | GUI boot/isolated native dispatch and software-stage contracts | General P6 `met`, P7 `puff`, and `all` **fail closed**; preprocessing/upper-air generic execution also remains restricted. |

**Precipitation/wet-removal blocker:** The selected upstream CALMET case records
`NPSTA=0`, precipitation observations/code fields do not provide a qualified
hourly precipitation series, and the accepted CALPUFF deck sets `MWET=0`.
There is currently **no validated project-specific precipitation-station input
template/format and parser→CALMET→CALPUFF provenance chain** for wet
deposition. A formal wet-scavenging work package must first pin the original
CALMET/CALPUFF input contract (station/header/record/time-zone/time-step units,
missing codes and spatial/temporal alignment), construct authentic rain/no-rain
test fixtures, and compare `MWET>0` reference-vs-native physics, inventories
and deposition fields. Never fabricate rainfall or infer wet-deposition support
from unrelated P6F MET.DAT binary-reader tests.

Source scope: `docs/reconstruction_cpp/P7_PHASE_STATUS_20261015.md`,
`P7_C1_C2_CALMET_TO_CALPUFF_INTEGRATION_20261015.md`,
`P1_P7_INTEGRATION_REHEARSAL_20261016.md` and prior P6 audit records.
Full migrated C1/C2 143h reruns remain **NOT_RUN** here.

## GitHub Actions manual 143h scientific rerun entrypoints — NOT_RUN

Two new proposed workflows execute on **Ubuntu 22.04 Linux x86-64 hosted
runners**, not the user's MacBook or an assumed Ubuntu workstation:

- `.github/workflows/science-c1-143h.yml` — fresh current-head C1 native P6
  143h MET.DAT, four original/native CALPUFF A/B/C/D 143h arms with original
  Fortran DGM, strict H-3 IEEE REAL4 same-MET A/B and C/D
  357,500/357,500, and independent P6 strict weather comparator. The
  2022 **original CALMET meteorology remains the pinned SHA-checked frozen
  reference**: this does **not** mean original 2022 Fortran CALMET is
  freshly rerun. Native P6 and all CALPUFF A/B/C/D solver outputs are
  independently regenerated. Flag this residual original-CALMET rerun
  separately rather than marking a complete original-P6 fresh comparison.
- `.github/workflows/science-c2-143h.yml` — fresh native and unchanged
  original Fortran CALMET, true 2024 2SS/2US 143h MET.DAT, frozen
  strict 6,435-field meteorological gate; fresh original and native
  CALPUFF A/B/C/D 143h 12×12 H-3 arrays, strict 20,592/20,592
  A/B and C/D REAL4 equivalence and independent different-MET
  concentration sensitivity. Synthetic-but-original-format 2024 case is
  *not* field-observed 2024 Hefei meteorology.

Both workflows are `workflow_dispatch` **only**. Their source of truth is the
actual triggering CTEAS-next `main` SHA; P6 and P7 must come from that same
checkout. A second **ephemeral** checkout at the exact old `RRain001/CTEAS`
source SHA `dfad99a78ed84d655e21411c9d25eb0d2583bf13` restores the
excluded original Fortran/vendor/terrain assets into only the runner's local
ignored paths through `configure_external_assets.py`; every manifest hash
is checked. No vendor code or restricted data is committed or included in
workflow artifacts. Only selected derived JSON, hashes and runtime traces
are uploaded, retained 14 days. Do not upload whole scientific workspace.

### Required operating and acceptance procedure

1. Review workflow source, then from **Actions → C1 143h** on `main`,
   click **Run workflow** (no automatic run on push, PR or merge).
2. Inspect the job, verify actual test input hashes, GHA run SHA, no
   original-MET oracle injected into native P6/P7 solver state, nonzero
   plumes, 143/143 completed hours, A/B and C/D REAL4 bit identities.
   If C1 fails or is blocked, stop and audit first scientific difference.
3. Next manually run **Actions → C2 143h** on the same `main` SHA.
   Require the original and native P6 fields and all four independently
   executed P7 arms; no tolerance relaxation, no synthetic empty-plume pass.
4. Record run URL, job and artifact IDs, toolchain, raw input and output
   SHA256, actual `main` SHA, evidence locations and the **original-C1
   CALMET-not-fresh** limitation in the new acceptance report. Do not
   upgrade scientific status from workflow existence or historical PASS.
5. A workflow cannot be considered verified until its own manual execution
   completes successfully and a reviewer confirms the logs and artifacts.
   Existing Ubuntu/Docker portable tests prove software/build behavior,
   not the new scientific 143h claims.

**Current migration baseline remains `C1=NOT_RUN; C2=NOT_RUN`** until those
workflows have actually been executed in CTEAS-next and reviewed. In
particular `MWET>0`/wet-deposition and arbitrary CALMET/CALPUFF options
remain unaccepted.

## Full C1 rerun — NOT_RUN

1. Restore and hash-check the local vendor package and CGIAR crop using
   `scripts/migration/configure_external_assets.py`.
2. Use the original command sequence preserved byte-for-byte in
   `historical-workflows/integration-p1-p7-2022-c1-143h.yml.disabled`:
   audit source statements, regenerate the original 143h DGM oracle with
   `native_cpp/modules/p7_calpuff/reference/dgm_p7_advection_2022/original_calcpf_receiver_oracle.py`,
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
