# P7 CALPUFF 7.2.1 — isolated reconstruction ledger

Date: 2026-10-11. Branch: codex/cteas-p7-calpuff-20261011.
Base: P1–P5 integrated foundation 9b17dc65dbe736cdfa205619003cce085cf05d0b.
P6 branches and original engine/vendor/src are NOT modified.

## Dedicated CI

P7-only workflow: .github/workflows/p7-calpuff-scoped-ci.yml.
Runner routing is [self-hosted, lhy-desktop-3], with RUNNER_NAME == lhy-desktop-3
fail-closed enforcement. A runner name alone is NOT an automatically installed
GitHub Actions custom label; label presence, online assignment and HTTPS checkout
must be verified by an actual job. Jobs for P6 are not changed.

## Work packages (gated)

- P7A: Source blob SHA1/sha256 audit, routine and active-control inventory:
  IMPLEMENTED_FOR_CI, no runner-success claim. Original unchanged Fortran build,
  real Hefei 2022 CALPUFF run and frozen CONC.DAT are PENDING.
- P7B: First scoped native C++20 control-file reader and strict sequential
  unformatted Fortran record framing reader (4/8-byte markers, endian choice,
  trailer/size/truncation checks and synthetic fixtures): IMPLEMENTED_FOR_CI,
  NOT CLAIMED PASS until CTest. Active !KEY=value! vs inactive *KEY=value*
  syntax, repeated lists (ZFACE, CSPEC), exact numeric checks and fail-closed
  selected dry reference option validation. Original CALMET.DAT binary reader,
  date/CRS compatibility and full source parser are PENDING.
- P7C: Puff release / 3D advection: NOT STARTED.
- P7D: Sigma evolution / Briggs plume rise / terrain: NOT STARTED.
- P7E: Receptor concentration / CONC.DAT writer: NOT STARTED.
- P7F: Dry+wet deposition, decay and inventories: NOT STARTED.
- P7G: Native P6 to P7 end-to-end: BLOCKED ON P6 FINAL MET OUTPUT.

## Baselines and scientific constraints

Original source authority: engine/vendor/src/CALPUFF_v7.2.1_L150618.
Initial bundled CALPUFF.INP is an ORIGINAL SAMPLE, not the 2022 Hefei
50x50x9 at 100 m configuration. Historical project/cases/smoke5d_coldstart_20260701
is a different 2023 case and cannot be relabeled as 2022 reference.

The desired 2022 Hefei reference has only 143 confirmed CALMET intervals,
not blindly 144 output records. P6 currently has IPCODE=9999 at 143/143 hourly
records and NPSTA=0. P7 wet scavenging cannot obtain a scientific pass from
these dry-only observations.

Original source audit is only identity/inventory. P7B current parser is only
an input contract, NOT a binary CALMET.DAT parser nor CALPUFF physical model.
Fortran original parity, mass conservation and real-case full-model numerical
comparisons are required before any P7 PASS_REFERENCE/PASS_REAL_CASE status.

## Next gates

1. Verify the runner custom label, online assignment, network transport and CTest.
2. Freeze actual 2022 CALPUFF.INP and per-hour source conversion from annual Bq.
3. Execute original CALPUFF 7.2.1 on frozen original 2022 MET.DAT in job-private
   scratch, record original compiler, hashes, log, 1/6/all-143-hour CONC.DAT.
4. Implement original MET.DAT record-level read/parity before adding puff physics.

## 2026-10-11 P7B second increment — MET.DAT v2.1 field reader

An isolated C++20 Calmet21Reader now handles the original selected
unformatted CALMET.DAT 2.1 OUTHD/OUTHR, WRTR2D and WRTI2D fields.
It parses run metadata (time zone, 50x50x9 geometry, spacing, station counts),
the 4-byte Fortran field prefix (8 ASCII + 4 ints), all 4*Nx*Ny float/int
grids per field, expected 4*Nz+9 label ordering, exact 3600-second intervals,
cross-field time consistency, contiguous intervals, and an optional frozen
Hefei 2022 gate demanding 143 intervals. Integer fields IPGT and IRH are
explicitly separated from float fields. The callback is streaming and bounded
to a single field in memory. Synthetic corruption/time/NaN fail-closed tests
were added; P7 CI still must run before a PASS_SOFTWARE claim.

This is a decoded field I/O contract, not a scientific demonstration of
CALMET/CALPUFF numerical equivalence. Full raw real-2022 comparison and
original CALPUFF reference runs remain PENDING. Original 2022 precipitation
is missing; wet deposition cannot be validated.

## P7A/P7B independent reference tool preparation

- reference/build_original_calpuff.py: compile original UNMODIFIED
  modules.for + calpuff.for with gfortran in a job-private directory and
  persist source/compiler SHA provenance. This is NOT a successful build
  until actually run, and does not execute the 2022 original reference.
- reference/original_decode_calmet_hourly.py: copied P6 original-readout
  oracle unchanged from repository branch codex/cteas-p6-calmet-hefei-100m;
  copy sourced from the P6 implementation as a separate reference harness.
- reference/compare_frozen_met21.py: opt-in compare selected 2022 original
  MET.DAT structure and timestamps against new C++ CALMET21 reader. Does NOT
  certify wind physics or CALPUFF original full-case concentration parity.
- No baseline data is fabricated or read from the historical 2023 case.

## 2026-10-11 P7B Runner-3 build failure corrective patch

Observed: Runner `lhy-desktop-3` was assigned (P7 CI 38121776970,
38121935433, 38122015862); first two failed while default compiler
GNU 9.5.0 lacked std::bit_cast and std::chrono calendar. Latest CI
38122015862 did not reach C++ due to github.com:443 transient timeout.
P7B replaces bit_cast with standards-conforming memcpy and chrono calendar
with integer Gregorian-to-epoch conversion; CI selects newer installed
g++-12/g++-11 when available and retries HTTPS preflight. These corrections
are **not accepted** until a new job builds and all CTests run successfully.

## P7A GNU Fortran toolchain diagnostic

Runner-3 job 38122867540 proved P7B 4/4 CTest PASS with GCC 12.3.
The legacy default `/usr/bin/gfortran` does not support
`-fallow-argument-mismatch` (first actual compiler diagnostic).
Original reference CI now prefers installed `gfortran-12`, then
`gfortran-11`, before falling back to the default binary, logging exact
compiler version; reference build status stays UNVERIFIED until execution.

## P7A explicit compiler compatibility check

The P7A job now prints all `gfortran-12`, `gfortran-11` and default
`gfortran` executable paths/versions and uses a minimum GNU Fortran 10
gate when only the default binary is available. An incompatible old
compiler fails with a toolchain-specific message before trying CALPUFF.
Previous successful existing Linux CTEAS builds do not establish the
compiler selected inside this independent P7 runner job. The most recent
P7 CI 38122937191 attempt 2 failed on github.com HTTPS before compilation;
therefore the new compiler selection has not yet been proven by CI.

## 2026-10-11 GNU Fortran 11 fixed-column source diagnosis

Actual Runner-3 job [38123324977](https://github.com/RRain001/CTEAS/actions/runs/38123324977)
selected `/usr/bin/gfortran-11` (GNU Fortran 11.4.0), so the old
gfortran 4.7.4 problem has been resolved. Original `calpuff.for` contains
legacy fixed-format sequence identifiers in columns 73–80; the accidental
`-ffixed-line-length-none` option made those identifiers parse as Fortran
tokens, causing cascaded unexpected declarations/duplicate labels/junk
after function declaration. Build flag corrected to explicit
`-ffixed-line-length-72`. This is compilation behavior correction,
**NOT a change to the original Fortran source** and not a claim of
successful numerical/reference validation.

## P7A original 2022 reference execution gate scaffold

`reference/run_original_calpuff_reference.py` stages independently supplied
2022 CALPUFF controls + untouched original CALMET.DAT inside a case-private
working tree. It refuses invalid wet mode, mismatched study geometry/date,
paths escaping scratch, overwrites, and unpinned source hashes before any
original numerical run. Original Fortran `--execute` must be explicitly
requested with *two* frozen SHA256 inputs and the independently compiled
unchanged binary. It saves original binary/control/met SHA256, runtime log,
listing and concentration file identities; original execution success is
NOT C++ CALPUFF physics parity. Even if reference run is successful,
P7A source/physics fidelity is limited to the supplied, audited control.
Synthetic staging/unit test is not an original model run.

Pending actual source files from 2022; the old 2023 case is excluded.

## P7A frozen original real-case CI routing

P7-only CI has an optional real ORIGINAL CALPUFF execution gate;
it requires repository Actions variables with explicit `MET.DAT` and
CALPUFF control paths, plus both SHA256 hashes:
`P7_FROZEN_2022_MET_DAT`, `P7_FROZEN_2022_PUFF_INP`,
`P7_FROZEN_2022_MET_SHA256`, `P7_FROZEN_2022_PUFF_SHA256`.
All absent => `BLOCKED_NO_FROZEN_2022_CASE`; partial => error, never a
success. When present, the runner hashes the supplied source files,
runs the untouched original Fortran binary with a bounded timeout,
checks listing and concentration output, and writes provenance.
Successful real original run still does not certify new C++ physics.

## P7 dedicated Runner-3 HTTPS source retrieval hardening

Due to repeated `github.com:443` timeouts after verified Runner assignment,
the P7 workflow now probes both Git and authenticated private GitHub API.
When Git transport is unavailable or checkout fails but REST is available,
it bootstraps only the P7 submodule and unmodified original CALPUFF vendor
source files from the **exact PR merge commit Git tree** using the Actions
read-only token. Every blob is SHA1-verified with canonical Git object framing,
stale module/vendor trees are removed, and required files are checked before
any source audit/Fortran execution. Unavailable Git and REST transports
remain hard failures with no invented C++/Fortran pass. P6 and other runners
are not modified. CI verdict pending.

## P7 independently frozen 2023 CALMET/CALPUFF historical reference

The ORIGINAL case `project/cases/smoke5d_coldstart_20260701` is verified
in Git to contain immutable blobs:
- `run/met/met.dat`: 53,927,996 bytes, Git blob `cd0af6fed77639a5e7205bc1fc4f9e4421b41926`.
- `run/puff/puff.inp`: 83,305 bytes, Git blob `67dcdb856c0af92d30de346d4877af3b7d80db6f`.
- `run/puff/puff.con`: 1,653,584 bytes, Git blob `2a0c1a0dabf50e1e61badaa526780cc623150dc3`.

This is **Jan 1–5, 2023, 50×50 at 1 km**, not Jan 1–6, 2022 at
100 m. It can validate a real CALMET.DAT reader, run unchanged original
CALPUFF and yield genuine reference concentration evidence **without P6**.
The case's original control has `MWET=0, NDECAY=0`: it is not a
wet-deposition or tritium radioactive-decay parity benchmark.

The separate read-only `legacy_2023_case.py` script enforces original
Git blob SHA1 identities and freezes original source/control details.
It runs the compiled untouched Fortran original in an isolated scratch
directory. The historical `puff.con` comparison reports exact bytes
if present; record-envelope differences remain explicitly unverified
scientifically, and only a future C++ concentration output can establish
P7E numerical parity. The native `Calmet21Reader` must decode real
2023 hourly fields to pass. No historical data can satisfy the P7 2022 gate.

## 2026-10-11 first historical real-case diagnostic and exact fix

[CI #38125878790](https://github.com/RRain001/CTEAS/actions/runs/38125878790)
reliably downloaded all three historical immutable Git blobs (53.9 MB
MET.DAT, 83.3 KB original puff.inp, 1.65 MB historical puff.con), ran
all **6/6 scoped software CTest PASS**, compiled original Fortran
**PASS**, and executed untouched original CALPUFF with real historical
output present. The C++ MET21 reader then failed on header label
`Z0` before the hourly `U-LEV` sequence. Source-backed reason:
CALMET 2.1 static OUTHD header grid records may have the same length
as hourly 2D wind fields but have zero begin/end times. The reader
now gates on these static timestamps as well as label and size; the
synthetic fixture adds a same-size `Z0` record. Do not accept P7B real
historical decoding until this fix is validated by the next run.

Preserve the new historical original-reference JSON, log and
`puff.con` as a short-lived GitHub Actions artifact on private PR.

## 2026-10-11 P7C first source and transport implementation

The P7C C++20 prototype implements:
- Strict single constant original `NPT1=1` source `X` parsing. UTM
  coordinates are converted km -> m; stack altitude is geometric base +
  stack height, **WITHOUT** Briggs plume rise.
- Independent emitted species mass array (as provided in original
  source units, no arbitrary tritium Bq/g conversion), deterministic
  sequential puff IDs and one emission per configured time step.
- Original CALMET i-fastest [z][j][i] 3D wind storage; cell-centred
  horizontal bilinear and flat-terrain layer-centre vertical interpolation.
- Explicit midpoint RK2 advection; out-of-domain puffs are classified
  as outflow, not silently clamped or lost.
- Per-species equality: release = active inventory + domain outflow.
  Negative/NaN rates, malformed geometry and fields fail closed.

These are **P7C software contracts only**. Original CALPUFF release
cadence and source term units/physical momentum and wind/terrain
transformations still require original Fortran numerical comparison.
The 2023 original CONC.DAT does not establish P7C puff trajectory
parity, since P7D dispersion and P7E concentration have not been
reconstructed. CI result pending.

## P7C second increment — actual original CALMET hourly replay

Added `met_replay.cpp` and `cteas_p7c_met_replay`: reads the full
verified original 2023 CALMET.DAT 2.1 twice (metadata integrity, then
hourly 3-D wind stream), stores only one meteorological hour at a time,
and moves deterministic prototype packets with bilinear/vertical wind
interpolation and midpoint RK2. Each source `NSECDT` substep releases
all configured constant-source species in input units. A per-species
mass closure gate verifies emitted = active inventory + outflow.

The 2023 original case requires **119 consecutive one-hour intervals**
(2023-01-01 00 to 2023-01-05 23) with 1-km spacing. Original
CALPUFF uses its own puff split/merge/cadence, plume rise, sigma,
terrain and receptor averaging; this initial P7C replay is explicitly
**NOT a claim of source-faithful puff position or CONC.DAT parity**.
Run the real integration gate via scoped P7 CI; verdict pending.

## 2026-10-11 original CALMET 2023 endpoint representation

Actual P7 CI [38127081928](https://github.com/RRain001/CTEAS/actions/runs/38127081928)
established `CALMET.DAT 2.1`: NX=50, NY=50, NZ=9, DX=1000m,
119 hourly field groups, `FIRST_UNIX_SEC=1672531200`,
`END_UNIX_SEC=1672959600`, i.e. Jan 1 00:00 through Jan 5
23:00 UTC. The encoded original **final** Fortran field time is
`2023 / Julian day 5 / hour 22 / seconds 3600`, which is exactly
the same instant as 23:00. Our earlier P7C condition erroneously
required raw hour==23; P7B correctly normalizes seconds with 3600.
P7C now gates on normalized absolute Unix seconds, not raw Fortran
packed-hour bytes. This fixes the actual observed real source mismatch
without weakening the historic original input time interval.

## 2026-10-11 P7 2022 Hefei 50x50/100 m case execution ledger

`cteas_p7_2022_case_ledger` (library `cteas_p7_case_ledger`) is the
machine-checked execution ledger of the frozen 2022 reference case. It
takes `--met MET.DAT --control CALPUFF.INP` plus optional
`--concentration`, `--listing`, `--report` and
`--expect-{met,control}-sha256` pins, and prints deterministic JSON
(`gate=P7_HFEI_2022_CASE_EXECUTION_LEDGER`) to stdout; the human summary
line goes to stderr.

Statuses and exit codes are fail closed:
- `ACCEPTED_CANONICAL_2022_PENDING_ORIGINAL_EXECUTION` / exit 0: every
  frozen-spec and cross-file assertion passed and no original
  concentration file is present, so the original 2022 run is still pending.
- `ACCEPTED_CANONICAL_2022_ORIGINAL_OUTPUT_PRESENT` / exit 0: same, with an
  original concentration artifact pinned for provenance only.
- `BLOCKED_MISSING_INPUTS` / exit 3: mandatory MET.DAT/control (or an
  explicitly requested artifact) is absent. No ledger rows are invented and
  nothing is asserted about the case.
- `REJECTED_NOT_CANONICAL_2022` / exit 4: any refusal row failed. It covers
  absent sign/contract, non-50x50x9 grid, spacing other than 100 m, non
  `UTC+0000` zone, zero surface/upper or nonzero precipitation stations,
  interval count other than 143, endpoints other than 2022-01-01 00:00Z and
  2022-01-06 23:00Z, MET origin outside the +-3.5 km 2022 crop window,
  control date/grid/`ABTZ`/single-point-source departure, missing grid
  origin, control grid outside the MET domain, MET control-time mismatch,
  and any caller SHA-256 pin mismatch.

Refusal rows record `expected` and `observed`, so a foreign or historical
case cannot be relabelled: the immutable 2023 case
`project/cases/smoke5d_coldstart_20260701` is refused with
`DX_M=1000.000`, `INTERVALS=119`, `FIRST_UNIX_SEC=1672531200`,
`END_UNIX_SEC=1672959600` and a MET origin 38.4 km/18.3 km away, while its
control still resolves `METDAT` to the identical immutable blob. The
2022 case itself reports MET.DAT `origin=510884.644/3531268.927` as the
selected domain lower face and passes every row.

CTest:
- `cteas_p7_2022_case_ledger_contract`: synthetic CALMET.DAT 2.1 fixtures
  written by the test (canonical 143-interval 100 m fixture accepted, plus
  in-place header/field mutations, a truncated file, a 1 km 119-interval
  2023-like fixture, control mutations, pin mismatch, blocked inputs) and
  SHA-256 FIPS 180-4 vectors. Exit 0 requires the accept rows to pass and
  every refusal row to fail exactly where expected.
- `cteas_p7_2022_ledger_real_2023_refusal`: real-data gate over the
  immutable 2023 case; skips with an explicit line when the case is absent
  (sparse CI checkout) and is executed with `--require` by
  `.github/workflows/p7-calpuff-scoped-ci.yml`.

The Gregorian date helper is now shared by the CALMET.DAT reader and the
ledger (`include/cteas/puff/gregorian.hpp`) instead of being duplicated.

This ledger is **input identity and provenance only**: it makes no CALMET
or CALPUFF physics claim, no dispersion or concentration parity claim, and
no tritium-release or wet-deposition claim (`MWET=0` and zero precipitation
stations are part of the selected scope). `P7_FROZEN_2022_MET_DAT`,
`P7_FROZEN_2022_PUFF_INP` and both SHA256 repository variables remain
unset, so the 2022 50x50/100 m case is still
`BLOCKED_NO_FROZEN_2022_CASE`, and P7D/P7E/P7F/P7G stay unchanged.

## 2026-10-11 P7D MDISP=3 dispersion coefficients (PG rural + MP urban)

The selected real deck `project/cases/smoke5d_coldstart_20260701/run/puff/puff.inp`
carries `MDISP=3`, `MDISP2=3`, `MTURBVW=3`, `MTAULY=0`, `MHFTSZ=0`, `MROUGH=0`,
`AVET=60.`, `PGTIME=60.`, `SYTDEP=5.5E2` and `MDRY=1`. For MDISP=3 the vendor
documentation states: "3 = PG curves (rural), MP (urban)" (`csigma.puf`), so
`MDISP2`, `MTURBVW` and `MTAULY` are recorded but **not effective** for this
case (they enter IDOPT 1, 2 and 5 only). `MDISP=3` is therefore the real-case
dispersion path and the one now reconstructed; wet scavenging (`MWET=0`),
chemistry (`MCHEM=0`), slug mode (`MSLUG=0`) and gravity settling/tilt
(`MTILT=0`) remain out of this path, and dry deposition (`MDRY=1`) is the next
physical path, not yet implemented.

New native module (`include/cteas/puff/dispersion.hpp`, `src/dispersion.cpp`,
probe `src/dispersion_probe.cpp`):

- SIGTY equivalent: rural Pasquill-Gifford-Turner sigma-y with the ISC 6-8
  C/D pair per class, averaging-time factor `(AVET/PGTIME)**0.2`, per-cell
  roughness factor `YZ0FAC`, the secant pseudo-distance inversion for a
  non-zero start-of-step sigma (CRIT = 1e-4, 50 iteration limit, 0.85 step
  restriction) and the Heffter (1965) time-based growth beyond `SYH`, with
  `THFTY` obtained exactly as SETCSIG does (`SIGTY` with `SIGY0 = SYH`).
- SIGTZ equivalent: rural ISC multi-segment sigma-z (segment A/B pairs per
  class, segment selection on the SIGSET junctions, optional roughness
  adjustment `A' = A*AZ0FAC`, `B' = B-BZ0TRM` when `BZ0TRM > -999`), and urban
  McElroy-Pooler/Briggs sigma-z with the ISC 5000 m cap. Urban sigma-y uses
  Briggs `AYURB`/`XIYURB`; `XVY`/`XVZ` pseudo-distances are ported verbatim
  (including the cubic branch for classes A and B).
- Tables from the vendor `BLOCK DATA`/`SIGTY` DATA statements
  (`AYURB`, `XIYURB`, `AZURB`, `XIZURB`, `NZBRUR`, `XZBRUR`, `AZRUR`, `BZRUR`,
  `AYT`, `AZT`, `AYPGT`, `BYPGT`, `SYH`, `SZH`, ISC `C`/`D`), plus the SIGSET
  junction recomputation from the A/B continuity condition.
- Original semantics reproduced: the stability class is conditioned to 6 above
  6 (SETCSIG), small negative increments are reset to zero and reported while
  larger ones fail closed at the original `ZEROSEC(2)`/`ZEROKM(2)` thresholds,
  and `SYTDEP` is clipped to `NINT(AVEFAC*100)*1000`.
- Fail closed (deviation from the original, which silently propagates or
  halts): negative or non-finite sigma inputs, non-finite results, negative or
  non-finite setup values, unsupported `MDISP`, unsupported `MROUGH`/`MHFTSZ`
  values, `MROUGH=1` (gridded CALMET z0 plumbing not reconstructed; use
  `roughness_adjustment(z0)` per cell) and `MHFTSZ=1` (HEFTRAN transition time
  not reconstructed).

Not yet reconstructed: the `SIGMA()` nearest-known-sigma restart wrapper,
`HEFTRAN` slug geometry, `MROUGH=1` gridded roughness plumbing, and MDISP 1, 2,
4 and 5. No advection, concentration, deposition or chemistry is claimed.

### Source anchor

`reference/sigma_source_anchor.py` slices the exact line spans of the vendor
units out of the unmodified `calpuff.for` (no edits), pins the vendor file and
all vendor `*.puf` includes by SHA-256 in `reference/sigma_source_anchor.json`,
and stages the spans plus the hand-written driver
`reference/sigma_oracle_driver.f` for compilation. Vendor source:
`sha256 da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`,
`BLOCK DATA` L1999-2424, `SIGSET` L52303-52502, `SIGTY` L50797-51215,
`SIGTZ` L51263-51752, `XVY` L51217-51261, `XVZ` L51754-51838,
`WARN` L79648-79797. Any drift fails the `--check` mode.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7d_dispersion_contract`: hand-derived closed-form values (classes C,
  D urban/rural), monotone growth for all six classes, pseudo-distance round
  trip, Heffter growth, roughness adjustment, averaging factor, control audit
  and every fail-closed path. PASS.
- `cteas_p7d_sigma_source_parity`: vendor anchor + 243 table values bit-exact
  as REAL*4 (including the SIGSET junctions, max recomputation deviation
  1.4e-6 relative) + 612-case matrix against the compiled **unmodified**
  vendor oracle: `MAX_REL=2.596e-07` with acceptance `1e-5` across 7 columns.
  PASS in 4.3 s.
- Local `ctest` 10/11 PASS; the only failure is the pre-existing
  macOS case-insensitive-filesystem failure of
  `cteas_p7_original_case_stage_contract` (reproduced from pristine HEAD, PASS
  on Linux).

The workflow runs the parity test with `--require` (a Fortran compiler is
mandatory there) and audits the real deck with
`cteas_p7d_sigma_probe --audit`, asserting `MDISP=3` is the selected option.

### CI evidence for the P7D increment

Dedicated runner `lhy-desktop-3`, [run 38134496962](https://github.com/RRain001/CTEAS/actions/runs/38134496962)
at commit [4449c84](https://github.com/RRain001/CTEAS/commit/4449c84): `p7-scoped`
SUCCESS, `100% tests passed, 0 tests failed out of 11`. The required P7D steps printed
`P7D_SIGMA_FORTRAN_ORACLE_PARITY=PASS CASES=612 COLUMNS=7 TOLERANCE_REL=1e-05 MAX_REL=0.000e+00`
with `GNU Fortran (Ubuntu 11.4.0) 11.4.0` (bit-exact against the compiled unmodified
vendor routines, versus 2.596e-07 on macOS with gfortran 16.2.0) and
`P7D_DISPERSION_OPTION_AUDIT=PASS MDISP=3 SELECTED_OPTION_IS_REAL_CASE_PATH=true
MDISP2_EFFECTIVE=false MTURBVW_EFFECTIVE=false MTAULY_EFFECTIVE=false` for the real
2023 deck. `MDRY=1` dry deposition is the next physical path and is not implemented.

## 2026-10-11 P7F MDRY=1 dry deposition (computed gas, real-case species)

The locked Hefei 2022 deck
(`project/cases/hefei5km_2022_reference_case_20261011/run/puff/puff.inp`)
carries `MDRY=1`, the default `RCUTR=30` s/cm, `RGR=10` s/cm, `REACTR=8.0`,
`NINT=9`, `IVEG=1`, `ZFACE` with a 20 m first layer (so `ZREF=10 m`), and two
species in input group 3a:

| species | modeled | emitted | dry deposition | group 7 parameters |
|---|---|---|---|---|
| `H-3` | 1 | 1 | `1` = COMPUTED-GAS | `DIFFUSIVITY .1509` cm**2/s, `ALPHA STAR 1.0`, `REACTIVITY 8.0`, `MESOPHYLL 0.0` s/cm, `HENRY 0.04` |
| `HE-3` | 1 | 0 | `0` = no dry removal | none |

So the real dry-deposition path is the gas resistance model for one species.
`IDRY=0` in input group 5, i.e. **the case writes no dry-flux output**: the
frozen `run/puff/puff.con` (1,896,056 bytes, 3,655 sequential-unformatted
records, 11 distinct record sizes, clean 4-byte envelope) contains
concentration records only.

New native module (`include/cteas/puff/dry_deposition.hpp`,
`src/dry_deposition.cpp`, probe `src/drydep_probe.cpp`):

- Input group 3a species table (hyphenated names, which the generic
  `!KEY=value!` parser cannot express), input group 7 gas parameters and input
  group 9 reference values are parsed from the control text with anchored
  patterns, and cross-checked against `CSPEC`.
- DRYI equivalents: `cm**2/s -> m**2/s` and `s/cm -> s/m` conversions,
  `SC = vair/pdiff`, `RD1 = d1*SC**d2/vk`, `RCUT = RCUTR*REACTR/REACT`,
  `RGG = RGR*REACTR/REACT`, `RGW1 = HENRY/(ALPHAS*d3)`, and
  `ZREF = min(0.5*(ZFACE1+ZFACE2), 10)`.
- VDCOMP equivalent: the aerodynamic resistance (stability-dependent `PSIH`,
  `USMIN` floor, `RAMIN` floor, wind-driven water roughness
  `z0m = 2e-6*w**2.5` with the 1 m/s threshold), the deposition-layer term
  `RD1/u*`, the canopy resistance from stomatal (`PCONST`, `BMIN`/`BMAX`,
  `QSWMAX` radiation interpolation and the 35 C/10 C temperature branches),
  mesophyll, cuticle and ground/water terms, and `vd = 1/(RA+RD+RC)`.
- DRY uniformly-mixed branch: `DIFFK` from `CONK1`/`CONK2`, `u*`, `w*` and the
  mixing height, `VDPVD = DIFFK/(DIFFK+vd*dz)`, and
  `FRACDRY = exp(-VDPVD*vd*dt/lid)`.
- Fail closed: `MDRY != 1`, particle deposition (method 2), user-specified
  diurnal velocities (method 3), illegal method values, a gas species without
  group 7 parameters, group 7 rows for unknown or non-deposited species, a
  species list that disagrees with `CSPEC`, non-positive `RCUTR`/`RGR`/
  `REACTR`/diffusivity/alpha/reactivity, `IVEG` outside 1-3, and non-finite or
  out-of-range environment inputs (lid height, sampling step, mixing height,
  `w*`, temperature, `u*`, `L`, LAI, roughness, vegetation state) all raise
  instead of being ignored.
- Not reconstructed: the Gaussian-puff removal branch (needs the `VCBar`
  vertical coupling coefficient), the `RDVD` input table and the particle
  physics of `DRYI`/`VDP1`.

### Source anchor

`reference/drydep_source_anchor.py` slices the exact spans out of the
unmodified `calpuff.for` and pins them in
`reference/drydep_source_anchor.json`: compiled by the oracle
`VDCOMP` L26293-26565 and `VDP` L26567-26681; anchored read-only `BLOCK DATA`
L1999-2424, `DRY` L26052-26291, `DRYI` L26820-27042, `RDVD` L26683-26818 and
`VDP1` L27044-27208, plus every vendor `*.puf` include. Vendor source
`sha256 da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`.
The DRYI statements that are ported by hand are asserted to still be present
verbatim in the anchored text, and the /DRYGAS/ constants (`PCONST`, `BMIN`,
`BMAX`, `QSWMAX`, `DCONST1`-`DCONST4`) are read back from the vendor BLOCK DATA
and compared with the values compiled into the module.

### CTest evidence

- `cteas_p7f_dry_deposition_contract`: hand-derived closed forms (inactive
  vegetation, hot/cold stomata, radiation interpolation and clamping, water
  cell with wind-driven roughness, neutral/stable `PSIH` branches, `u*` floor),
  the removal fraction, and every fail-closed path. PASS.
- `cteas_p7f_locked_case_dry_deposition`: the locked Hefei 2022 deck is audited
  in C++ (`MDRY=1`, H-3 gas, HE-3 none, `ZREF=10`, `RCUTR=3000` s/m,
  `RGR=1000` s/m, `REACTR=8`, `RD1=4.9801`). PASS.
- `cteas_p7f_drydep_source_parity`: anchors + 8 vendor constants + 11 quoted
  DRYI statements + **11,520 cases x 2 species against the compiled unmodified
  VDCOMP**: `MAX_REL=1.414e-07` (float32 level) against a fixed `1e-5`
  acceptance bound, plus the real-deck audit
  (`P7F_REAL_DECK_DRYDEP_AUDIT=PASS MDRY=1 GAS_SPECIES=1 NON_DEPOSITED=1
  UNSUPPORTED=0 VEGETATION_STATE=1 ZREF_M=10 RD1_SPECIES_0=4.9801`). PASS in
  1.4 s.
- Local `ctest` 13/14 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of
  `cteas_p7_original_case_stage_contract` (PASS on Linux).

### Real-case comparability statement (no fabricated comparison)

`run/puff/puff.con` is **not yet comparable** with the new C++ deposition
velocities, and no comparison number is claimed. Verified gaps:

1. `IDRY=0` in the locked deck: the artifact has no dry-flux records, and the
   original writes per-step `vd` only behind its debug flag, so a
   case-level dry-flux comparison is impossible without re-running the
   original with debug output (out of scope here).
2. Per-cell dry-deposition inputs are missing: the P7B CALMET.DAT reader
   decodes the hourly typed fields (`USTAR`, `ZI`, `EL`, `QSW`, `TEMPK`, ...)
   but skips the static header records, so the real-case `Z0`, land use and
   `XLAI` are not available yet.
3. No puff-state integration: the `SIGMA()` restart wrapper, `HEFTRAN` and the
   `VCBar` coupling coefficient are not reconstructed, and P7C is still a
   prototype, so the removal fraction cannot be advanced over a real puff
   trajectory.
4. No concentration output: P7E does not exist, so there is nothing to diff
   against the 3,655 concentration records of `puff.con`.

What is comparable and now compared: the deposition velocity and the
time-invariant parameters for the real species configuration, against the
unmodified vendor routines (above), which is the strongest available
original-reference check at this stage.

## 2026-10-11 P7E receptors, puff-to-receptor sampling and CONC.DAT framing

The locked deck uses gridded receptors (`LSAMP=T`, `IBSAMP/JBSAMP=1`,
`IESAMP/JESAMP=50`, `MESHDN=1`) with an empty discrete-receptor subgroup, i.e.
**2500 receptors at 100 m spacing** (first at 510.935/3531.320 km, last at
515.835/3536.220 km).

New native module (`include/cteas/puff/receptors.hpp`,
`include/cteas/puff/conc_file.hpp`, `src/receptors.cpp`, `src/conc_file.cpp`,
probe `src/p7e_probe.cpp`):

- Receptor geometry from the sampling grid using the vendor cell-centre
  convention (`(IBSAMP-0.5)*DGRID + i*DELSAM` with `DELSAM = DGRID/MESHDN`) plus
  discrete receptors from subgroup 17b (`! N = X, Y, ZELEV [, ZRCT] !`).
  Fail closed on indices outside the met or computational grid, `MESHDN < 1`,
  receptors outside the met grid, malformed rows, and a deck that enables
  neither gridded nor discrete receptors.
- PFSAMP equivalent (the two sampling integrals, including the `A < 1e-4`
  low-wind branch) and ERFDIF equivalent, both in REAL*4 like the originals.
- CALCPF gridded-receptor accumulation
  `conc += VDPVD*F1*TFRACT*(QOLD*T1 + QNEW*T2)` with
  `dinv = ASDF/(2*pi*sigma_y**2)`, `T2 = I2*dinv`, `T1 = I1*dinv - T2`. The
  vertical coupling factor F1 (VCBar) and VDPVD are explicit inputs because
  those layers are not reconstructed; ASDF defaults to 1.0.
- CONC.DAT writer and reader with the **measured** record layout of the frozen
  artifact: version record (96 B), comment count (4 B), 132-byte comments,
  32-byte sampling-period records `(year, julian, hour, seconds) x2`, 32-byte
  grid descriptors (`nrec, group index, 'TOTAL' 16 chars, XORIGKM, YORIGKM`)
  and species fields `label(8) + 7-byte index + nx*ny REAL*4` (10015 B for
  50x50). Fail closed on label length, date/second ranges, non-finite values,
  field dimension/species-count mismatches and period inconsistencies.
- Not reconstructed (and refused or explicitly supplied): CTSG (terrain
  factors, upper/lower splits, slugs, wind shear, PDF), VCBar, the WROUT1
  header beyond the version and comment records, area/line/volume source
  sampling, and the AVET averaging machinery of the original output stage.

### Source anchor

`reference/p7e_source_anchor.py` slices the exact spans out of the unmodified
`calpuff.for` and pins them in `reference/p7e_source_anchor.json`: `PFSAMP`
L4683-4751, `ERFDIF` L54910-54965, `WRTI1D` L64706-64739, `WRTR1D`
L64741-64774, `WRTR2D` L64776-64826, plus every vendor `*.puf` include.
Vendor source `sha256 da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`.
The PFSAMP/ERFDIF constants and 8 quoted statements are asserted to still be
present verbatim in the anchored text.

### CTest evidence

- `cteas_p7e_receptor_sampling_conc_contract`: receptor geometry (2500
  receptors, `MESHDN=2` refinement to 99x99, discrete receptors, five
  fail-closed cases), PFSAMP invariants (low-wind branch closed form, invariance
  under trajectory reversal, closer approach samples more mass), the ERFDIF
  branches, the accumulation closed form, writer/reader round trip, and
  **structure parity with the frozen artifact**: identical period/grid/field
  counts (143/143/143), identical field record sizes (10015 B) and identical
  period times, with this module's own values.
- `cteas_p7e_source_parity`: anchors + 8 quoted statements +
  `P7E_PFSAMP_ORACLE_PARITY=PASS CASES=182 MAX_REL=4.121e-06` (tolerance
  `1e-5`) against the compiled unmodified PFSAMP + vendor framing readback
  (records written by the unmodified `WRTI1D`/`WRTR1D` are parsed by this
  module's reader) + locked-deck receptor geometry +
  `P7E_FROZEN_CONC_STRUCTURE=PASS RECORDS=3655 PERIOD_RECORDS=143
  GRID_RECORDS=143 SPECIES_FIELDS=143 FIRST_BEGIN=2022001 LAST_END=2022006`.

### Real-case comparability statement (no fabricated numbers)

**Structure is compared and matches; values are NOT compared.**
`run/puff/puff.con` (1,896,056 B, 3,655 records) contains 143 sampling-period
records, 143 grid descriptors and 143 species fields labelled `H-3`
(10015 B each, i.e. the 50x50 grid) covering 2022 julian days 1-6. This module
reproduces that data-record structure exactly for the same configuration, but
its field values are its own. Verified gaps before a value comparison is
possible:

1. CTSG (the concentration kernel) and the VCBar vertical coupling factor are
   not reconstructed, so no receptor concentration can be produced for a real
   puff yet.
2. Puff advection is still the P7C prototype: no CALPUFF release cadence,
   split/merge, plume rise, sigma restart (`SIGMA()`/`HEFTRAN`) or terrain
   interaction.
3. Per-cell dry-deposition inputs (`Z0`, land use, `XLAI`) live in CALMET
   static records that the CALMET.DAT reader does not decode yet.
4. The writer emits the CTEAS header subset (version + comments), so the
   original post-processing toolchain cannot read these files yet.

## 2026-10-11 P7G CALMET static fields decoded (Z0 / ILANDU / ELEV / XLAI / NEARS)

Closes the "per-cell dry-deposition inputs missing" gap of the P7E round. The
original CALMET.DAT 2.1 OUTHD static section is written before the first hourly
field (CALMET `calmet.for` L12482-12536, anchored):

| record | label | contents |
|---|---|---|
| NCOM+4 | `ZFACE` | `nz+1` REAL*4 cell face heights |
| NCOM+5/6 | `XSSTA`/`YSSTA` | surface station coordinates (when `nssta >= 1`) |
| NCOM+7/8 | `XUSTA`/`YUSTA` | upper air station coordinates |
| NCOM+9/10 | `XPSTA`/`YPSTA` | precipitation station coordinates |
| NCOM+11 | `Z0` | `nx*ny` REAL*4 roughness lengths |
| NCOM+12 | `ILANDU` | `nx*ny` **INTEGER** land use categories (`WRTI2D`) |
| NCOM+13 | `ELEV` | `nx*ny` REAL*4 elevations |
| NCOM+14 | `XLAI` | `nx*ny` REAL*4 leaf area indices |
| NCOM+15 | `NEARS` | `nx*ny` **INTEGER** nearest station indices |

`Calmet21Reader` now decodes these records instead of skipping them
(`Calmet21Static` in `calmet21.hpp`): the label must be exact and the payload
length must match the documented field, otherwise the file is malformed and the
read fails; `Z0`, `ELEV` and `XLAI` must be finite and within physical bounds
(0-100 m, -1000-10000 m, 0-20), `ILANDU` categories within 0-1000, and
`ILANDU`/`NEARS` are read as INTEGER exactly as `WRTI2D` writes them.

Locked-case evidence (`project/cases/hefei5km_2022_reference_case_20261011`,
`met.dat` sha256 `b1823cda...`), CTest
`cteas_p7g_locked_case_static_decode` with pinned digests:

```
P7G_STATIC Z0   COUNT=2500 MIN=0.25  MAX=0.25  MEAN=0.25    DIGEST=7401557581232649795
P7G_STATIC XLAI COUNT=2500 MIN=3     MAX=3     MEAN=3       DIGEST=14015295161301286211
P7G_STATIC ELEV COUNT=2500 MIN=25    MAX=59.5  MEAN=42.9157 DIGEST=16152187619603912443
P7G_STATIC_LAND_USE_DIGEST=3196964006486516483 NEAREST_DIGEST=14033661785612014883
P7G_REAL_MET_STATIC_DECODE=PASS INTERVALS=143 HOURLY_FIELDS=6435
```

The decoded fields immediately feed the dry-deposition path: the probe mode
`cteas_p7f_drydep_probe --real-cell MET.DAT PUFF.INP 25 25 0` builds the
VDCOMP environment from the real file (land use, `Z0`, `XLAI`, `USTAR`, `EL`,
`QSW`, `TEMPK`, `ZI`, `WSTAR`) and reports, for the locked case:

```
P7G_REAL_CELL_VD=PASS CELL=25,25 HOUR=0 LAND_USE=20 Z0_M=0.25 XLAI=3 USTAR=0.246525
  EL=-49.495 QSW=194.594 TEMPK=279.15 ZI=230.977 WSTAR=0.484167 RA=29.5576 DIFFK=11.1832
  H-3_VD=0.00198035 H-3_FRACDRY=0.970734 HE-3_VD=0 HE-3_FRACDRY=1 NOT_A_MODEL_RUN=true
```

i.e. H-3 deposits at 0.198 cm/s with 2.9 % removed per 3600 s step at that cell
and hour, while HE-3 (flagged with no dry removal in the deck) stays at zero.
This is a coefficient evaluation on real inputs, not a model run: it still uses
the caller-supplied vertical factor and does not advance any puff.

Remaining incomparability causes after this round (was four, now two):

1. CTSG (the concentration kernel) and `VCBar` are still missing, so no
   receptor concentration exists for a real puff. `VCBar` is scoped as
   `function vcbar(ip,mfact0,hlid,ppcoef,lcalm)` at `calpuff.for`
   L53866-54088 (223 lines, span sha256 prefix `4c6aa6584979`) and it calls
   `ctadj`, `getelev` and `hlidmax` plus the `/PUFF/`, `/GRID/`, `/CURRENT/`
   and `/FLAGS/` state; CTSG additionally needs terrain factors, upper/lower
   layer splits, slug and shear/PDF paths.
2. Puff advection is still the P7C prototype (no release cadence, split/merge,
   plume rise, `SIGMA()`/`HEFTRAN` restart or terrain interaction), and the
   writer emits only the CTEAS header subset, so the frozen `puff.con` values
   still cannot be reproduced or compared.

## 2026-10-11 P7H vertical coupling (VCBar / VCOUP / CTADJ)

The concentration path's vertical coupling is now reconstructed and wired into
the receptor accumulation.

- `VCOUP` (`calpuff.for` L53711-53864, self-contained): well-mixed codes
  (2/6 and their slug forms 12/16), the "above mixed layer and uniform" code 4,
  the elevated-receptor branches, the `SZCUT` sigma-z screen, the
  unlimited-mixing rule when the source is above the lid, the reflection sum
  over ground and lid, and the near-uniform approximation of Yamartino (JAPCA
  27, 5, 1977) selected by `sz/hlid > 0.63`.
- `VCBAR` (L53866-54088): the per-step space/time average, i.e. one third
  weights for a puff (mid-step with `SZM1`, begin with `SZB1`, end with `SZE1`)
  and one quarter weights for a slug (both ends at both ends of the step), with
  the plume-tilt heights `ZFINAL - t*VSETL` when `MTILT=1`, the non-negative
  height conditioning, and the `HLIDMAX = HLID` argument used for the VCOUP
  calls. `LCALM=TRUE` fails closed (the vendor halts).
- `CTADJ` (L20480-20540): both the ISC treatment (`MCTADJ=1`) and the partial
  plume-height correction (`MCTADJ=3`). The vendor's terrain *lookup*
  (`GETELEV`/`GETCELL`) is not ported: callers pass a lookup function and
  `MCTADJ=1/3` fails closed without one, so the locked case's `MCTADJ=2` path
  is what runs today.
- Wiring: `receptor_concentration_increment_with_coupling` takes the vertical
  factor from VCBAR instead of a caller constant, so the P7E accumulation now
  uses reconstructed physics.

### Source anchor

`reference/p7h_source_anchor.py` pins the exact spans of `VCBAR`, `VCOUP`,
`CTADJ` plus `GETELEV`/`GETCELL` (referenced by VCBAR and linked by the oracle)
in `reference/p7h_source_anchor.json`, together with every vendor `*.puf`
include; the constants and 17 statements the port reproduces are asserted
verbatim in the anchored text. Vendor source
`sha256 da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`.

### Evidence

- `P7H_VCOUP_ORACLE_PARITY=PASS CASES=1920 MAX_REL=0.000e+00` - bit-exact
  against the compiled unmodified `VCOUP` over codes 1/2/4/6/11/12/16/99,
  receptor and source heights, five sigma-z values and three lid pairs.
- `P7H_VCBAR_ORACLE_PARITY=PASS CASES=96 MAX_REL=1.076e-07` - puff and slug
  branches, `MTILT` 0/1, two lid heights, three height pairs and two sigma
  pairs, against the compiled unmodified `VCBAR` (tolerance `1e-5`).
- `cteas_p7h_vertical_coupling_contract`: hand-derived closed forms for the
  well-mixed, elevated-receptor, unlimited-lid, trapping and CTADJ branches,
  puff/slug weighting, plume tilt, the coupling-aware accumulation equivalence,
  and every fail-closed path.
- `P7H_REAL_GRID_RUN=PASS HOUR=0 RECEPTORS=2500 STABILITY=4 URBAN=false
  SPEED_MS=1.39612 STEP_KM=5.02603 SIGMA_Y_M=293.839 SIGMA_Z_M=88.9692
  ZI_M=230.977 VCBAR_1_PER_M=0.0065347 SUM=7.91939e+08 MAX=316795 MIN=0
  NONZERO=2500`: one synthetic puff moved one step over the locked case's
  receptor grid with real met inputs (statics, `U`/`V`/`ZI`/`IPGT`) and the
  reconstructed coupling. This is a physical-chain demonstration, explicitly
  **not** a comparison against the frozen `puff.con`.

### Remaining incomparability causes (still two)

1. `CTSG` - the concentration kernel - is still missing. Its precise
   requirements: the terrain-factor path (`FCTZ`/`FCTY`/`TFAC` plus the
   `CTSGDAT` hill arrays), the upper/lower layer split (`UPPER`/`LOWER`,
   `QATR` numerical integration, `ERF`/`BJI`/`BI` reflection helpers), the slug
   sampling (`SLUGINT`/`SLUGAVE`/`SLUGSNP`, `ERFDIF`), the wind-shear and PDF
   options, and the receptor-side averaging that consumes them. `VCBAR` (this
   round) removes the coupling part of that dependency.
2. The puff model itself is still the P7C prototype (release cadence,
   split/merge, plume rise, `SIGMA()`/`HEFTRAN` restart, terrain interaction)
   and the CONC.DAT writer emits only the CTEAS header subset, so the frozen
   `puff.con` values still cannot be reproduced or compared.

## 2026-10-11 P7I CTSG blocks: QATR and TFAC closed; the rest scoped

Status of the CTSG dependency closure, with the locked deck's own values as the
evidence for what is and is not the real-case path
(`MSLUG=0`, `MSHEAR=0`, `MPDF=0`, `NHILL=0`, `NINT=9`, `AVET=PGTIME=60`,
`MCTADJ=2`, `MTILT=0`):

| block | status |
|---|---|
| `QATR` Romberg integrator (L25406-25520) | **implemented and parity-checked** (`P7I_QATR_ORACLE_PARITY=PASS CASES=80 MAX_REL=2.980e-07`, status flags match) |
| `TFAC` terrain distortion interpolation (L25765-25813) | **implemented and parity-checked** (`P7I_TFAC_ORACLE_PARITY=PASS CASES=14 MAX_REL=1.366e-07`) |
| `FCTZ`/`FCTY` + `CTSGDAT` hill arrays | not the real-case path: `NHILL=0`, so no hill/terrain-following factors exist for this deck; the routines are neither ported nor needed |
| slug sampling `SLUGINT`/`SLUGAVE`/`SLUGSNP` | not the real-case path: `MSLUG=0`; `ERFDIF` is already ported and parity-checked in P7E |
| wind shear / PDF options | not the real-case path: `MSHEAR=0`, `MPDF=0` |
| `AVET` receptor averaging | not effective for this case: `AVET=PGTIME=60`, so the averaging factor is exactly 1 (already recorded in the P7D section) |
| `CTSG`/`CTREC`/`CTPAR`/`MUNU`/`LOWER`/`UPPER` + `BI`/`BJIL`/`FLOPUFF` | still missing: the remaining real-case kernel. `CTSG` L22923-23112 calls `ctpar`/`ctrec`/`lower`/`puffc`/`upper`; `CTREC` L22841-22921 calls `munu`/`rotate`; `LOWER` L24657-24863 calls `bi`/`bjil`/`munu`; `UPPER` L25815-26001 calls `bi`/`bji`/`flopuff`/`qatr`. With `NHILL=0` and a puff inside the mixed layer the reachable kernel is the lower-segment one, but it still needs the `/CTPASS/` state (`Hd`, `zi`, `ppcoef`, the plume/slug geometry), the `BI`/`BJIL` reflection helpers and the `MUNU` vertical distribution index |

`reference/p7i_source_anchor.py` pins `BLOCK DATA` (L1999-2424), `QATR` and
`TFAC` spans plus every vendor `*.puf` include, and 12 quoted statements are
asserted verbatim; the oracle sets the `/CONST/` values that the vendor BLOCK
DATA would otherwise provide.

Incomparability causes remain two: the CTSG kernel above, and the still
unfaithful puff model plus the CTEAS-only CONC.DAT header.

## 2026-10-11 P7J CTSG kernel round: ROTATE closed, kernel still open

This round closed one more CTSG-closure block and re-verified the earlier ones;
the core kernel itself is **not** done and is listed precisely below.

| block | status |
|---|---|
| `ROTATE` (L25522-25549, used by CTREC/CTPAR) | **implemented + parity**: `P7I_ROTATE_ORACLE_PARITY=PASS CASES=45 MAX_REL=5.059e-07` |
| `QATR` (L25406-25520) | implemented + parity (80 cases, `MAX_REL=2.980e-07`, status flags match) |
| `TFAC` (L25765-25813) | implemented + parity (14 cases, `MAX_REL=1.366e-07`) |
| `MUNU` | **not done**: the vertical distribution index; the vendor name is not a plain `function munu`/`subroutine munu` under the anchor patterns used so far, so the span must be located by its call sites (`CTREC` L22841-22921 calls it) before it can be extracted and ported |
| `CTREC` (L22841-22921) | **not done**: needs `MUNU` plus the receptor/puff geometry state it rotates |
| `CTSG` (L22923-23112) | **not done**: calls `ctpar`/`ctrec`/`lower`/`puffc`/`upper`; the real-case branch selection (`MCTADJ=2`, `NHILL=0`, `MSLUG=0`, `MSHEAR=0`, `MPDF=0`) resolves to the lower-segment kernel, but the routine itself, its slug/puff dispatch and the `PUFfC` path are not ported |
| `CTPAR` | **not done**: puff geometry/parameter preparation for CTSG |
| `LOWER` (L24657-24863) | **not done**: needs `BI`/`BJIL` (the reflection-series helpers), `MUNU` and the `/CTPASS/` state (`Hd`, `zi`, `ppcoef`, plume/slug geometry) |
| `UPPER` (L25815-26001) | **not done**: needs `BI`/`BJI`, `FLOPUFF` and `QATR` (the integrator is now available) |
| `BI`/`BJIL`/`BJI` | **not done**: the reflection-series helper functions; their spans must be located by call sites before extraction |
| `FLOPUFF` | **not done**: the flow-splitting routine that provides `Hd` |

Consequence: the `F1` chain is still `VCBAR` (P7H) for the *vertical coupling*,
but the concentration kernel that consumes it (`CTSG`/`LOWER`) does not exist
yet, so no receptor concentration can be produced for a real puff and the
incomparability list stays at two causes (the CTSG kernel above; the
still-prototype puff model plus the CTEAS-only CONC.DAT header).

Honest status of this round: the acceptance target "CTSG plus CTREC/MUNU with
original-source parity" was **not reached**; only the support blocks (`ROTATE`,
re-verified `QATR`/`TFAC`) carry parity evidence. The next round should start by
locating `MUNU`, `BI`, `BJIL`, `BJI`, `FLOPUFF`, `CTPAR` and `PUFfC` spans by
their call sites, then port `CTSG` with the lower-segment branch.

## 2026-10-11 P7K CTSG kernel units located by call site

The plain-name anchor patterns used for `QATR`/`TFAC`/`ROTATE` did not match the
remaining CTSG kernel units, so they are now located by scanning every vendor
routine header (any `function`/`subroutine` declaration, optional type prefix,
flexible indentation). `reference/p7k_source_anchor.py` records the exact span,
SHA-256 and call closure of each unit and `--check` fails on any drift; the gate
and the workflow run that check.

| unit | span | lines | sha256 prefix | calls |
|---|---|---|---|---|
| `bi` | L22229-22263 | 35 | `917e2da3b8b2547a` | - |
| `bji` | L22265-22316 | 52 | `53e3010313a89e13` | - |
| `bjil` | L22318-22363 | 46 | `e34ab5ac71fdd8c4` | - |
| `ctpar` | L22505-22839 | 335 | `00dee71ee0419be6` | `axis`, `hilrot`, `munu`, `path`, `rotate` |
| `ctrec` | L22841-22921 | 81 | `279397a1d0f7ad5e` | `munu`, `rotate` |
| `ctsg` | L22923-23112 | 190 | `3f1011394e50` (P7H anchor) | `ctpar`, `ctrec`, `lower`, `puffc`, `upper` |
| `flopuff` | L23178-23656 | 479 | `5dccb500891d` | (own closure, not yet scanned) |
| `lower` | L24657-24863 | 207 | `688c6978246d` | `bi`, `bjil`, `munu` |
| `munu` | L24865-24967 | 103 | `348cec20d84b` | - |
| `puffc` | L25286-25404 | 119 | `b739807ef741` | - |
| `upper` | L25815-26001 | 187 | `9e24496fb8da` | `bi`, `bji`, `flopuff`, `qatr`, `to` |
| `rotate` | L25522-25549 | 28 | `ce0f8fc51d2c` | - (ported, parity 45 cases) |
| `qatr` | L25406-25520 | 115 | `2cded8ebe7da` | - (ported, parity 80 cases) |
| `tfac` | L25765-25813 | 49 | `fe35527fd872` | - (ported, parity 14 cases) |

`munu` (vertical distribution index) and `puffc` are self-contained; `bi`,
`bji` and `bjil` are the reflection-series helpers; `ctrec` is `munu` + a
rotation; `ctsg` dispatches to `ctpar`/`lower`/`upper`/`puffc`. The real-case
branch selection (`MCTADJ=2`, `NHILL=0`, `MSLUG=0`, `MSHEAR=0`, `MPDF=0`)
resolves to the lower-segment kernel, whose remaining inputs are the
`/CTPASS/` state (`Hd`, `zi`, `ppcoef`, plume/slug geometry) and `BI`/`BJIL`.

Status of the round: **`CTSG`/`CTREC`/`MUNU` are located and pinned but not yet
ported**, so the F1 chain still ends at `VCBAR` and the incomparability list
stays at two causes. The next round's port order is now mechanical: `munu` ->
`bi`/`bjil` -> `lower` -> `puffc` -> `ctrec` -> `ctsg` (lower branch), then wire
`VCBAR -> CTSG` and re-run the real receptor grid.

## 2026-10-11 P7L CTSG kernel port: not started; input contract pinned

Round status, stated plainly: the CTSG kernel port (the P7K port order
`munu -> bi/bjil -> lower -> puffc -> ctrec -> ctsg`) was **not started** - the
session budget was consumed by the preceding rounds, so no new code, no parity
evidence and no partial port exist for it. Nothing is approximated or
substituted; the entry point stays exactly as P7K left it.

To make the next round mechanical, the `/CTPASS/` input contract the kernel
needs is recorded here from the vendor declaration
(`engine/vendor/src/CALPUFF_v7.2.1_L150618/ctpass.puf`, real/logical fields):

- timestep and geometry: `sz1, sy1, sz2, sy2, szr, syr` (puff sigmas at the
  start/end of the step and at the receptor), `frac` (fraction of the step from
  the start to the receptor), `twokz, twoky` (diffusivities over the step),
  `t12p, t12rl, t12ru, tstep, tstart, timpg, szimpg, syimpg, szesq, szosq,
  szpsq, szsq`
- puff/receptor positions: `xp, yp, xpf, ypf, zpuff, isc` (puff, in metres
  relative to the met-grid origin), `xr, yr, xrf, yrf, xre, yre, zrec`
  (receptor), `x12f, x23f, xob`
- flow state: `q` (emission), `u` (transport speed), `hd` (dividing-streamline
  height), `ubyn`, `zlid` (lid), `thetaw`, `rotflo`, `rotang`, `alfw, beta,
  cbeta, d, h, baxi, r`, plus the vertical profiles `z(mxlev), ws(mxlev),
  abvf(mxlev)` and `nlev`
- terrain/hill state (unused for this deck, `NHILL=0`): `relief`, `expo`,
  `scale`, `axmax`, `xc`, `yc`, `thetah`, `zgrid`, `hda`, `ubyna`, `ih`, `ip`,
  `ir`, `iregl, iregu`, `mhillt`, `nzh`, `zh`, `majaxw`, `minaxw`, `at`,
  `ntpts`, `xbegin, xend, xspace`
- receptor arrays: `xrctm(mxrect), yrctm(mxrect)`
- diagnostics: `ldb, idebug`

The same discipline as P7H applies: these must become **explicit inputs** of the
ported routines (no hidden common state), and any missing field must fail
closed. `flopuff` (479 lines) belongs to the upper-segment path, which this deck
does not use (`NHILL=0`, puff inside the mixed layer); its call closure still
has to be scanned before deciding whether it is needed at all.

Incomparability causes remain two: the CTSG kernel (not ported), and the
still-prototype puff model plus the CTEAS-only CONC.DAT header.

## 2026-10-12 P7M CTSG kernel ported (MUNU/IREG/BI/BJI/BJIL/SIGMA/CTREC/PUFFC/LOWER/CTSG)

Round status: the P7K port order is now closed for the real-case reachable
kernel. `munu`, `bi`, `bji`, `bjil`, `ireg`, `sigma`, `ctrec`, `puffc`, `lower`
and `ctsg` are ported, and every one of them is compared against the compiled
**unmodified** vendor spans. `ctpar`, `upper` and `flopuff` are NOT ported and
the port fails closed when the vendor would call them.

| unit | vendor span | ported | parity evidence |
|---|---|---|---|
| `munu` (elliptical coordinates) | L24865-24967 | yes | `P7M_MUNU_ORACLE_PARITY` 46 cases x 2 columns, `MAX_REL=1.8e-13` |
| `ireg` (CTSG region index) | L24576-24603 | yes | `P7M_IREG_ORACLE_PARITY` 12 cases, `MAX_REL=0` |
| `bi` (constant-sigma-z reflection) | L22229-22263 | yes | `P7M_BI_ORACLE_PARITY` 36 cases, `MAX_REL=9.4e-07` |
| `bji` (UPPER reflection helper) | L22265-22316 | yes | `P7M_BJI_ORACLE_PARITY` 12 cases, `MAX_REL=2.1e-13` |
| `bjil` (LOWER reflection helper) | L22318-22363 | yes | `P7M_BJIL_ORACLE_PARITY` 24 cases, `MAX_REL=3.0e-13` |
| `sigma` (nearest-known-sigma restart) | L25551-25648 | yes | `P7M_SIGMA_ORACLE_PARITY` 96 cases, `MAX_REL=1.1e-07` |
| `ctrec` (receptor frames + travel times) | L22841-22921 | yes | `P7M_CTREC_ORACLE_PARITY` 12 cases x 10 columns, `MAX_REL=1.7e-13` |
| `puffc` (pole / flat puff sampling) | L25286-25404 | yes | `P7M_PUFFC_ORACLE_PARITY` 12 cases, `MAX_REL=8.9e-08` |
| `lower` (below the dividing streamline) | L24657-24863 | yes | `P7M_LOWER_ORACLE_PARITY` 12 cases, `MAX_REL=1.4e-13` |
| `ctsg` (kernel dispatch, lower branch) | L22923-23112 | yes | `P7M_CTSG_ORACLE_PARITY` 11 cases x 2 columns, `MAX_REL=1.2e-07` |
| `ctpar` / `upper` / `flopuff` | L22505-22839 / L25815-26001 / L23178-23656 | **no** | refused at run time |

`P7M_ORACLE_PARITY_TOTAL_CASES=273` against the compiled unmodified vendor
routines with a fixed `1e-5` relative acceptance bound, **0 mismatches** and a
worst absolute difference of `1.9e-06` (the SIGMA matrix; every other matrix
stays at or below `4.7e-10`). The matrices are driven identically on both sides
and the ported `SIGMA` wrapper is compared against the **unmodified vendor
SIGMA** with a deterministic SIGTY/SIGTZ stub pair that both sides share (the
vendor SIGTY/SIGTZ themselves carry the P7D parity evidence). Linux `gfortran-11`
runs the same matrices in the local gate.

### Source anchor

`reference/p7m_source_anchor.py` locates every unit with the P7K header scan and
pins the spans, SHA-256 and call closure in `reference/p7m_source_anchor.json`;
`--check` additionally cross-checks the nine units P7K already pinned and fails
on any drift. Vendor source
`sha256 da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`.

### Two vendor properties reproduced verbatim (found by the parity test)

1. **`RT2PI` is never initialised.** `RT2PI` is declared in `const.puf`, but
   `CTINIT` (L22365-22503, the only unit that sets `/CONST/`) sets every constant
   except it, and no `DATA` statement in a unit that includes `const.puf` writes
   it either (the five `data ... rt2pi/2.5066283/` statements belong to routines
   that do not include `const.puf`). The original therefore evaluates the "puff
   mixed in the vertical" branch of `LOWER`/`PUFFC`/`UPPER` as
   `fz = rt2pi*sz/zlid = 0`. The port reproduces that zero exactly, the anchor
   manifest records the static proof (`vendor_rt2pi_initialised=false`), and the
   parity test reads `RT2PI` back from the compiled oracle as `0.0`
   (`P7M_CONST_READBACK`).
2. **The `SIGMA` sigma-z branch does not advance the sigma.** The sigma-y branch
   passes the advanced `(DKM, TSEC)` pair to the forward `SIGTY` call, but the
   sigma-z branch passes the *reverse* outputs `(VDZ, VTZ)` to the forward
   `SIGTZ` call and only uses `TSEC` for its positivity test, so
   `SIGMA(2,...)` returns the nearest known sigma-z unchanged. The port mirrors
   this asymmetry (it is what makes the `LOWER` vertical factor behave as the
   original does) and the sigma matrix would fail without it.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7m_ctsg_kernel_contract`: closed forms for MUNU/IREG/BI/BJIL, the SIGMA
  shortcut and both stub-curve closed forms, CTREC frame/travel-time checks, the
  PUFFC no-reflection closed form and its zero branches, the LOWER BI-branch
  closed form, the CTSG dispatch (LOWER, PUFFC(2) and the flat comparison) and
  every fail-closed path (missing curves, invalid modes, CTPAR required, UPPER
  required, zero transport speed). PASS.
- `cteas_p7m_source_parity`: anchor + P7K cross-check + 40 quoted statements +
  `/CONST/` readback + the ten matrices above. PASS (273 cases).
- `cteas_p7m_real_grid_ctsg`: the physical-chain run below. PASS.
- Local `ctest` 22/23 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of
  `cteas_p7_original_case_stage_contract` (PASS on Linux).

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=55cd7c9e2 ok=21 blocked=0 failed=0` with the authoritative
local gate (`python3 scripts/local_gate.py --track p7 --repo /home/lhy/gate/driver`):
`100% tests passed, 0 tests failed out of 23`, including the three new P7M CTest
entries. The same case matrices against the compiled unmodified vendor units with
`GNU Fortran (Ubuntu 11.4.0) 11.4.0`:

```
MUNU  CASES=46 MAX_REL=1.825e-13   BI    CASES=36 MAX_REL=9.433e-07
BJI   CASES=12 MAX_REL=2.057e-13   BJIL  CASES=24 MAX_REL=3.008e-13
SIGMA CASES=96 MAX_REL=3.073e-13   IREG  CASES=12 MAX_REL=0.000e+00
CTREC CASES=12 MAX_REL=1.655e-13   PUFFC CASES=12 MAX_REL=8.851e-08
LOWER CASES=12 MAX_REL=1.422e-13   CTSG  CASES=11 MAX_REL=1.247e-07
TOTAL 273 CASES, MISMATCHES=0
```

The only difference from macOS (gfortran 16.2.0) is the SIGMA matrix, which
tightens from `1.1e-07` to `3.1e-13`; every other matrix is unchanged to the
reported digits.

### Real receptor-grid run (physical chain only)

`cteas_p7m_probe --real-grid MET.DAT puff.inp 0 2.63e13 513.3846439571
3533.7689269678 70.8` moves one synthetic puff one 3600 s step with the locked
case's real met inputs (statics, `U`/`V`/`ZI`/`IPGT`), and samples the **2500
real receptors** with the reconstructed CTSG kernel:

```
P7M_REAL_GRID_CTSG_RUN=PASS HOUR=0 RECEPTORS=2500 STABILITY=4 URBAN=false
  SPEED_MS=1.39612 STEP_KM=5.02603 SIGMA_Y_M=294.387 SIGMA_Z_M=89.1519
  ZI_M=230.977 HILL_RELIEF_M=200 HD_M=120 HILL_OFFSET_KM=2 IMPINGEMENT_S=1432.54
  SYNTHETIC_HILL=true LOWER_BRANCH=230 POLE_BRANCH=2270 SUM=1.17251e+08
  MAX=82400 MIN=0 NONZERO=2499 CFLAT_SUM=2.60874e+07 CFLAT_MAX=46304
  VCBAR_STANDARD_SUM=5.25600e+08 VCBAR_STANDARD_NONZERO=2500
  PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true
```

The locked deck has **`NHILL=0` and `NCTREC=0`**, so CALPUFF never calls CTSG for
it (`lctsg` requires `nctrec > 0`): the deck's concentration path is the ordinary
puff sampling (`CALCPF` with `VCOUP`, the P7E/P7H chain whose vertical factor is
`VCBAR`). The run therefore constructs a documented synthetic hill 2 km downwind
of the stack (relief 200 m, dividing streamline 120 m, 2 km major axis, frame
rotated onto the real flow) so that the lower-segment branch is actually
exercised, and reports the `VCBAR` standard-path sum next to the CTSG sum for
orientation only. **It is not a comparison with the frozen `puff.con`.**

### `VCBAR -> CTSG` is not a vendor call edge (machine-checked)

The CTSG kernel does **not** consume `VCBAR`. The anchored call lists show
`ctsg -> ctpar, ctrec, lower, puffc, upper` and none of the ported units
references `VCBAR`; the only caller of `VCBAR` in the whole vendor source is
`DRY` (`f1=vcbar(jp,mfact0,hlid,ppcoef,lcalmf)`, calpuff.for L26267, the
Gaussian-puff dry-removal branch that P7F listed as not reconstructed). The
anchor manifest therefore records the function-reference callers of `VCBAR` and
`VCOUP` separately from the `call` closure (a `call` scan cannot see
`f=vcbar(...)`), and the parity test asserts
`P7M_VCBAR_CLOSURE=PASS VCBAR_FUNCTION_REFERENCE_CALLERS=dry
CTSG_CONSUMES_VCBAR=false`. What is wired into the F1 chain this round is
therefore: the standard puff path keeps its P7H `VCBAR` vertical factor, and the
terrain path gets the reconstructed CTSG kernel - the two are exercised side by
side on the same real receptor grid below.

### `flopuff` closure scan and case-path verdict

The closure scan is machine-checked by the anchor manifest and asserted by the
parity test (`P7M_CALL_CLOSURE`): `flopuff` <- `path`, `path0`, `upper`;
`path` <- `ctpar`; `upper` <- `ctsg`; `ctpar` <- `ctsg`; `ctsg` <- the main
program. `upper` runs only for receptors above the dividing streamline whose flow
is in the upper region, and `ctpar`/`upper` run only when CTSG runs, which
requires a CTSG hill (`nctrec > 0`). The locked 2022 deck has no hill at all -
read back from the deck itself by the probe
(`LOCKED_DECK_NHILL=0 LOCKED_DECK_NCTREC=0 CTSG_NOT_ON_LOCKED_DECK_PATH=true`) -
so `flopuff` is **not on this case's path** and is not ported; `upper` fails
closed instead of approximating it.

### Correction to the incomparability list

The earlier rounds listed "the CTSG kernel" as one of two causes that make the
frozen `puff.con` incomparable. That was wrong for this deck: with `NHILL=0` and
`NCTREC=0` the vendor's `lctsg` is `.FALSE.` and CTSG is never invoked, so a
missing CTSG kernel never blocked a `puff.con` value comparison. The port is
still required for reconstructing the CTSG feature and for the kernel-parity
obligation, and it is now closed for the real-case reachable units.

**Remaining incomparability cause: one.** The puff model is still the P7C
prototype (no CALPUFF release cadence, split/merge, plume rise, terrain
interaction), and the `CONC.DAT` writer still emits only the CTEAS header
subset, so the frozen `puff.con` values cannot be reproduced or compared yet.
Also still open and explicitly out of this round: `ctpar`/`upper`/`flopuff`,
the slug/wind-shear/PDF options (`MSLUG=0`, `MSHEAR=0`, `MPDF=0` for this deck),
and `MCTADJ=1/3` terrain lookup.

## 2026-10-12 P7N plume rise: the first cut of the advection prototype (on-path)

Round status: the gradual plume-rise path of the locked deck is reconstructed and
parity-checked against the compiled **unmodified** vendor units. The slice was
chosen from the deck's own option set, not from convenience:

| deck option | value | consequence |
|---|---|---|
| `MTRANS` | 1 | gradual (transitional) rise is modelled -> `PRM`/`PRB` are on the path |
| `MTIP` | 1 | stack-tip downwash is modelled -> `STKTIP` is on the path |
| `MRISE` | 1 | Briggs rise (not numerical) -> `PRFIN` + `PRM`/`PRB` are the formulas |
| `MPARTL` | 1 | partial penetration of an elevated inversion -> `PRFPP` is on the path |
| `MSHEAR` | 0 | `PRSHEAR`/`PRFINSH` are **off** this case's path |
| `MSPLIT` | 0 | puff splitting/merging is **off** this case's path |
| `MHFTSZ` | 0 | the Heffter transition (`HEFTRAN`) is **off** this case's path |
| building downwash | none (`IDW0=0`) | `PRSS`, `PRIME` and the tabulated rise are **off** |

That is why this round ports the rise family rather than `split`/`HEFTRAN`: the
release cadence and the rise are the parts of the P7C prototype that actually
drive the locked case's puff heights.

### Ported units and parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| `STKTIP` (stack-tip downwash) | L46904-46947 | yes | 144 cases, `MAX_REL=1.1e-13` |
| `PRB` (transitional buoyant rise) | L46949-46999 | yes | 18 cases, `MAX_REL=0` |
| `PRM` (transitional momentum rise) | L47001-47079 | yes | 48 cases, `MAX_REL=8.5e-14` |
| `PRFIN` (final rise) | L47081-47249 | yes | 288 cases x 6 columns, `MAX_REL=2.0e-07` |
| `PRFPP` (partial penetration) | L48041-48150 | yes | 18 cases x 3 columns, `MAX_REL=5.8e-14` |
| `GRISE` (gradual-rise dispatch) | L47251-47620 | yes | 98 cases x 2 columns, `MAX_REL=3.3e-13` |
| POINTS1 flux statements | L15527-15535 (inline) | yes | 32 cases x 2 columns, `MAX_REL=2.4e-13` |

`P7N_ORACLE_PARITY_TOTAL_CASES=646`, `MISMATCHES=0`, worst absolute difference
`4.6e-05` (the `PRFIN` matrix, whose `**0.25`/`**0.375` powers are constant-folded
differently by the two compilers). `PRSHEAR`, `PRSS`, `PRTAB`, `PRBL` and
`INTERTAB` are provided as hard-failing stubs in the oracle, so a parity case can
never silently reach an unported branch.

### Source anchor

`reference/p7n_source_anchor.py` locates the six routines with the P7K/P7M
header scan and pins their spans, SHA-256, call closure and include list in
`reference/p7n_source_anchor.json`; `--check` fails on any drift. The buoyancy and
momentum flux statements live **inline in `POINTS1`** rather than in a routine, so
they are pinned by content (the `(i)` spelling occurs exactly once) and staged
inside a generated harness subroutine that adds only declarations and the
argument transfer: the three extracted statements stay byte-identical
(`P7N_INLINE_BLOCK=PASS UNIT=points1 LINES=15527-15535 STATEMENTS=3`). Vendor
source `sha256 da40372cab1c181158d0ee5faac16f678e876fc14415073c38c8e3bdabfbc568`.

### Fail-closed deviations (documented, never approximated)

`GRISE` refuses the tabulated/numerical rise (methods 2/3, `MRISE=2`), the shear
correction (`MSHEAR=1`), the building-downwash paths and the area/line/flare
source types instead of returning an invented height; `PRFIN`/`PRM` refuse a
stability class outside 1-6; the flux builder refuses a zero stack temperature;
`PRFPP` refuses a zero ambient temperature. `GRISE`'s vendor "halts on a rise
factor below -1e-4" is reproduced as a refusal.

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=b7052d751 ok=24 blocked=0 failed=0` with the
authoritative local gate, `100% tests passed, 0 tests failed out of 26`
(including the three new P7N CTest entries). The same matrices against the
compiled unmodified vendor units with `GNU Fortran (Ubuntu 11.4.0) 11.4.0`:
STKTIP 144 cases `MAX_REL=1.086e-13`, PRFIN 288x6 `MAX_REL=3.979e-13`, PRM 48
`MAX_REL=8.544e-14`, PRB 18 `MAX_REL=0`, PRFPP 18x3 `MAX_REL=5.797e-14`, FLUX
32x2 `MAX_REL=2.362e-13`, GRISE 98x2 `MAX_REL=3.275e-13` - 646 cases,
`MISMATCHES=0`. The only difference from macOS (gfortran 16.2.0) is PRFIN, which
tightens from `2.0e-07` to `4.0e-13`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7n_plume_rise_contract`: closed forms for STKTIP, the flux pair, PRFIN
  (all four stability/calm branches and the `FM=0` zeroing), PRM (neutral and
  stable), PRB, PRFPP (the three `ZI` branches), the GRISE method-1 assembly, the
  method-0 cavity path, the ground clipping, the `ZFRISE=0` rise fraction and
  every fail-closed path. PASS.
- `cteas_p7n_source_parity`: anchor + inline block + 39 quoted statements + the
  seven matrices. PASS (646 cases).
- `cteas_p7n_locked_case_rise`: the deck run below. PASS.
- Local `ctest` 25/26 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of
  `cteas_p7_original_case_stage_contract` (PASS on Linux).

### Locked-case rise run (physical chain only)

`cteas_p7n_probe --deck-rise MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8 1.6 17.26 298.15` uses the deck's own stack (diameter 1.6 m, exit velocity
17.26 m/s, exit temperature 298.15 K, `FMFAC=1.0`) and the sampled hour's real met
inputs:

```
P7N_DECK_RISE_RUN=PASS HOUR=0 STABILITY=4 SPEED_MS=1.39612 AMBIENT_K=279.15
  ZI_M=230.977 STACK_H_M=70.8 DIAM_M=1.6 VEXIT_MS=17.26 TSTAK_K=298.15
  TEMP_EXCESS_K=19.0 FLUXB=6.90346 FLUXM=178.511 TIPDW_M=0
  XFIN_M=163.913 ZFIN_M=65.3579 ZFIN_MOMENTUM_M=59.3416 ZFIN_BUOYANCY_M=65.3579
  FMIX=1 ZFIN_PARTIAL_M=65.3579 PLUME_HEIGHT_M=136.158
  PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true
P7N_DECK_GRADUAL_RISE X_M=100    HEIGHT_M=125.103 RISE_FRACTION=0.830855
P7N_DECK_GRADUAL_RISE X_M=500    HEIGHT_M=136.158 RISE_FRACTION=1
P7N_DECK_GRADUAL_RISE X_M=5026.03 HEIGHT_M=136.158 RISE_FRACTION=1
```

i.e. the buoyant rise (65.36 m) exceeds the momentum rise (59.34 m), the stack-tip
downwash is zero because the exit velocity is well above `1.5*WSSTK`, the plume
reaches its final height of 136.16 m within ~500 m, and the locked hour's 5.03 km
step samples a fully developed plume. Two assumptions are stated in the output
path and in the code: the sampled hour is neutral/unstable (class 4, so the stable
branches that need the potential-temperature gradient are not exercised - the run
fails closed for `ISTAB >= 5`), and the `MPARTL=1` revision uses the vendor's
default gradient path (`PTGRAD0=0.005`, `JSUP=5` -> `PTGINV=0.020 K/m`,
`DPTINV=0.6 K`) because `PTLAPS`/`LCALGRD` are not reconstructed. This is a
physical-chain demonstration, **not** a comparison with the frozen `puff.con`.

### Precise gaps and the next-round entry point

1. **Release cadence and the per-puff rise state** (`points1`/`setpuf`): the
   *origin* of `FM`/`FB`/`XFIN*`/`ZFIN*`/`STIPDW`/`WS0`/`ISTAB0`/`SQRTS0` and the
   emission schedule (`NSECDT`, puff ages, `TMTOTB`/`TMTOTE`) are still inline in
   `points1` (L15505-16150) and `setpuf` (L48198-48757). The flux statements and
   `PRFIN`/`STKTIP` are ported, so the next round is the *scheduler*: when a puff
   is released, with what mass, and which `SQRT(S)`/`DPBL`/`PTGINV` the vendor
   uses at release (`SQRT(S)=SQRT(g*ptgrad/t0)`, `ptgrad` from the met profile or
   `PTGRAD0`, plus `JSUP`/`PTG(1:2)`).
2. **`PTLAPS`/`LCALGRD`** (met-model inversion gradient, L18421-18559) is needed
   before the stable branches and the met-based `PTGINV` can be exercised.
3. **Advection/step integration** is still the P7C prototype; `SIGMA()`
   restart/`HEFTRAN` semantics for `MHFTSZ=1` and the `split`/merge path
   (`MSPLIT=1`, `split` L11952-12424) remain unported but are off this deck.

### Incomparability list after this round

**Still one cause**, now narrowed: the puff model is still the P7C prototype
(release cadence, step integration and split/merge) plus the CTEAS-only
`CONC.DAT` header. The plume-rise component of that prototype is no longer a gap
for the locked deck: its gradual-rise path (`MTRANS=1`/`MTIP=1`/`MRISE=1`/
`MPARTL=1`) is reconstructed with original-source parity, and the P7M CTSG finding
stands (no hill in this deck, so CTSG is never invoked). Explicitly out of scope
and off this case's path: `MSHEAR=1`, `MSPLIT=1`, `MHFTSZ=1`, building downwash
and the numerical rise.

## 2026-10-12 P7O release scheduler: the second cut of the advection prototype

Round status: the release scheduler of the locked deck's constant point source is
reconstructed and parity-checked against the compiled **unmodified** vendor
source. The slice is the "release time / age / mass / initial rise state" chain
that P7N named as its entry point.

### Ported units and parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| `INJECT` (release mass split + puff code) | L18561-18696 | yes | 2592 cases x 10 columns, `MAX_REL=0` (bit-exact) |
| POINTS1 release cadence (inline) | L15975-16002 | yes | 108 cases x 3 columns, `MAX_REL=0` (bit-exact) |
| POINTS1 release-time state (inline) | L16120-16176 | yes | 32 cases x 46 columns, `MAX_REL=4.3e-08` |
| puff-age rule | SWAP L19366 + SETPUF L48718 | yes | pinned statements, machine-checked |

`P7O_ORACLE_PARITY_TOTAL_CASES=2732`, `MISMATCHES=0`. The two inline blocks are
extracted **verbatim** (19 and 46 statements) and staged inside generated harness
subroutines that add only declarations and the argument transfer; the anchor
records their spans and SHA-256. `ROLLDN` (array roll-down) is a hard-failing stub
in the oracle, and the port refuses the unported paths instead of guessing.

### What the vendor actually does (findings from the anchor)

1. **Release cadence**: `NPUFFS = min(max(INT(WSNEW*XTMP1(MD)) + 1, 1), MXNEW)` and
   each puff is emitted over `DT = DHR/NPUFFS` seconds. With the deck's stack and
   the sampled hour (`WSNEW` = 1.396 m/s, `XTMP1` = 1.0 because `NSPT1 = 0`) this
   is **2 puffs per hour, each carrying 1800 s of emission** - not the "one puff
   per step" of the P7C prototype. `WSNEW` is `max(WS, W at the final rise)` from
   `RLSMET`; `RLSMET` is not reconstructed, so the port takes the release wind as
   an explicit input and the run reports that it used the stack-height wind.
2. **Puff age**: for a constant point source `TMTOTB` is *not* assigned in
   POINTS1. `SWAP(i,0)` zeroes it when the puff is created (L19366) and `SETPUF`
   adds `TSAMP` every step (L48718), so a puff released during the current step
   has age 0 and grows by the sampling step. The age rule is ported and pinned;
   `SETPUF`'s per-step state update is the next round's entry point.
3. **Release mass**: `INJECT` puts `Q*DT` into the mixed layer, into the layer
   above, or splits it by `FMIX` for partial penetration, and sets the puff code
   (`1/2` Gaussian/uniform in the mixed layer, `3/4` above, `5/6` split, plus
   `MFACT0` for the slug forms; a stable source above the lid is treated as
   unlimited mixing with `ZIMAX = ZIOLD = 10 000 m`).

### Locked-case release run (physical chain only)

`cteas_p7o_probe --deck-release MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8 1.6 17.26 298.15 8.34e5` runs the reconstructed rise (P7N) and release (P7O)
chains for the deck's stack and the sampled hour:

```
P7O_DECK_RELEASE_RUN=PASS HOUR=0 STABILITY=4 SPEED_MS=1.39612 ZI_M=230.977
  PLUME_HEIGHT_M=136.158 PUFFS_PER_HOUR=2 EMISSION_DURATION_S=1800 MGAUSS=1
  PUFF_CODE=1 ZIMAX_M=230.977 ZIOLD_M=230.977 QM_H3_BQ=1501200000 QU_H3_BQ=0
  QM_HE3_BQ=0 QU_HE3_BQ=0 STEP_S=3600 AGE_AFTER_ONE_STEP_S=3600
  RELEASE_WIND_IS_STACK_WIND=true RLSMET_NOT_RECONSTRUCTED=true
  PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true
```

i.e. the deck releases 2 puffs per hour, each carrying 1800 s of emission =
1.5012e9 Bq of H-3 (and none of HE-3, matching the deck's `0.000E+00` second
emission rate), entirely within the mixed layer (code 1), from a plume that has
risen to 136.16 m, with the first step advancing the puff age from 0 to 3600 s.

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=3b26812cc ok=27 blocked=0 failed=0` with the
authoritative local gate, `100% tests passed, 0 tests failed out of 29`
(including the three new P7O CTest entries). The same matrices against the
compiled unmodified vendor source with `GNU Fortran (Ubuntu 11.4.0) 11.4.0` are
identical to macOS: `INJECT` 2592 cases `MAX_REL=0` (bit-exact), cadence 108 cases
`MAX_REL=0` (bit-exact), release-time state 32 cases x 46 columns
`MAX_REL=4.310e-08` - 2732 cases, `MISMATCHES=0`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7o_release_scheduler_contract`: cadence closed forms (including the
  calm hour, the `MXNEW` cap and the interval scaling), all five `INJECT`
  branches and codes, the release-time state field mapping, the age rule and every
  fail-closed path. PASS.
- `cteas_p7o_source_parity`: anchor + two inline blocks + the age pins + 27 quoted
  statements + the three matrices. PASS (2732 cases).
- `cteas_p7o_locked_case_release`: the deck run above. PASS.
- Local `ctest` 28/29 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of `cteas_p7_original_case_stage_contract`
  (PASS on Linux).

### Precise gaps and the next-round entry point

1. **`SETPUF`** (L48198-48757, 560 lines) is the per-step puff update: distances
   and travel times, the receptor-independent sigma update (`SETCSIG`), the rise
   table / `WAKE_TAB` handling, the `MCTADJ=2` height adjustment, gravitational
   settling and the `TMTOTB` increment. This is now the single largest missing
   piece of the puff model and the natural next slice; the release-time state it
   consumes is already ported and pinned.
2. **`RLSMET`** (L18172-18379) supplies `WSNEW` (the wind at the final rise) and
   the `MFACT0` determination for `METFM=1/4/5`; without it the release wind is a
   caller input (as the deck run states).
3. **`PTLAPS`/`LCALGRD`** (L18421-18559) is still needed before the stable rise
   branches (`ISTAB >= 5`) and the met-based `PTGINV` can be exercised.
4. **`SWAP`/`ROLLDN`** (L19217-19433 / L19110-19216) manage the puff arrays; the
   port models a single release set and leaves array management to the caller.

### Incomparability list after this round

**Still one cause, narrowed again**: the puff model is still the P7C prototype -
now reduced to `SETPUF`'s per-step state update (and the advection step around it)
plus the CTEAS-only `CONC.DAT` header. Both the plume-rise path (P7N) and the
release scheduler (P7O) of the locked deck are reconstructed with original-source
parity. Explicitly out of scope and off this case's path: `MSHEAR=1`, `MSPLIT=1`,
`MHFTSZ=1`, building downwash, the numerical rise and (for the locked deck) CTSG.

## 2026-10-12 P7P SETPUF step bookkeeping and SETCSIG

Round status: the per-step bookkeeping of `SETPUF` - the piece P7O named as its
entry point - is reconstructed and parity-checked against the compiled
**unmodified** vendor source, together with the `/CSIGMA/` selection state.

### Ported units and parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| SETPUF step bookkeeping (inline) | L48373-48399 | yes | 320 cases x 13 columns, `MAX_REL=3.4e-08` |
| SETPUF state update (inline) | L48706-48723 | yes | 64 cases x 6 columns, `MAX_REL=4.2e-13` |
| `SETCSIG` (/CSIGMA/ selection) | L52504-52619 | yes | 32 cases x 22 columns, `MAX_REL=2.0e-08` |

`P7P_ORACLE_PARITY_TOTAL_CASES=416`, `MISMATCHES=0`. Both inline blocks are
extracted **verbatim** (16 and 10 statements) into generated harnesses; the
`TMTOTB` increment (L48718), the `XTOTB` increment (L48717) and the end-of-step
position store (L48723) are pinned by line as well. `TAULY` is a hard-failing
stub in the oracle (`MTAULY=1` is off this deck) and `SETCSIG`'s SIGTY call is
exercised through a deterministic curve pair that both sides share (the vendor
curves themselves carry the P7D parity evidence).

### What the block does (and what it deliberately does not)

The step bookkeeping sets the travel distance and time at the begin/end of the
step, the midpoint distance/time, the mean transport speed and its km/s form, and
the CALM determination: below `WSCALM` the sigma-v/w dispersion options are forced
to 1 and both the downwash code and the final-rise distance are cleared. The
state update applies gravitational settling **only when `MTILT=1`** (the deck has
`MTILT=0`, so the settling term is read but never applied), then advances
`XTOTB`/`TMTOTB` and stores the end-of-step position. `SETCSIG` copies its
arguments into `/CSIGMA/`, conditions the stability class to 6, and computes the
Heffter transition pair with `SIGTY(SYH,0,0)`.

Not reconstructed and refused by the callers: `SETPUF`'s sigma update (the
`SIGTY`/`SIGTZ` calls with their virtuals at the start/midpoint/end of the step
and the `MHFTSZ=1` Heffter branch), the rise-table/`WAKE_TAB` handling, the
`MCTADJ=2` height adjustment (`CTADJ2`, L20542-20835) and the PRIME wake
treatment; `TAULY` and `MTAULY=1`.

### Locked-case step run (physical chain only)

`cteas_p7p_probe --deck-step MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8` runs the reconstructed step bookkeeping and `/CSIGMA/` selection for the
sampled hour:

```
P7P_DECK_STEP_RUN=PASS HOUR=0 STABILITY=4 URBAN=false SPEED_MS=1.39612
  ZI_M=230.977 STEP_S=3600 STEP_DISTANCE_M=5026.03 CALM=false UAVG_MS=1.39612
  UKPS=0.00139612 XTTB1_M=0 XTTE1_M=5026.03 TB1_S=0 TE1_S=3600 DMIDKM=2.51301
  TMID_S=1800 IDOPTYS=3 IRUS=0 KSTABS=4 SZH_M=550 THFTY_S=7257.12
  DHFTY_KM=10.1318 XPB_KM=511.063 YPB_KM=3538.227 ZPB_M=70.8 XTOTB_M=5026.03
  TMTOTB_S=3600 SIGMA_UPDATE_NOT_RECONSTRUCTED=true PHYSICAL_CHAIN_ONLY=true
  NOT_A_PUFF_CON_COMPARISON=true
```

i.e. the locked hour is not calm, the puff advances 5.026 km in 3600 s, the
midpoint is at 2.513 km / 1800 s, the dispersion option stays at the deck's
`MDISP=3`, and the Heffter transition for this environment is `THFTY=7257 s`
(`DHFTY=10.13 km`) with `SZH=550 m` from the deck's `SYTDEP`. This is a
physical-chain demonstration, **not** a comparison with the frozen `puff.con`.

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=ca991a3b7 ok=27 blocked=0 failed=0` with the authoritative
local gate, `100% tests passed, 0 tests failed out of 32` (including the three new
P7P CTest entries). The same matrices against the compiled unmodified vendor
source with `GNU Fortran (Ubuntu 11.4.0) 11.4.0` are identical to macOS: step
bookkeeping 320x13 `MAX_REL=3.426e-08`, state update 64x6 `MAX_REL=4.213e-13`,
`SETCSIG` 32x22 `MAX_REL=1.981e-08` - 416 cases, `MISMATCHES=0`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7p_step_bookkeeping_contract`: closed forms for the step bookkeeping
  (including the calm override of the dispersion options, the downwash/rise
  clearing and the midpoint terms), the state update with and without `MTILT`, the
  ground clipping, the `/CSIGMA/` selection and the Heffter pair, and every
  fail-closed path. PASS.
- `cteas_p7p_source_parity`: anchor + two inline blocks + the three pinned
  statements + 32 quoted statements + the three matrices. PASS (416 cases).
- `cteas_p7p_locked_case_step`: the deck run above. PASS.
- Local `ctest` 31/32 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of `cteas_p7_original_case_stage_contract`
  (PASS on Linux).

### Precise gaps and the next-round entry point

1. **`SETPUF`'s sigma update** (L48434-48667): the `SIGTY`/`SIGTZ` calls at the
   start/midpoint/end of the step with their virtuals, the PRIME `WAKE_TAB`
   branch, the `MHFTSZ=1` Heffter branch (`HEFTRAN`) and the sigma-z enhancement
   terms. This is now the largest remaining piece of the puff model; the
   bookkeeping it consumes, the curves (`SIGTY`/`SIGTZ`, P7D), the `SIGMA()`
   restart wrapper (P7M) and the `/CSIGMA/` state (this round) are all ported.
2. **`CTADJ2`** (L20542-20835) is the `MCTADJ=2` height adjustment and
   **`WAKE_TAB`** (L78403-78541) the PRIME wake table; both are off this deck
   (no building) but are needed for a general puff step.
3. **`RLSMET`** (L18172-18379) and **`PTLAPS`/`LCALGRD`** (L18421-18559) remain the
   prerequisites for the met-based `WSNEW` and the stable rise branches.

### Incomparability list after this round

**Still one cause, narrowed again**: the puff model is still the P7C prototype -
now reduced to `SETPUF`'s sigma update (plus the advection step around it) and the
CTEAS-only `CONC.DAT` header. The release scheduler (P7O), the plume-rise path
(P7N), the step bookkeeping and `/CSIGMA/` selection (this round) all carry
original-source parity. Explicitly out of scope and off this case's path:
`MSHEAR=1`, `MSPLIT=1`, `MHFTSZ=1`, `MTILT=1`, building downwash, the numerical
rise and (for the locked deck) CTSG.

## 2026-10-12 P7Q SETPUF's sigma update (non-PRIME branch)

Round status: the sigma update of `SETPUF` - the last piece P7P named - is
reconstructed for the deck's path and parity-checked against the compiled
**unmodified** vendor blocks.

### Ported units and parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| begin/mid/end sigma + virtuals (inline) | L48505-48536 | yes | 192 cases x 18 columns, `MAX_REL=8.5e-08` |
| sigma-y final adjustments (inline) | L48570-48604 | yes | 144 cases x 6 columns, `MAX_REL=2.6e-13` |
| sigma-z final adjustments (inline) | L48635-48668 | yes | 72 cases x 5 columns, `MAX_REL=2.2e-13` |

`P7Q_ORACLE_PARITY_TOTAL_CASES=408`, `MISMATCHES=0`. All three blocks are
extracted **verbatim** (15, 12 and 11 statements) into generated harnesses, and
the pieces this round does not port are pinned by line: the PRIME wake branch
(`WAKE_TAB`, L48445), the `MCTADJ=2` valley constraint (`WALLTRAP`, L48551) and
strain (`CTADJ2`, L48622), plus the two sigma stores (`SIGYB` L48574, `SIGZB`
L48639). The dispersion curves are injected (SIGTY/SIGTZ carry the P7D parity
evidence) through a deterministic pair both sides share.

### Semantics worth recording

1. The begin/mid/end chain advances the sigmas with the step's half-distance and
   half-time: the start-of-step sigma is converted to its virtual pair, the
   midpoint is evaluated at `(vty+tmid, vdy+dmidkm)` and the end at
   `(tm+tmid, dm+dmidkm)` - note that the end uses the midpoint's **time
   argument**, not its virtual time.
2. Sigma-z is carried through unchanged unless the puff is Gaussian in the
   vertical (`mod(ICODE,2) == 1`); in that case the sigma-z virtuals are
   *undefined* (stale) in the vendor, so the harness pre-zeroes them to make the
   comparison well defined and the port returns zeros.
3. The final adjustments enforce "sigmas must grow with time", store the
   end-of-step sigma for the next step **before** adding the BID/SY0 quadrature,
   then grow the reported sigmas by `sqrt(sigma**2 + sysq)` (sigma-y) and
   `sqrt(sigma**2 + BIDFNL)` (sigma-z), and finally set the calm minimum sigmas
   to the adjusted midpoint values.

### Locked-case sigma run (physical chain only)

`cteas_p7q_probe --deck-sigma MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8 1.0 1.0 100.0` runs the reconstructed sigma update for the deck's puff over
the sampled step with the real met environment:

```
P7Q_DECK_SIGMA_RUN=PASS HOUR=0 STABILITY=4 URBAN=false SPEED_MS=1.39612
  STEP_S=3600 STEP_DISTANCE_KM=5.02603 SIGMA_Y_START_M=1 SIGMA_Z_START_M=1
  SYB1_M=1 SYM1_M=157.919 SYE1_M=294.387 SZB1_M=1 SZM1_M=58.3502
  SZE1_M=89.1519 VTYE1_S=3607.48 VDYE1_KM=5.03647 VTZE1_S=3612.23
  VDZE1_KM=5.04311 SIGYB_STORED_M=294.387 SIGZB_STORED_M=89.1519 SYSQ_M2=100
  DECK_MCTADJ=2 MCTADJ2_ADJUSTMENTS_OMITTED=true
  PRIME_WAKE_NOT_RECONSTRUCTED=true PHYSICAL_CHAIN_ONLY=true
```

The end-of-step sigmas (294.39 m / 89.15 m) match the independent P7N deck run
(`SIGMA_Y_M=294.387`, `SIGMA_Z_M=89.1519`), which is a useful cross-check between
the two rounds. The sigma update is a **per-puff** quantity: the 2500-receptor
grid enters only through the sampling (P7E), so no per-receptor sigma exists to
report. The deck selects `MCTADJ=2`, whose strain (`CTADJ2`) and valley
(`WALLTRAP`) adjustments are NOT reconstructed; the run says so explicitly rather
than hiding the difference. This is a physical-chain demonstration, **not** a
comparison with the frozen `puff.con`.

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=539aa11b1 ok=33 blocked=0 failed=0` with the authoritative
local gate, `100% tests passed, 0 tests failed out of 35` (including the three new
P7Q CTest entries). The same matrices against the compiled unmodified vendor
blocks with `GNU Fortran (Ubuntu 11.4.0) 11.4.0`: begin/mid/end 192x18
`MAX_REL=3.991e-13` (vs `8.5e-08` on macOS, the same compiler constant-folding
difference seen in P7N/P7O), sigma-y 144x6 `MAX_REL=2.648e-13`, sigma-z 72x5
`MAX_REL=2.166e-13` - 408 cases, `MISMATCHES=0`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7q_sigma_update_contract`: the begin/mid/end closed forms (including the
  time-argument subtlety and the uniform-vertical shortcut), the precision
  monotonicity fix, the store-before-quadrature ordering, the BID/SY0 quadrature,
  the calm minima and every fail-closed path. PASS.
- `cteas_p7q_source_parity`: anchor + three inline blocks + the five pinned
  statements + 26 quoted statements + the three matrices. PASS (408 cases).
- `cteas_p7q_locked_case_sigma`: the deck run above. PASS.
- Local `ctest` 34/35 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of `cteas_p7_original_case_stage_contract`
  (PASS on Linux).

### Precise gaps

1. **`MCTADJ=2` strain and valley constraints** (`CTADJ2` L20542-20835,
   `WALLTRAP` L21745-21894) are on this deck's path and are the largest remaining
   omission of the sigma update. `CTADJ2` adjusts the sigma-z by a strain factor
   over the step and `WALLTRAP` constrains sigma-y in valleys; both need the
   /GRID/ terrain state.
2. **The PRIME wake branch** (`WAKE_TAB` L78403-78541, `IDW0` 3/4) is off this
   deck (no building) but is needed for a general puff step.
3. **`MHFTSZ=1`** (`HEFTRAN` L52621-52768) is off this deck; P7D already refuses
   the Heffter sigma-z transition.
4. `SETPUF`'s remaining tail (the `/CURRENT/` transfer, `ZFINAL`/`ZFRISE`, the
   settling with `MTILT=1`) is covered by P7P for the counters and the position;
   the `/CURRENT/` publication is still open.

### Incomparability list after this round

**Still one cause, narrowed to its smallest form so far**: the puff model is still
the P7C prototype, now reduced to (a) the `MCTADJ=2` strain/valley adjustments of
the sigma update and (b) the overall fidelity of the advection/step integration
(no release-cadence-to-concentration end-to-end run yet), plus the CTEAS-only
`CONC.DAT` header. The release scheduler (P7O), the plume rise (P7N), the step
bookkeeping and `/CSIGMA/` selection (P7P) and the sigma update (this round) all
carry original-source parity, and the two independent deck runs agree on the
end-of-step sigmas.

## 2026-10-12 P7R MCTADJ=2 terrain constraints (CTADJ2 + WALLTRAP)

Round status: the two MCTADJ=2 constraints that P7Q left open - both on the locked
deck's path - are reconstructed and parity-checked against the compiled
**unmodified** vendor units.

### Ported units and parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| `CTADJ2` (strain + stable-flow height change) | L20542-20835 | yes | 432 cases x 4 columns, `MAX_REL=5.9e-07` |
| `WALLTRAP` (valley sigma-y limit) | L21745-21894 | yes | 144 cases x 2 columns, `MAX_REL=4.4e-14` |

`P7R_ORACLE_PARITY_TOTAL_CASES=576`, `MISMATCHES=0`. Both units are extracted whole
and compiled unmodified; the oracle driver supplies deterministic `GETCELL`/
`GETELEV` stubs and fills the `/GRID/` (`relief(5,...)`, `ivalw(...)`, `dzval`) and
`/METHD/` (`elev`, `xgridm`) state from the case line, while the port takes the
same lookups as explicit dependencies (`TerrainLookup`) and fails closed when one
is missing. The terrain-state producer `TRELIEF` (L21205-21545, calls `TERAVG`)
and the lookups `GETCELL` (L82482-82742) / `GETELEV` (L21098-21203) are pinned in
the anchor as the documented next entry point.

### Semantics worth recording

1. `CTADJ2` conditions `R` to at most one, picks the relief corner from the step's
   bearing (N-S / NE-SW / EW / SE-NW at the 22.5 and 67.5 degree tangents), and
   only adjusts the puff height when the flow is upslope with stratification;
   `FRACZ` is **not** clamped - it can be negative (the dividing streamline lies
   above the start elevation) or exceed one (the puff height is then reduced by the
   full rise).
2. `WALLTRAP` first checks the puff against the dividing-streamline elevation, then
   requires a valley-width table (`IVALW`) for both ends and both bracketing
   levels; a single `-1` disables trapping. The trapping ratio is `RCRIT = 0.4`
   with the full/partial/none branches (`SYE = SYB` for full trapping and a linear
   crossing for partial).
3. Both routines read the terrain through the met-grid-unit lookups, which is why
   the port's lookups are called with met-grid coordinates (the deck run initially
   sampled the wrong point until this was fixed).

### Locked-case terrain run (physical chain only)

`cteas_p7r_probe --deck-terrain MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8 89.152 0.9 1.396 0.02` drives the constraints with the deck's real CALMET
elevation field (decoded by P7G):

```
P7R_DECK_TERRAIN_RUN=PASS HOUR=0 MCTADJ=2 ZI_M=230.951 DX_M=100 ELEV_MIN_M=25
  ELEV_MAX_M=59.5 PUFF_HEIGHT_M=70.8 SIGMA_Z_START_M=89.152 ELEV_OLD_M=47.7415
  ELEV_NEW_M=45.7526 DELX_M=5025.6 SIGMA_RATIO=0.9 SPEED_MS=1.396 BVF=0.02
  STRAIN=1.00649 ZPNEW_M=70.8 FRACZ=0 UPSLOPE=false WALLTRAP_TRAPPED=false
  WALLTRAP_SYE_M=200 TRELIEF_STANDIN=true VALLEY_TABLE_ABSENT=true
  PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true
```

Two stand-ins are stated in the output: `TRELIEF`'s directional relief is replaced
by the local drop from the surrounding peak to the cell elevation (computed from
the real field) and the valley-width table is absent (`IVALW = -1`), so `WALLTRAP`
reports no trapping. For this hour the step is nearly level and downslope
(-1.99 m over 5025.6 m), so the strain is small (1.0065) and the puff height is
unchanged. This is a physical-chain demonstration, **not** a comparison with the
frozen `puff.con`.

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=4138760ba ok=36 blocked=0 failed=0` with the authoritative
local gate, `100% tests passed, 0 tests failed out of 38` (including the three new
P7R CTest entries). The same matrices against the compiled unmodified vendor units
with `GNU Fortran (Ubuntu 11.4.0) 11.4.0`: CTADJ2 432x4 `MAX_REL=7.563e-08` (vs
`5.9e-07` on macOS), WALLTRAP 144x2 `MAX_REL=4.355e-14` - 576 cases,
`MISMATCHES=0`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7r_terrain_constraints_contract`: the `CTADJ2` degenerate case, the
  upslope/stratified branch, the neutral branch, the `R` conditioning and every
  fail-closed path; `WALLTRAP`'s no-stratification, full, partial and no-trapping
  branches, the above-dividing-streamline case, the missing-valley-table case and
  every fail-closed path. PASS.
- `cteas_p7r_source_parity`: anchor + the pinned `TRELIEF`/`GETCELL`/`GETELEV`
  spans + 36 quoted statements + the two matrices. PASS (576 cases).
- `cteas_p7r_locked_case_terrain`: the deck run above. PASS.
- Local `ctest` 37/38 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of `cteas_p7_original_case_stage_contract`
  (PASS on Linux).

### Precise gaps

1. **`TRELIEF`** (L21205-21545, 341 lines) builds `relief(1..5)` and `ivalw(...)`
   from the CALMET elevation grid; without it the deck run uses the documented
   relief stand-in and has no valley widths. It is the last piece needed for the
   terrain constraints to run on fully original inputs.
2. **`GETCELL`/`GETELEV`** (the vendor's own lookups, incl. nested grids) are
   replaced by explicit callables; the vendor versions remain unported.
3. `SETPUF`'s `/CURRENT/` publication tail (`xb1/yb1/xe1/ye1`, `bidsq`,
   `xfrise/zfrise`, `xshift`, `speedi/srat`, `temis`, `iage`) is still open.

### Incomparability list after this round

**Still one cause, now at its narrowest**: the puff model's remaining gap is the
overall fidelity of the advection/step integration (no release-cadence-to-
concentration end-to-end run yet), the `TRELIEF` terrain-state producer and the
CTEAS-only `CONC.DAT` header. Every other on-path piece of the puff step now
carries original-source parity: release scheduler (P7O), plume rise (P7N), step
bookkeeping and `/CSIGMA/` (P7P), the sigma update (P7Q) and the MCTADJ=2 terrain
constraints (this round), with CTSG closed earlier (P7M) and off this deck.

## 2026-10-12 P7S terrain-state producers (TERAVG + TRELIEF + GETELEV)

Round status: the terrain-state producers that P7R named as its entry point are
reconstructed and parity-checked against the compiled **unmodified** vendor units,
so the MCTADJ=2 path now runs on real, original relief.

### Ported units and parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| `TERAVG` (45-degree strip average) | L21547-21743 | yes | 652 cases x 1 column, `MAX_REL=2.1e-13` |
| `TRELIEF` (relief corners + peak per cell) | L21205-21545 | yes | 16 cases x 45 columns, `MAX_REL=0` (bit-exact) |
| `GETELEV` (bilinear elevation interpolation) | L21098-21203 | yes | 96 cases x 1 column, `MAX_REL=0` (bit-exact) |

`P7S_ORACLE_PARITY_TOTAL_CASES=764`, `MISMATCHES=0`. The oracle driver fills
`/METHD/` (`elev`, `nxm`, `nym`) and `/GRIDNEST/` (`nestfac = 1`,
`rnxnest0 = rnynest0 = 0` for the single non-nested domain) from the case line and
stubs `GETCELL`; the port takes the elevation grid as a 1-based accessor and the
domain size/nesting as explicit inputs. `GETCELL` (L82482-82742) and `VWIDTH`
(L21896-22178, the valley-width table producer, which calls nothing) are pinned in
the anchor as the remaining gaps.

### Semantics worth recording

1. `TERAVG` is defined only for the four sector orientations (axis or diagonal);
   the vendor leaves `ELAVG` untouched for anything else, which the port refuses.
   The NE/SW and NW/SE branches also sum the "half-step" cells at doubled indices,
   which the port reproduces.
2. `TRELIEF` walks each of the four orientations in both directions, accumulating
   the average-elevation change while the slope ratio stays within `BETA = 1.0`
   of the first step, then combines them with the `rplus`/`rminus` rule and takes
   the peak as `elev + max(reliefi, -reliefd)` over all orientations.
3. `GETELEV` resolves the domain, applies the nested-grid scaling (1 and 0 for a
   single domain) and interpolates bilinearly between cell centres.

### Locked-case relief run (physical chain only)

`cteas_p7s_probe --deck-relief MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8 89.152 0.9 1.396 0.02` runs the ported `TRELIEF` over the deck's real CALMET
elevation field and feeds the result into the MCTADJ=2 constraints:

```
P7S_DECK_RELIEF_RUN=PASS HOUR=0 NX=50 NY=50 DX_M=100 ZI_M=230.951
  CELL_I=25 CELL_J=25 RELIEF_NS_M=2 RELIEF_NESW_M=13.8 RELIEF_EW_M=7
  RELIEF_SENW_M=4 RELIEF_PEAK_M=50.5 ELEV_CELL_M=47 STRAIN=1.00882
  ZPNEW_M=70.8 FRACZ=0 UPSLOPE=false TRELIEF_STANDIN=false
  VWIDTH_NOT_RECONSTRUCTED=true VALLEY_TABLE_ABSENT=true
  PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true
```

**`TRELIEF_STANDIN=false`**: the relief corners are the vendor algorithm's own
values from the real elevation field, so the P7R stand-in is gone. The strain for
this hour is `1.00882` (a small real-terrain value). `WALLTRAP` still reports no
trapping because `VWIDTH` (the valley-width table) is not reconstructed, and the
run says so explicitly. This is a physical-chain demonstration, **not** a
comparison with the frozen `puff.con`.

### Gate evidence (Linux, lhy-desktop, g++-12 + gfortran-11)

`LOCAL_GATE_P7=PASS sha=66b47e173 ok=39 blocked=0 failed=0` with the authoritative
local gate, `100% tests passed, 0 tests failed out of 41` (including the three new
P7S CTest entries). The same matrices against the compiled unmodified vendor units
with `GNU Fortran (Ubuntu 11.4.0) 11.4.0` are **identical to macOS**: TERAVG 652x1
`MAX_REL=2.068e-13`, TRELIEF 16x45 `MAX_REL=0` and GETELEV 96x1 `MAX_REL=0` -
764 cases, `MISMATCHES=0`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7s_terrain_state_contract`: `TERAVG`'s four orientations on flat, ramp
  and degenerate sectors plus the invalid-direction refusal; `TRELIEF`'s flat and
  ramp relief with the peak; `GETELEV`'s flat, ramp, single-cell and
  half-cell-centre cases plus every fail-closed path. PASS.
- `cteas_p7s_source_parity`: anchor + the pinned `GETCELL`/`VWIDTH` spans + 26
  quoted statements + the three matrices. PASS (764 cases).
- `cteas_p7s_locked_case_relief`: the deck run above. PASS.
- Local `ctest` 40/41 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of `cteas_p7_original_case_stage_contract`
  (PASS on Linux).

### Precise gaps

1. **`VWIDTH`** (L21896-22178, 283 lines) builds `ivalw`/`dzval` from the relief
   grid; without it `WALLTRAP` reports no trapping. It is the last piece of the
   MCTADJ=2 path and is pinned in the anchor.
2. **`GETCELL`** (L82482-82742) resolves the met domain (including nested grids);
   the port takes the domain size and nesting explicitly instead.
3. `SETPUF`'s `/CURRENT/` publication tail (`xb1/yb1/xe1/ye1`, `bidsq`,
   `xfrise/zfrise`, `xshift`, `speedi/srat`, `temis`, `iage`) is still open.

### Incomparability list after this round

**Still one cause**: the overall fidelity of the advection/step integration (no
release-cadence-to-concentration end-to-end run yet), the `VWIDTH` valley table
and the CTEAS-only `CONC.DAT` header. The terrain path is now original end to end
except for `VWIDTH`, and every other on-path piece (release scheduler P7O, plume
rise P7N, step bookkeeping and `/CSIGMA/` P7P, sigma update P7Q, MCTADJ=2
constraints P7R, terrain state P7S) carries original-source parity.

## 2026-10-12 P7T VWIDTH: the valley-width table (VALLEY_TABLE_ABSENT cleared)

Round status: `VWIDTH` (calpuff.for L21896-22178), the producer of the `/GRID/`
valley-width table `ivalw(mxvalz,...)` and `dzval` that `WALLTRAP` consumes, is
reconstructed and parity-checked against the compiled **unmodified** vendor unit.

### Parity evidence

| unit | vendor span | ported | parity |
|---|---|---|---|
| `VWIDTH` (valley widths + layer thickness) | L21896-22178 | yes | 20 cases x 251 columns, `MAX_REL=0` (bit-exact) |

`P7T_VWIDTH_ORACLE_PARITY=PASS`, `MISMATCHES=0`; `VWIDTH` calls nothing, so it is
extracted whole and compiled unmodified, with the elevation grid supplied as a
1-based accessor and the vendor parameters (`MXVALZ`, `DZMIN = 10`, `QAHIT = 0.5`)
as explicit inputs.

### Semantics worth recording

1. `DZVAL` starts at `max(DZMIN, (zmax-zmin)/MXVALZ)` and is **re-resolved** (with
   the whole table cleared and the scan restarted, the vendor's backward `goto 1`)
   whenever a level above the first finds no width anywhere (`lwidth` false) and
   `DZVAL > DZMIN`.
2. Per cell and level the routine marches N, S, E and W to the first strip whose
   elevation reaches `ztarget = elev + k*DZVAL`, requiring `NINT(span*QAHIT)+1`
   hits in the strip; the south and west marches only run when the north and east
   sides found a wall.
3. The reported width is `max(lookNS, lookEW)` when exactly one side is valid and
   `min(lookNS, lookEW)` when both are valid or both invalid; `-1` means "no
   valley". The vendor's fatal "width of 0 or 1" check is reproduced as a refusal.

### Locked-case valley run (physical chain only)

`cteas_p7t_probe --deck-valley MET.DAT puff.inp 0 513.3846439571 3533.7689269678
70.8` runs `TRELIEF` and `VWIDTH` over the deck's real CALMET elevation field and
then `WALLTRAP` with the real widths:

```
P7T_DECK_VALLEY_RUN=PASS HOUR=0 NX=50 NY=50 DX_M=100 ZI_M=230.951 CELL_I=25
  CELL_J=25 DZVAL_M=10 DEFINED_WIDTHS=353 WIDTH_L1_CELLS=-1 WIDTH_L2_CELLS=-1
  WALLTRAP_TRAPPED=false WALLTRAP_SYE_M=200 TRELIEF_STANDIN=false
  VWIDTH_RECONSTRUCTED=true VALLEY_TABLE_ABSENT=false
  PHYSICAL_CHAIN_ONLY=true NOT_A_PUFF_CON_COMPARISON=true
```

**`VALLEY_TABLE_ABSENT=false`**: the valley table is now the vendor algorithm's
own output over the real terrain (353 defined widths over the 50x50 grid at
`DZVAL = 10 m`). At the stack's own cell no valley is resolved at the first two
levels (the local terrain is open), so `WALLTRAP` still reports no trapping there,
which is the correct behaviour for that cell. This is a physical-chain
demonstration, **not** a comparison with the frozen `puff.con`.

### CTest evidence (local worktree, macOS gfortran 16.2.0, Debug -Werror)

- `cteas_p7t_valley_width_contract`: the flat-terrain null widths and `DZMIN`
  fallback, a symmetric valley (wall cells null, the centre cell two or more
  cells wide) and every fail-closed path. PASS.
- `cteas_p7t_source_parity`: anchor + 20 quoted statements + the matrix. PASS
  (20 cases x 251 columns).
- `cteas_p7t_locked_case_valley`: the deck run above. PASS.
- Local `ctest` 43/44 PASS; the only failure remains the pre-existing macOS
  case-insensitive-filesystem failure of `cteas_p7_original_case_stage_contract`
  (PASS on Linux).

## 2026-10-12 P7U advection / step integration: located, pinned, instrumentation requested

Round status: the chain that advances a puff one step is located and pinned, and
the exact instrumentation request for a first real numerical comparison is
recorded below. **No advection code is ported this round**; the pinned spans are
the entry point for the next one.

### Located and pinned units

| unit | span | lines | calls |
|---|---|---|---|
| `ADVWND` (vertically-averaged wind over the puff's layer) | L2438-2538 | 101 | `zfind` |
| `ADVECT` (advective-wind dispatch, METFM 1-5) | L2540-2765 | 226 | `advwnd`, `powlaw`, `xtprf` |
| `PUFFDZ` (the puff's vertical extent ZBOT/ZTOP for the step) | L2882-3005 | 124 | - |
| `ZFIND` (met layer containing a height) | L18381-18419 | 39 | - |
| `POWLAW` (power-law profile, METFM 2/3 - off this deck) | L33463-33516 | 54 | - |
| `XTPRF` (profile-data lookup, METFM 4/5 - off this deck) | L33192-33461 | 270 | - |

plus the two inline pieces of `COMP`'s step integration
(`comp_step_start` L10465-10473 and `comp_step_wind` L10494-10519), pinned by
content and SHA-256 in `reference/p7u_source_anchor.json` (`--check` fails on
drift).

### The deck's advection path (METFM = 1)

`COMP`'s puff loop runs, per sampling substep: the start-of-step position
(`xold = xpb(ii)`, L10465) -> `GETCELL` -> the cell's met parameters (`IPGT`,
`HTMIX`, `XMONIN`, `Z0`) -> `PUFFDZ` (L10487) -> `ADVECT` (L10491) -> `ws =
sqrt(uadv**2+vadv**2)` (L10494) -> the rise-wind adjustment through `RISEWIND`
when the puff is Gaussian and has not reached its final rise (L10499-10512) -> the
calm treatment (L10516-10523). `ADVECT` with `METFM = 1` copies the cell's U/V
profile and calls `ADVWND`, which clamps ZBOT/ZTOP to the face range, resolves the
bracketing layers with `ZFIND` and returns the depth-weighted average.

### Instrumentation request (DGM-style) for a first real numerical comparison

The following probe would make one puff step numerically comparable against the
original on the locked case. All of it is **read-only instrumentation** of the
unchanged original (a debug `write` guarded by the existing `LDB`/`LDBHR` flags or
a new `P7DBG` logical), and it should run for `METFM=1` on the frozen 2022 inputs
for a single hour and a single puff:

| # | unit / span | variables to print | purpose |
|---|---|---|---|
| 1 | `COMP` L10465-10473 | `ii`, `xold`, `yold`, `zold`, `icode` | the start-of-step puff state (the comparison's initial condition) |
| 2 | `COMP` L10474-10486 | `ixs`, `iys`, `mdoms`, `istab`, `dpbl`, `el`, `z0m` | the met cell and parameters the step uses |
| 3 | `PUFFDZ` L2882-3005 (return) | `ztop`, `zbot` | the averaging layer bounds |
| 4 | `ADVECT` L2540-2765 (return) | `uadv`, `vadv` | the advective wind (our `advwnd` port must reproduce this) |
| 5 | `COMP` L10494-10523 | `ws`, `lcalm`, `uadv`, `vadv` after the rise-wind and calm adjustments | the effective transport speed |
| 6 | `COMP` L10155-10180 and the sampling loop | `nsam`, `nsstr`, `xsami`, `tsamp` | the substep cadence |
| 7 | the position update of the sampling loop | `xnew`, `ynew`, `znew`, `xpb(ii)`, `ypb(ii)`, `zpb(ii)` after the step | the end-of-step puff position |
| 8 | `SETPUF` L48198-48757 (entry/return) | `xtotb(ii)`, `tmtotb(ii)`, `syb1/sym1/sye1`, `szb1/szm1/sze1`, `sigyb(ii)`, `sigzb(ii)` | the sigma update (already ported in P7P/P7Q) |

Items 1-5 plus 8 are reachable with the ported modules alone except for `PUFFDZ`
and `ADVWND`/`ZFIND` (this round's pinned entry points); items 6-7 are the inline
substep/position code. The request is deliberately expressed as *observable
variables at named lines* so the instrumented run can be diffed against the C++
chain value by value.

### Incomparability list after this round

**Still one cause**: the advection/step integration is now the only unported
physics on the deck's path (its units are located, pinned and instrumented above),
plus the CTEAS-only `CONC.DAT` header. The terrain path (P7R/P7S/P7T) is complete
on real inputs, and the release scheduler (P7O), plume rise (P7N), step
bookkeeping and `/CSIGMA/` (P7P), the sigma update (P7Q) and CTSG (P7M, off this
deck) all carry original-source parity.

## 2026-10-12 P7V the advection units: ZFIND, ADVWND, ADVECT, PUFFDZ ported

Round status: the advection chain located by P7U is now ported and closed against
the unmodified vendor source. Four units, each extracted whole (span and SHA-256
pinned by `reference/p7v_source_anchor.py`, which fails the gate on drift) and
compiled with a hand-written driver (`reference/p7v_oracle_driver.f`):

- `ZFIND` (calpuff.for L18381-18419): the layer containing a height.
- `ADVWND` (L2438-2538): the depth-weighted average wind between ZBOT and ZTOP,
  including the vendor's clamp of both depths to ZFACE(1)/ZFACE(NZP1) and the
  single-layer copy.
- `ADVECT` (L2540-2765): the dispatch. METFM=1 (the locked deck's path) copies the
  cell's U/V profile and calls ADVWND. METFM 2/3 (POWLAW) and 4/5 (XTPRF) are
  **refused**: those routines are not reconstructed, so the port fails closed
  instead of approximating them.
- `PUFFDZ` (L2882-3005): the Gaussian branch (HTMET +/- SIGMAZ, slugs averaging
  SIGZB and SIGZE), the three lid caps (DPBL, then ZIOLD, then ZIMAX, applied only
  when that level is above HTMET and ICODE is not 3/13 and ISTAB <= 4), the
  uniformly-mixed branches ICODE 2/12 and 4/14, the two-layer ICODE 6/16 revision
  `ZBOT = ZIOLD*(1-2*QM/QU)`, and the vendor's "Bottom EXCEEDS Top" halt as a
  refusal.

Parity (unmodified vendor source, macOS gfortran 16.2.0):
- `P7V_ZFIND_ORACLE_PARITY=PASS CASES=14 MISMATCHES=0 MAX_REL=0.000e+00`
- `P7V_ADVWND_ORACLE_PARITY=PASS CASES=10 MISMATCHES=0 MAX_REL=2.898e-13`
- `P7V_ADVECT_ORACLE_PARITY=PASS CASES=8 MISMATCHES=0 MAX_REL=2.898e-13`
- `P7V_PUFFDZ_ORACLE_PARITY=PASS CASES=17 MISMATCHES=0 MAX_REL=7.250e-14`
- `P7V_ADVECTION_CONTRACT=PASS CHECKS=43 FAILURES=0` (hand-computed vendor
  semantics plus every refusal: METFM 2-5, an invalid ICODE, ISTAB outside 1-6,
  mismatched mass arrays, a revised ZBOT above ZTOP, a short profile, a NaN height).

Physical-chain run on the locked case (real CALMET cell winds and mixing height at
the source cell; SIGMA-Z is an explicit input because the sigma model is P7Q's
output; **this is not a puff.con comparison**):
`HOUR=0 NX=50 NY=50 NZ=9 DX_M=100 CELL_I=25 CELL_J=25 ZI_M=230.951 ISTAB=4
RELEASE_H_M=70.8 SIGMA_Z_M=89.152 ZTOP_M=159.952 ZBOT_M=0.000 UADV_MS=-0.651
VADV_MS=1.358 SPEED_MS=1.506` - PUFFDZ clamps ZBOT to the ground (70.8-89.152 < 0)
and caps ZTOP at 159.952 m (below the 230.951 m mixing height), and ADVECT averages
the real U/V profile over that span.

Still open on this path: the inline COMP step integration (the substep cadence
NSAM/TSAMP and the end-of-step position update - pinned by P7U at L10465-10473 and
L10494-10519, with the eight-row instrumentation request in the ledger) and
SETPUF's /CURRENT/ publication tail. GETCELL remains the last unported lookup; the
port takes the domain explicitly. Incomparability causes are unchanged: the inline
step integration, and the CTEAS-only CONC.DAT header.
### DGM 第三轮：原版 CALPUFF 步进/平流内部状态导出（2026-10-12）

详见 [DGM_P7_PUFF_STEP_DUMP_20261012.md](DGM_P7_PUFF_STEP_DUMP_20261012.md)。按 P7U 的 8 行插桩请求逐条实现：**只写**插桩（`subroutine comp` 内 8 个点 + 文件末尾 9 个子程序，vendor `calpuff.for` sha256 `da40372c…` 未变），同一编译器同一组 flag（含 `-ffixed-line-length-72`）编译两份二进制，用冻结输入各跑完 **143 小时**：**插桩前后 `puff.con` SHA256 同为 `0d51bdb6…`，且等于冻结参考**（未插桩那份不产生任何 dump，否则 fail-closed）。

产物 `dgm_puffstep.bin`（sha256 `cbbdaa29…`，89,649,824 字节 = **254,687 条 × 352 字节**：`int32[24]` 头 + `float32[64]`），逐条覆盖 P7U 的 8 项：起始位置/`icode`、网格单元与 `istab/dpbl/el/z0m`、`PUFFDZ` 返回的 `ztop/zbot`、`ADVECT` 返回的 `uadv/vadv`、抬升风与静风调整后的 `ws/uadv/vadv`、采样节奏（`nsam/nsstr/xsami/tsamp`）、`SETPUF` 入/出状态（`xtotb/tmtotb/sigyb/sigzb` 与 `/CURRENT/` 各量）、以及步末位置（`xnew/ynew`、`xpb/ypb/zpb`）。143 个小时标签、puff 1…11,985；每小时记录数、首末 puff 与字节偏移在 `dgm_puffstep.json`，可据此切出任意小时；入库切片为第 1 小时（1,275 条，sha256 `b51d20d3…`）。

自查：238,908 组相邻子步连接中位置/行程/`sigyb` **0 处不一致**（`sigzb` 只增不减——垂直散度因子）；`distm == ws × tsamp_effective` 最大相对差 5.8e-08；`zold` 恒在 `PUFFDZ` 的 `[zbot,ztop]` 内；`tsamp_effective` 18.56–3600 s（子步切分被实际触发）。坐标单位为**最外层气象网格格数**（1 格 = 100 m，源在 25.0 格 = 2.5 km，与烟囱位置一致），不是 km。本节只记录证据，不改变既有阶段结论。

## 2026-10-12 P7W RISEWIND ported; one-step numerical comparison against the vendor dump

Round status: `RISEWIND` is ported and closed against the unmodified vendor source,
and the **first real one-step numerical comparison against original CALPUFF numbers**
is in place, driven by DGM's instrumented puff-step dump.

### RISEWIND (calpuff.for L67162-67300)
Extracted whole (span/SHA-256 pinned by `reference/p7w_source_anchor.py`, gate-checked
on drift) and compiled unmodified with `reference/p7w_oracle_driver.f`. The port takes
its two dependencies as explicit injected callbacks - the gradual-rise height (P7N's
`gradual_plume_height`) and the advective wind (P7V's `advective_wind`) - so no common
state is hidden. Vendor semantics reproduced: the initial wind over the start-of-step
rise layer, the calm floor `ucalm=0.001`, the `NCOUNT` refinement loop, the step length
`WS*DT`, the rise/fall layer selection (`RTOP=REND+DZB` while rising, `RTOP=RBEG+DZB`
while falling, `RBOT` floored at zero), and the final-rise blend
`UADV=(1-FFINAL)*UGR+FFINAL*UFNL` with `FFINAL=1-XFINAL/XEND` once the step passes the
distance of final rise.

Parity: `P7W_RISEWIND_ORACLE_PARITY=PASS CASES=12 COLUMNS=3 MISMATCHES=0
MAX_REL=1.197e-06 STUBBED_DEPENDENCIES=GRISE,ADVECT` (the deterministic stubs isolate
RISEWIND's own iteration; GRISE and ADVECT are exercised separately), plus
`P7W_RISE_WIND_CONTRACT=PASS CHECKS=17 FAILURES=0`.

### One-step numerical comparison (DGM dump, hour 202200100, 1,275 substeps / 54 puffs)
`reference/dgm_p7_advection_2022/dgm_puffstep_hour202200100.bin` (sha256 `b51d20d3...`)
is read record by record; each record carries the vendor's own PUFFDZ/ADVECT inputs and
returns. The ported chain is driven per substep: PUFFDZ from the record's own
`htmet/icode/istab/dpbl` and the previous substep's stored sigma, ADVECT from the real
CALMET cell profile over the vendor's `ZBOT/ZTOP`, then RISEWIND (applied exactly where
COMP applies it: odd ICODE and `XTOTB < XFINAL`) with `XFINAL/ZFIN` from the
reconstructed P7N rise chain (`XFIN_M=163.913 ZFIN_M=136.158 ISTAB=4`), and finally
COMP's calm treatment (`wscalm=0.5`, `ucalm=0.001`):

- `P7W_DGM_STEP_ZT_VENDOR_VS_PORT_TOP=CASES=1221 MISMATCHES=0 UNCHECKED=54 MAX_ABS=0`
- `P7W_DGM_STEP_ZT_VENDOR_VS_PORT_BOTTOM=CASES=1221 MISMATCHES=0 UNCHECKED=54 MAX_ABS=0`
- `P7W_DGM_STEP_UADV_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=4.47035e-08 MAX_REL=3.13534e-07`
- `P7W_DGM_STEP_VADV_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=0 MAX_REL=0`
- `P7W_DGM_STEP_RISEWIND_APPLIED=107 SKIPPED=1168`
- `P7W_DGM_STEP_UADV_ADJUSTED_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=4.08292e-05 MAX_REL=7.04828e-05`
- `P7W_DGM_STEP_VADV_ADJUSTED_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=7.89165e-05 MAX_REL=5.82092e-05`
- `P7W_DGM_STEP_WS_ADJUSTED_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=5.65052e-05 MAX_REL=3.83265e-05`
- `P7W_DGM_STEP_LCALM_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=0`

The 54 `UNCHECKED` rows are each puff's first substep in the slice: PUFFDZ reads the
sigma stored by the previous substep, which lies outside the slice, so those rows are
reported as unchecked rather than guessed. `CAP_BRANCH_SKIPPED=0`: every record's DPBL
is above HTMET, so the vendor's DPBL cap determines ZTOP without ZIOLD/ZIMAX (which the
dump does not carry).

Comparability after this round: the puff-state **values** of the advection/step chain
are comparable against original CALPUFF on real substeps (this comparison), and the
remaining non-comparable item is the CTEAS-only `CONC.DAT` header subset. The inline
COMP step integration (the substep cadence NSAM/TSAMP and the end-of-step position
update, pinned at L10465-10473 / L10494-10519) is still not ported; the dump carries
its own end-of-step positions, so it is the next comparison target. GETCELL and
SETPUF's `/CURRENT/` publication tail remain open (spans pinned in the P7W anchor).


## 2026-10-12 P7X the inline COMP step integration; puff.con comparability statement

### The inline step integration
The three inline pieces P7U pinned are now ported and closed. They live inside
`subroutine comp`, so they cannot be extracted as units: their spans are pinned by
line number AND content hash in `reference/p7x_source_anchor.py` (gate-checked, so
the oracle can never silently drift):

- `cadence_old_puff` L10136-10147: `NSAM = NINT(WS*SMXI2+1)` with
  `SMXI2 = SECDT/(XSAMLEN*XGRIDM)`, clamped by `MXSAM`, `XSAMI = 1/NSAM`,
  `NSSTR = 1`, `TSAMP = SECDT*XSAMI`.
- `cadence_new_puff` L10158-10318: for the constant point source (ISTYPE=1)
  `NSAM = NINT(SECDT/TEMIT0)`, `NSSTR = IPNO`, `TSAMP = TEMIT0`; then
  `REFTSAMP = TSAMP`, `TLEFT = 0` and `LSUBSAM = NSAM < MXSAM`. The variable-emission,
  area, line and road paths (VARSAM/NEWAR1/NEWLN1/NEWVL1/NEWBC/NEWRD1) are **refused**.
- `substep_length` L10548-10582: `FSTEP = WS*TSAMP/(XSAMLEN*XGRIDM)` for a puff or a
  free slug while LSUBSAM; `TSAMP/FSTEP` for a full XSAMLEN substep (or when
  `KSAM < NSAM`), and `0.5*TSAMP` for the last substep when `1 < FSTEP < 2`; a slug
  attached to the source and a non-subsampled step are left alone.
- `position_update` L10607-10619: `DX/DY = U/V*TSAMP` in metres then in outermost
  met grid units, `DISTM = WS*TSAMP`, `XNEW/YNEW = XOLD/YOLD + DX/DY`.

### One-step numerical comparison, extended (same dump, hour 202200100, 1,275 substeps)
- `P7W_DGM_STEP_TSAMP_EFFECTIVE_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=0` (bit-exact)
- `P7W_DGM_STEP_DISTM_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=3.769e-03 m MAX_REL=3.835e-05`
- `P7W_DGM_STEP_XNEW_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=2.861e-05`
- `P7W_DGM_STEP_YNEW_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=5.341e-05`
- `P7W_DGM_STEP_NSAM_IDENTITY=CASES=1275 MISMATCHES=0` (`NSAM = NINT(SECDT/TSAMP)`)
- `P7W_DGM_STEP_TSAMP_EQ_REFTSAMP=CASES=1275 MISMATCHES=0`
- `P7W_DGM_STEP_TSAMP_NOT_ABOVE_REFERENCE=CASES=1275 MISMATCHES=0`
- `P7X_STEP_INTEGRATION_CONTRACT=PASS CHECKS=39 FAILURES=0`

Together with the P7W results (`PUFFDZ` bit-exact, `ADVECT` 0 mismatches, the
`RISEWIND` adjustment applied on exactly the 107 substeps where COMP applies it, the
adjusted transport wind and the calm flag all matching), the whole per-substep wind,
rise and position chain now reproduces the vendor's own instrumented numbers.

### puff.con comparability statement (final for this round)
- **Structure**: comparable. The record framing and the per-receptor grid are the
  P7E construction; the only structural difference from the vendor's file is the
  CTEAS-only `CONC.DAT` header subset.
- **Values, step chain**: comparable and verified. For hour `202200100` (1,275 real
  substeps, puffs 1..54) the fields `ztop`, `zbot`, `uadv/vadv` (raw and after
  RISEWIND), `ws`, `lcalm`, `tsamp_effective`, `distm`, `xnew`, `ynew`, `nsam`,
  `tsamp`, `reftsamp` all match the original run (0 mismatches; `ztop/zbot` and
  `tsamp_effective` bit-exact). The full 143-hour dump (254,687 records) carries the
  same fields, so any hour can be compared with the same probe once sliced.
- **Values, whole file**: NOT yet comparable, and the reason is assembly rather than
  a missing unit. The reconstruction still lacks (a) the vertical dispersion update
  and the `/CURRENT/` publication of SETPUF (so `zpb_out`/`ze1` and the `xb1..sze1`
  block are not compared), (b) `GETCELL` (the nested-domain cell resolution; the
  comparisons above take the vendor's own `ixs/iys/mdoms`), and (c) the end-to-end
  driver that runs the reconstructed step loop over the case. The remaining
  non-comparable item after those is the CTEAS-only `CONC.DAT` header subset.

Spans for the still-open pieces are pinned in the P7W anchor: `GETCELL`
L82482-82742, `SETPUF` L48198-48757.

## 2026-10-12 P7X (continued) GETCELL: the cell resolution closed against the dump

`GETCELL` (calpuff.for L82482-82742) is ported for the deck's path: one met domain
(`NGRID=1`) with `GRIDIJ` input coordinates, i.e. the vendor's truncate-then-add-one
cell index, the nudge of a location that leaves the outer domain just inside its
border (`DELTA1 = 0.5/NESTFACM X`), the "no valid cells" halt as a refusal, and the
final full-precision adjustment `IX0 = (X+DX)+1`, `ICELL = MIN(MAX(1,IX0), NXM)`.
The nested-domain and other coordinate-type paths are refused, not approximated.

Compared against the vendor's own resolution on the same dump:
- `P7W_DGM_STEP_GETCELL_I_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=0` (bit-exact)
- `P7W_DGM_STEP_GETCELL_J_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=0` (bit-exact)
- `P7X_STEP_INTEGRATION_CONTRACT=PASS CHECKS=49 FAILURES=0`

Comparability statement update: the step chain's values AND the cell resolution are
now comparable against original CALPUFF on the locked case. The remaining
non-comparable pieces are SETPUF's `/CURRENT/` publication (L48198-48757, so
`zpb_out`/`ze1` and the `xb1..sze1` block are not compared), the end-to-end driver
that runs the reconstructed step loop over the case, and the CTEAS-only `CONC.DAT`
header subset.

## 2026-10-12 P7G CONC.DAT structure comparison; SETPUF's /CURRENT/ coordinates closed

### SETPUF's /CURRENT/ coordinate publication (L48673-48723)
The coordinate part of SETPUF's tail is ported and compared against the vendor's own
`/CURRENT/` in/out blocks in the dump: `XB1/YB1 = XPB/YPB*DGRID`, `XB1..XE1` in
metres, `ZB1 = ZPB`, `ZE1` after gravitational settling (floored at the ground), and
the stored position update (`XPB=XNEW`, `YPB=YNEW`, `ZPB=ZE1`).

- `P7W_DGM_STEP_CURRENT_XB1_VENDOR_VS_PORT=CASES=1275 MISMATCHES=0 MAX_ABS=0` (and YB1,
  ZB1, XE1, YE1, ZE1 identically bit-exact)
- `P7X_STEP_INTEGRATION_CONTRACT=PASS CHECKS=59 FAILURES=0`

SETPUF's sigma and virtual-potential-temperature publication (SIGTY/SIGTZ, HEFTRAN,
CTADJ2, WALLTRAP, the quadrature and buoyancy-enhancement terms, the rise table) is
**not** ported, so `syb1/sym1/sye1`, `szb1/szm1/sze1` and `sigyb/sigzb` remain the
comparison gap on that path; the dump carries their in/out values as material.

### CONC.DAT structure comparison against the frozen puff.con
`cteas_p7e_probe --structure-compare FROZEN OUT NX NY` writes a file with this
module's own framing for every period the frozen artifact carries, then reports both
inventories. `P7G_CONC_STRUCTURE=PASS PERIODS=143 GRID=143 SPECIES_FIELDS=143
FIELD_BYTES=10015 NX=50 NY=50 FROZEN_RECORDS=3655 DATA_RECORDS=429
HEADER_RECORDS=3226 WRITTEN_RECORDS=431 FROZEN_BYTES=1896056 WRITTEN_BYTES=1444845`
(`tests/p7g_structure_tests.py`, gate-run, fail-closed on any change to the frozen
artifact's size, record count or period span).

So the structure is comparable and measured: the 143 period records, 143 grid
descriptors and 143 `H-3` species fields (10,015 bytes = 8+7+4*50*50) are reproduced
one for one, with the same first/last period (`2022001`..`2022006`). The difference is
the frozen file's 3,226 header records - the embedded control file plus the WROUT1
tables (model run info, source and receptor group tables, chemistry labels) - which
this reconstruction does not write yet.

### Whole-case driver: precise gap
The driver that runs the reconstructed step loop over the case and produces a
value-comparable CONC.DAT is **not** built. Every unit it needs on this deck's path
is now closed against the vendor (release P7O, rise P7N, step bookkeeping P7P, sigma
update P7Q, advection P7V, rise wind P7W, step integration/GETCELL//CURRENT/
coordinates P7X, sampling P7E, deposition P7F, terrain P7R/P7S/P7T, coupling P7H), so
the remaining prerequisite is the assembly plus three named pieces that the modules
themselves refuse today:

1. SETPUF's sigma/virtual-temperature bookkeeping (L48400-48670): SIGTY/SIGTZ, HEFTRAN,
   CTADJ2 and WALLTRAP calls, the begin/mid/end sigmas, the quadrature and
   buoyancy-enhancement terms, and the rise table.
2. The output stage's averaging machinery (AVET and the receptor-specific averaging),
   which the P7E module refuses explicitly.
3. The WROUT1 header records (the 3,226 records above).

Until those land, the honest statement is: **structure comparable and measured (data
records one for one, header tables missing); values comparable per substep for the
step chain (P7W/P7X, 0 mismatches on 1,275 real substeps) but not yet for the
concentration field.**

## 2026-10-12 P7G correction: the SETPUF sigma bookkeeping is already ported (P7Q)

Correction to the gap list recorded above, checked against the modules themselves
before starting any new port (this is the boundary the parent asked for):

- **SETPUF's sigma bookkeeping is NOT a gap.** P7Q's `sigma_update` module already
  transcribes `calpuff.for` L48505-48536 (begin/mid/end sigma and virtuals),
  L48570-48604 (the sigma-y final adjustments, the BZID/quadrature term and the
  stores) and L48635-48668 (the sigma-z final adjustments) - i.e. exactly the span
  that the P7G gap list named. `adjust_sigmas` carries the quadrature
  `SYSQ = BID + SY0SQ`, the monotonicity fix, the stored `SIGYB/SIGZB` and the calm
  minima.
- **CTADJ2 and WALLTRAP are NOT a gap either**: P7R/P7S/P7T delivered the terrain
  path (`CTADJ2`, `WALLTRAP`, the valley widths and the relief), so the `MCTADJ=2`
  strain and valley constraints are available rather than missing.
- **HEFTRAN is off this case**: P7D established `MHFTSZ=0`, so the Heffter branch is
  not on the deck's path.
- **PRIME wake**: `IDW0` is 0 on this deck, so `WAKE_TAB` is off the path.

So the remaining prerequisites for the whole-case driver are exactly two:
1. the `WROUT1` header records (the frozen artifact's 3,226 header records: the
   embedded control file, the model run info and the source/receptor group tables);
2. the output stage's averaging machinery (`AVET` and the receptor-specific
   averaging), which must first be classified as effective or not on this deck
   (`AVET`/`PGTIME` determine `AVEFAC`).

The next round's first action should therefore be a **verification** rather than a
port: drive P7Q's `sigma_update` with the dump's per-substep inputs (the previous
substep's stored sigmas, `zpb`, half the step time and distance) and compare
`syb1/sym1/sye1`, `szb1/szm1/sze1`, `sigyb_out` and `sigzb_out` against the dump -
the work in progress when the session paused, with the comparison hook
(`P7W_DGM_STEP_SIGMA_*`) designed but not yet compiled.
