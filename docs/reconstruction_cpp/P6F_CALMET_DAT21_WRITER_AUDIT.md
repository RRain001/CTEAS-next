## Independent OUTHD control provenance (2026-10-13)

[Actions #38376315827](https://github.com/RRain001/CTEAS/actions/runs/38376315827) is a separate independent-header source gate with **PASS**. It parses the frozen `CALMET.DAT` as a target (not a header template), reads only the upstream `met.inp` and `GEO.DAT` as expected-value inputs and validates 49 source-derived conditions across the 176-byte OUTHD run-control record: 143 hourly intervals, independent start/end clocks, UTC zone, grid geometry and spacing, selected station counts, land-use count/range, UTM 50N datum/date, origin and projection numeric terms. Mutated ABTZ, IEHR, NX and GEO UTM-zone inputs are each rejected. The tool is `scripts/p6f_independent_header_control_audit.py`; workflow `.github/workflows/p6f-independent-header-source.yml`; only the repository's GitHub-hosted Ubuntu runner was used. The reference file SHA-256 is pinned by the job before validation.

This is separate from [Actions #38375786650](https://github.com/RRain001/CTEAS/actions/runs/38375786650), which confirmed 12,514 independently GEO/deck-sourced static field values and byte-exact re-serialisation in the frozen-hourly **envelope**. The selected real-case independent native P6D/P6E 143h candidate was re-serialized with the same sourced statics in [Actions #38376244497](https://github.com/RRain001/CTEAS/actions/runs/38376244497), retaining all 45 numeric original comparison PASS.

**Important scope restriction:** the independent OUTHD audit checks the bytes' *content provenance*, not that all controls/comments/field masks are generated without any reference CALMET envelope in the current production writer. The 1,114 original comments/declaration and full per-hour autonomous writer invocation remain separate completion gates. A 45/45 real-case numeric pass and static source reconstruction do not establish a fully self-sufficient P6F implementation or generic CALMET acceptance. PR #53 must remain Draft.

---

# P6F CALMET.DAT 2.1 writer — byte-identity contract

Date: 2026-10-11. Unchanged reference is CALMET 6.5.0 L150223 (original vendor Git blob
`437f43bb7f0e51a1919e56664663e1a046986ed0`). New module: `native_cpp/modules/p6_calmet/p6f/`
(branch `codex/p6f-calmet-dat21-writer-20261011`). Roadmap row: P6F `CALMET.DAT` writer in
`P6_A_TO_G_SEQUENTIAL_EXECUTION_LEDGER.md`.

## Implemented

A standalone C++20 writer that turns **explicit field arrays** into a legal CALMET.DAT 2.1 file —
the record layout the unmodified CALPUFF reads.

1. **Library** `cteas::p6f` (`include/cteas/p6f/calmet_dat21_writer.hpp`, header-declared /
   compiled in `src/`). `Calmet21File` carries the declaration record, the comment section, the
   run control block (`IBYRN..IESECN`, `AXTZ`, `IRLG`, `IRTYPE`, `NX/NY/NZ`, `DGRID`, origins,
   `IWFCOD`, `NSSTA/NUSTA/NPSTA/NOWSTA`, `NLU`, `IWAT1/IWAT2`, `LCALGRD`) plus the OUTHD
   projection block (`PMAP/DATUM/DATEN/FEAST/FNORTH/UTMHEM/IUTMZN/RNLAT0/RELON0/XLAT1/XLAT2`),
   and the explicit arrays: `ZFACE`, `XSSTA/YSSTA`, `XUSTA/YUSTA`, `XPSTA/YPSTA`,
   `Z0`, `ILANDU`, `ELEV`, `XLAI`, `NEARS`, and per interval the per-level `U-LEV`/`V-LEV`/
   `WFACE` sequence, the `T-LEV` block and `IPGT/USTAR/ZI/EL/WSTAR/[RMM]/TEMPK/RHO/QSW/IRH/[IPCODE]`.
   `serialize_calmet_dat21` / `validate_calmet_dat21` / `parse_calmet_dat21` / `read_calmet_dat21` /
   `write_calmet_dat21` / `field_inventory` are the public surface.

2. **Layout facts** are taken from the unchanged original sources, not from a decoder:
   `OUTHD` L12448–L12537 (declaration, comment section, controls word order, static record order and
   widths, `ncom=ncommout+2`), `OUTHR` L13067–L13237 (hourly order: `U/V/[W]` inside the level loop,
   then `[T-LEV]`, then `IPGT USTAR ZI EL WSTAR [RMM] TEMPK RHO QSW IRH [IPCODE]`,
   `clabel(6:8)` I3 level digits), `WRTR1D` L36789–L36816, `WRTR2D` L36829–L36881,
   `WRTI2D` L36734–L36788 (24-byte record header: `char*8` label + begin/end `YYYYJJJHH` + seconds,
   then `NX*NY` words), `map.met` L5–L7 (`character*8 datum,pmap`, `character*12 daten`,
   `character*4 utmhem`).

3. **Explicit semantics**, all enforced fail-closed:
   - *time*: packed `YYYYJJJHH` + explicit seconds; every interval exactly 3600 s; the original writes
     the end clock as the same packed hour with seconds advanced by 3600; intervals are contiguous;
     `AXTZ` is an 8-character zone label; the declared run window (`IBYRN..IESECN`, written as
     year/month/day/hour plus seconds *inside* that hour — the frozen case is on the hour, so its
     seconds words are zero) must equal the first interval begin and the last interval end as
     instants.
   - *units*: every field carries its SI unit and its OUTHR/OUTHD mask condition
     (`hourly_field_specs`, `static_field_specs`); `check` prints them next to the denominators.
   - *masks*: the field set is exactly a function of `IRTYPE`/`LCALGRD`/`NPSTA`. `RMM`/`IPCODE` with
     `NPSTA=0` are rejected (`cannot appear when NPSTA=0`), internal CALMET state with no file
     representation (`ZICONV`, `DPTT`, `QH`, `USTAROLD`) is rejected by name, a missing field of a
     declared interval is rejected, and `NEARS` supplied with `NSSTA<1` is rejected instead of being
     dropped.
   - *extents/kind*: grid, station, static and per-field value counts must match the declared
     dimensions; `IPGT`/`IRH` must be stored as int32 and every other field as real32; real values
     must be finite; `ZFACE` must be strictly increasing with `NZ+1` faces; `IWAT1<=IWAT2`.
   - *missing*: the original sentinel `XMISS=9999.` (real) / `9999` (integer) is a legal value and is
     preserved bit-exactly; `field_inventory` counts it and excludes it from the number of defined
     cells.

4. **CLI** `cteas_p6f_calmet_dat21_writer`: `roundtrip --file [--out] [--expect-sha256] [--report]`
   (parse → serialise → byte compare, with the first differing record reported),
   `check --file [--report]` (layout validation + per-field inventory with units, masks and the
   `ILANDU` statistics), `emit-fixture --out … [--irtype 0|1] [--with-missing]` (deterministic,
   explicitly labelled synthetic layout fixture that exercises the writer from explicit arrays) and
   `write-from-p6d …` (the P6D wind-array entry point, section **P6D input adapter** below).

   Supported modes: `IRTYPE=0` (winds only) and `IRTYPE=1` (winds plus the 2-D meteorological
   fields), both with `IWFCOD=1`, `LCALGRD` taken from the header, and `NPSTA>=0`. `NPSTA=-1`
   (MM5 precipitation) is refused with an explicit message: it selects a precipitation input whose
   `RMM`/`IPCODE` mask semantics this writer does not implement, so a caller must supply observed
   precipitation stations or none at all. `IRTYPE=0` is derived from `OUTHR` L13160–L13180 (the
   routine returns right after the U/V/[W] loop) and is covered by synthetic round trips and an
   independent structural walk; no frozen original `IRTYPE=0` file exists in this repository, so the
   byte-identity proof above does not transfer to it.

## Byte-identity evidence against the frozen real case

Frozen truth: `project/cases/hefei5km_2022_reference_case_20261011/run/met/met.dat`,
64,762,556 B, sha256 `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`,
7,562 Fortran records, 1,114 comment records, 143 intervals × 45 fields = 6,435 field records,
`NX=NY=50, NZ=9`, `IRTYPE=1`, `IWFCOD=1`, `LCALGRD=T`, `NSSTA=1`, `NUSTA=1`, `NPSTA=0`.

Parsing that file into the explicit arrays and serialising it back produces a **byte-identical**
image (`cmp` clean, output sha256 equal to the frozen digest). The same file is then read back by
three independent consumers:

- the writer's own fail-closed parser (self-consistency only);
- an **independent Python record walk** in `tests/verify_real_reference_roundtrip.py`
  (framing, 96-byte declaration, 1,114×132-byte comments, 176-byte controls, the ten static records
  with zero clock words, the OUTHR order, the packed time labels, contiguity, and an aligned XMISS
  count per label) whose inventory must equal the writer's `check` report field by field;
- the **P7 decoder** `native_cpp/modules/p7_calpuff/reference/original_decode_calmet_hourly.py`
  (read-only), which must report `PASS_ORIGINAL_CALMET_EXPLICIT_TIME_AND_FIELD_LAYOUT` on the
  re-serialised file and produce a report **identical** to the one it produces for the frozen
  original, including its own sha256 of the file it read;
- the **E22 contract reader** `cteas::p6e::read_calmet_dat21` (P6E module, read-only include), which
  must parse the re-serialised real case and agree on all 6,435 field records cell by cell
  (bitwise float comparison), and vice versa (the P6F parser must read what the E22 writer produces).

Observation about the frozen artifact: the hourly field values of `met.dat` contain **no** `XMISS`
sentinel (0/15,372,500 real and 0/715,000 integer values of 16,087,500 stored cells), so the
sentinel path of the inventory is exercised only by the synthetic fixtures. This says nothing about
precipitation: the P6C record of the same case already documents `IPCODE=9999` 143/143 in `SURF.DAT`
and `NPSTA=0`.

## Gate

```
python3 scripts/local_gate.py --track p6f     # LOCAL_GATE_P6F=PASS
```

Delivered as PR [#26](https://github.com/RRain001/CTEAS/pull/26) (base `main`); the script writes
its own machine-readable evidence under `$CTEAS_GATE_ROOT/evidence/p6f-<sha12>.json`.

The gate configures, builds (`g++-12`, `-Wall -Wextra -Wpedantic -Werror`) and runs the module's
CTest targets, plus one dedicated step for the original-CALPUFF read test:

| CTest | What it proves |
|---|---|
| `p6f_calmet_dat21_writer_unit` | explicit arrays → records → read back, per-field bit equality, both output modes, the calendar/time helpers over 1600–2400, XMISS preservation, and the ~55-case fail-closed matrix |
| `p6f_calmet_dat21_synthetic_cli_roundtrip` | CLI end to end on four synthetic variants (including `NSSTA=0` and `NPSTA=3`) plus an `IRTYPE=0` and a sub-hourly (`00:30`) start, with an independent Python walk of every emitted record and the CLI-level fail-closed options |
| `p6f_calmet_dat21_real_reference_round_trip` | the frozen byte identity + SHA-256 pin + independent inventory agreement (including the `ILANDU` statistics) + P7 decoder cross-read + six fail-closed negatives |
| `p6f_calmet_dat21_e22_contract_cross_read` | E22 reader on the re-serialised frozen case (6,435 records) and P6F reading an E22-written file |
| `p6f_calmet_dat21_p6d_array_input` | the P6D contract end to end (202,500 values mapped and verified) plus eight fail-closed cases |
| `p6f_calmet_dat21_real_scale_xmiss` | 50x50x9 x 143 intervals densified with XMISS (167,310 sentinel values), independent per-label counts, byte-exact round trip, P7 decoder acceptance, NaN rejected |
| `p6f_calmet_dat21_original_calpuff_reads_written_calmet` | rebuilds the unmodified original and runs cases A-D of the table above (excluded from the plain `ctest` invocation and run as its own step, so a missing Fortran toolchain is reported BLOCKED instead of silently skipped, with `--no-tests=error` preventing a silent skip) |

The real-case tests are registered fail-closed: `CMakeLists.txt` raises a configure error if the
frozen reference file or the P7 decoder is absent, so the byte-identity proof can never be silently
skipped, and the gate's own step declares the Fortran toolchain, the vendor sources and the tracked
reference outputs in `requires`.

## P6D input adapter (the P6D -> P6F -> P6E pipeline entry)

The P6D producer `cteas_p6_realcase_wind_field` (module `native_cpp/modules/p6_calmet`) writes, per
hour, one raw little-endian float32 plane per field plus `metadata.json`, `produced_hours.txt`,
`temp2d_*`, `qh_*` and four `terset_*` planes. One documented command turns that product into a legal
CALMET.DAT 2.1:

```
cteas_p6f_calmet_dat21_writer write-from-p6d \
    --fields <p6d-dir> --variant wind1 --w-field w_face \
    --statics-from <legal CALMET.DAT 2.1> \
  [ --irtype 1 --met-fields-from <legal CALMET.DAT 2.1> ] \
    --out <CALMET.DAT> [--report <json>]
```

- **Read, never guess**: `metadata.json` supplies `grid.nx/ny/nz`, `grid.grid_spacing_m`,
  `grid.layout` (must be the documented `i_fastest` index `i + nx*(j + ny*k)`), `grid.dtype`
  (`float32`) and `grid.byte_order` (`little`), `levels.zface_m` (must equal the `ZFACE` of
  `--statics-from`), `missing_sentinel` (scalar), `hour_label` (`END` or `START`, so the interval
  begin is `label - 3600 s` or the label itself) and the hourly label list/count. Any other spelling
  is rejected with the value it found.
- **Accepted variants**: `wind1_*`, `inter2_*`, `blend_*`, `slope_corrected_*`. The producer renamed
  the pre-tail INTER2 field from `blend_*` to `inter2_*` and reused `blend_*` for the closed DIAGNO
  field (`INTER2 -> SMOOTH -> DIVCEL`), which is the variant P6D recommends for a full wind product;
  `inter2_*` stays available as the diagnostic stage whose verdict is anchored by the unchanged
  original comparator. Each name carries its own verdict in `metadata.json` (`blend.verification`,
  `inter2.verification`), and the adapter records whichever it finds verbatim. `windbc_*` is refused
  with an explicit message: those planes are stitched lateral boundaries (`NZ*2*NY` / `NZ*2*NX`,
  level-major), not a gridded field.
- **What the verdict does and does not do**: the adapter refuses a variant only when the producer
  marks it with the `NOT_SOURCE_VERIFIED` prefix (a "do not use" marker, observed on the earlier
  `rw11` blend). Any other verdict string - including a partial one such as
  `PARTIAL_LEVELS_8_9_PASS_LEVELS_1_7_NEUTRAL_SIMILT_GAP` or a degraded
  `MIXING_HEIGHT_NOT_SUPPLIED_ALL_LEVELS_NEUTRAL_SIMILT` - is written and recorded verbatim in the
  CLI report (`blend_verification`, `variant_source_verified`, `product_partial`, `product_status`);
  the writer never upgrades a producer's caveat into a pass of its own.
- **W faces**: `w_face_*.f32` holds `NZ+1` faces per column (face 1 is the ground face); CALMET.DAT
  writes W at the *top* face of each layer, so face `k+1` becomes `WFACE(k)` and the ground face is
  not written.
- **No invented values**: the declaration, the static records, the station tables and the projection
  block are case input and come from `--statics-from`; the declared run window and `IRLG` are derived
  from the intervals actually written. The P6D contract contains only U/V/W, so `IRTYPE=0` is the
  default product; `IRTYPE=1` requires `--met-fields-from`, which takes `T-LEV/IPGT/USTAR/ZI/EL/
  WSTAR/TEMPK/RHO/QSW/IRH` verbatim from another legal file (P6E's product, or the case's own records
  when composing for integration).
- **Verification status is honoured**: the adapter keys on the verdict P6D publishes in
  `metadata.json` (`blend.verification`) instead of on a hard-coded list. A variant whose verdict
  starts with `NOT_SOURCE_VERIFIED` is refused unless `--accept-unverified-variant` is passed, and
  the report always records `blend_verification`, `fradj_status`, `variant_source_verified` and
  `w_face_source_verified`. This was exercised on real metadata, not only in tests: the directory
  used for the earlier case C run (`/home/lhy/build/p6d/rw11`, read 2026-10-12) carries
  `blend.verification = "NOT_SOURCE_VERIFIED: the 143-hour comparison against the unchanged original
  INTER2 FAILED (worst 10.36 m/s) …"`, and `write-from-p6d --variant blend` on it was **refused**
  (fail-closed observed on real metadata). The regenerated directory `rw12` carries
  `PASS_REALCASE_BLEND_ORIGINAL_INTER2` (143 hours, 6,435,000 components, worst 4.22e-05 m/s at a
  2e-4 m/s tolerance, zero mismatches) and the same command accepts `--variant blend` with no code
  change - which is what the case C row records. The refusal path and the explicit
  `--accept-unverified-variant` opt-in are covered by the adapter test.
- **What the composition is not**: `w_face_*` is SLOPE-compensated but not FRADJ-compensated
  (`FRADJ: PENDING_GAMMA` in the P6D metadata) until `GAMMA`/`CGAMMA` lands, so it is QA/plumbing
  data; and composing a reconstruction with the *original* 2-D fields is an integration step, not a
  claim that those fields were reconstructed.

Evidence: `tests/verify_p6d_array_input.py` builds a directory of exactly this shape and requires
every U/V/W value of the produced file to equal the corresponding plane value (202,500 values for
three hours at 50x50x9), the byte-exact round trip, the `IRTYPE=1` composition path, and eight
fail-closed cases (missing plane, wrong plane size, unsupported `grid.layout`, unsupported
`hour_label`, non-finite value, non-contiguous hours, `IRTYPE=1` without a met source, grid
mismatch). Run against the **real** P6D product (`/home/lhy/build/p6d/rw8`, 143 hourly labels, 1,291
files) the same command writes a 64,762,556-byte, 143 x 45 file, and the unmodified original CALPUFF
reads it end to end (case C below).

## Original CALPUFF reads what we write

The roadmap clause for this stage is "C++ 完整合法输出 v2.1，原版 P7 读取". Our own decoders are not
enough, so `tests/verify_original_calpuff_reads_written_calmet.py` rebuilds the **unmodified original
CALPUFF 7.2.1** from the tracked vendor sources with the repository's own reference flags
(`scripts/capture_hefei_2022_reference_case.py`, `PUFF_FFLAGS`) and runs it in a temporary directory
(nothing is ever written inside `project/`):

| Case | File the original read | Result |
|---|---|---|
| A | the writer's re-serialisation of the frozen `met.dat` (byte-identical, pinned SHA-256) | 143 hours; `puff.con` **byte-identical** to the tracked original reference output and `puff.lst` identical beyond its two wall-clock lines; the listing echoes our header (`metfm=1`, `irlg=143`, `nsecdt=3600`, `abtz=UTC+0000`, `ibdathr=202200100`, `iedathr=202200623`, `zface = 0.00000000 … 3000.000`) and ends at `Year: 2022 Month: 1 Day: 6 Julian day: 6 Hour: 23 Second: 0` |
| B | the same file with **changed values** from `cteas_p6f_calmet_dat21_perturb` (wind x1.25, ZI x1.5, TEMPK +5 K; structure, masks, units and time labels untouched) | 143 hours, no fatal marker, identical time-window echo, and different finite non-negative concentrations (mean 0.032848 → 0.029406, max 5.1697 → 4.6693, non-zero cells 42,685 → 42,670) - legal *and* read, not merely hash-equal |
| C | `write-from-p6d --variant blend` on the **real P6D** product `/home/lhy/build/p6d/rw17` (the recommended closed-DIAGNO blend, 1,865 files, 143 labels, tree sha256 `7d34bcc9525f19dd1d207a48a40b5aff87501b2ac26315d11db7152e9cc23cfd`, `metadata.json` sha256 `a36acd862174f2837c28eb1be482447e942eb996ec6984d2213ae10e882d6b6a`, `blend.verification = PARTIAL_LEVELS_8_9_PASS_LEVELS_1_7_NEUTRAL_SIMILT_GAP: …`, `inter2.verification = PASS_REALCASE_BLEND_ORIGINAL_INTER2`, `w_face_*` FRADJ-pending) plus the case's 2-D fields | 143 hours, no fatal marker, finite non-negative concentrations (mean 0.030236, max 5.2611, 31,701 non-zero cells) on a 64,762,556-byte composed file |
| D | a structurally broken file (the frozen file truncated by 10 bytes) | **rejected**: the original aborts (`Error termination. Backtrace:`, return code 2) instead of producing a clean successful run |

The build is pinned in the report: GNU Fortran 11.4.0, the SHA-256 values of the unchanged
`modules.for`/`calpuff.for` and the produced binary (the run documented here built
`f248b09a76a1792c…`; a rebuild in another directory yields a different binary hash because the build
path is embedded, while the pinned sources and flags are the same). One case takes about 20 s. The
test also fails if the original changes a byte of the weather file it read (it opens `METDAT`
read-write).

Two findings worth keeping: the PE `calpuff_v7.2.1.exe` from the distribution directory cannot
execute on the Linux build host (no Wine is installed), and a pre-built binary from outside the
repository that looks like the original did **not** reproduce the tracked reference output (it halted
in `GETCELL` at hour 25 and printed differently formatted listings). This test therefore builds the
original from the repository's own tracked sources - the only reproducible authority - and proves the
build by reproducing the tracked reference `puff.con` byte for byte.

## Hard limits and open dependencies

- **The original-CALPUFF evidence is layout/readability evidence.** Case A additionally shows that
  the original computes exactly what it computed from the frozen file (byte-identical concentration
  output), and cases B/C show that changed values are read and used - none of that makes the
  reconstructed fields scientifically correct, which stays a P6G obligation.
- **This is a serialiser, not a physics result.** Byte identity proves the record layout, time
  semantics, units and masks. It does **not** show that reconstructed 2022 fields equal the original
  CALMET values; the writer stores whatever value words the caller supplies, including wrong ones.
  The P6F acceptance clause "物理值正确" therefore remains **open** and belongs to P6G, which must
  compare the P6D/P6E chains' fields with the frozen original under the pre-registered tolerances.
  Status of this work: writer implemented, layout + byte identity PASS, **field values NOT accepted**.
- `IRTYPE=0` is supported and tested synthetically but has no frozen original reference in this
  repository; `NPSTA=-1` (MM5 precipitation) stays refused (see above).
- The projection block is only byte-preserved and typographically validated; only the frozen case's
  UTM/WGS-84 block (`UTM`, `WGS-84`, `02-21-2003`, `N   `, `IUTMZN=50`) has been exercised end to end.
- `ILANDU` is written verbatim and never range-rejected: the frozen case stores category 20 on all
  2,500 cells while `NLU=14`, so `check` reports `ilandu_max`, `ilandu_over_nlu_cells` and
  `ilandu_negative_cells` instead of failing (the independent cross-check in the byte-identity test
  reproduces `ilandu_max=20` and `ilandu_over_nlu_cells=2500`). Land-use validity remains a
  caller/upstream concern.
- The P6D U/V products are written as delivered and carry their own original-source verdicts in the
  metadata this adapter reads (`wind1_*`: original `WIND1`+`SIMILT`; `blend_*`: as published by P6D,
  which was still `NOT_SOURCE_VERIFIED` in the directory used here). `slope_corrected_*` and
  `w_face_*` are SLOPE-compensated but not FRADJ-compensated (`FRADJ: PENDING_GAMMA`): they are
  QA/plumbing values and are labelled as such in the report.
- The E22 header is consumed only as an independent decoder through an explicit include path, and the
  P6D contract is consumed through its published `metadata.json`/plane files: the P6F library and CLI
  include no P6E/P6D/P7 C++ header. If E22 or the P6D contract changes, the corresponding cross-read
  test must be re-run.
- The writer does not close P6F as a stage milestone: it closes the writer/layout half of it.


## 2026-10-13: independently sourced P6F static records and numeric control fields

The earlier `write-from-p6d --statics-from` CLI is a **source-dependent integration adapter** and must not be represented as native P6F static-source completion. Following P6D 27/27 and P6E 18/18 strict 143h scientific PASS, a new separate fail-closed source-provenance boundary was built:

- `native_cpp/modules/p6_calmet/p6f/src/p6f_geo_static_provenance_main.cpp` uses the previously vetted independent `cteas::calmet::p6::read_geo_50` reader on **GEO.DAT v2.1** and the original model's **met.inp** numeric deck. It never derives an expected static value from the CALMET.DAT candidate. The candidate is only parsed to compare observations and to retain non-independent envelope portions as declared below.
- Independently rebuilt: 2,500 cells each of land use `ILANDU`, terrain `ELEV`, roughness `Z0`, and leaf-area index `XLAI`; 10 `ZFACE` levels; the four surface/upper-air station X/Y coordinates; 2,500 one-station `NEARS` values. **12,514** comparisons, 0 disagreements with the unchanged original static values. The source-derived numerical run header includes begin/end dates, hourly interval count, grid dimensions/origin/spacing, time zone, station counts, run type, projection key and UTM zone, `NLU/IWAT1/IWAT2`, and `LCALGRD`.
- Exact source-coordinate fidelity: the CALMET OUTHD station static arrays are **grid-origin-relative metres**, whereas SS1/US1 in the deck use absolute UTM kilometres. Original REAL*4 operation order is `float32(station_km)*1000f - float32(origin_km)*1000f`, **not** `(station_km-origin_km)*1000f`. The false latter conversion produced 6 mm of error for upper-air station X, rejected by the audit.
- Optional `--emit-source-statics OUTPUT` rewrites static values and the numerical controls from GEO.DAT/met.inp into the legal `CALMET.DAT` 2.1 file envelope. The original frozen 143h reference remains byte-identical (SHA-256 `b1823cda92280888d70b00961ab39486036a3086e18637fff21efb4f4b237d30`) after replacing those records with independent inputs, and intentionally mutated ZFACE is rejected. [Actions #38376041857](https://github.com/RRain001/CTEAS/actions/runs/38376041857) PASS.
- **Real native 143h integration**: the same independent upstream static regeneration was applied to the actual C++ P6D→P6E G3/G4 PASS output archived from [Actions #38372382572](https://github.com/RRain001/CTEAS/actions/runs/38372382572). Rewritten native candidate is byte-identical to the native candidate before static replacement, and the source-locked original 45-field numeric comparator reports `total_exceedances=0`. [Actions #38376244497](https://github.com/RRain001/CTEAS/actions/runs/38376244497), PASS. This does **not** inject original winds into the native candidate.

**Outstanding P6F work (not accepted):** the complete `OUTHD` comment block, declaration text, and projection auxiliary date field are still held from the candidate envelope. Unsupported multi-station and precipitation-station static paths are not regenerated here; `NSSTA=1, NUSTA=1, NPSTA=0` is the admitted source-emission scope. Full independent native 143h file assembly should use explicit `Calmet21Header + Calmet21Statics + P6D/P6E hourly arrays` without parsing the reference as its starting envelope. Do not label `P6F_COMPLETE` or `P6_COMPLETE` based only on this selected-case source-static gate.


## 2026-10-13: P6F independently generated OUTHD + native 143h hourly fields

This milestone **supersedes the earlier pending independently rebuilt header comment block** for the *locked 50×50×9 Hefei 2022 case only*.

- New C++ P6F tool mode: `cteas_p6f_geo_static_provenance --geo SOURCE_GEO.DAT --deck SOURCE_MET.INP --candidate NATIVE_P6D_P6E_CALMET.DAT --emit-native-header OUTPUT.DAT`. It creates a **new** `Calmet21File`, derives the complete `OUTHD` declaration, 1,090 132-column comments, date/zone/run control, UTM projection date from GEO.DAT, and all admitted static arrays from the GEO/deck source. Only the **hourly fields** are transferred from the native P6D/P6E file. Earlier `--emit-source-statics` remains byte-identity reference-envelope validation, not this new mode.
- Original Fortran `TFERCF` copies each control-deck line as a comment, but the frozen binary has 1,114 comment records whereas the tracked updated `met.inp` supplies a different native comment count (1,090 including the two native provenance comments). Header **byte identity is neither claimed nor desired**. Original CALMET file layout is preserved, not a copied reference text block.
- In [GitHub Actions #38378460648](https://github.com/RRain001/CTEAS/actions/runs/38378460648), selected native 143h file with newly generated header passed C++ binary validation, P7 independent 143h record decoder, and frozen original source numeric comparator **45/45 fields, zero exceedances** with unchanged per-field tolerances. The independent header must differ in bytes from the source candidate, and its first comment must identify CTEAS.
- In [GitHub Actions #38378766675](https://github.com/RRain001/CTEAS/actions/runs/38378766675), **unmodified vendor CALPUFF 7.2.1** was compiled with the original source build recipe and read the CTEAS source-generated header file for all 143 hours. Original CALPUFF generated finite, nonnegative, nonzero concentrations; no original numerical equivalence of P7 is inferred.
- **Original CALPUFF paired-run scientific concentration parity:** [GitHub Actions #38379522205](https://github.com/RRain001/CTEAS/actions/runs/38379522205) PASS. With the *same 143-hour native meteorological 45-field payload*, the borrowed native header (3 comment records) and independently reconstructed P6F OUTHD header (1,090 comment records) produce **identical bitwise float32 143-hour 50×50 concentration grid payloads** in the unmodified original CALPUFF 7.2.1. Input controls, all 12,514 static values and all 6,446 non-comment binary met records are already bit-identical. However the complete original CALPUFF `puff.con` binaries **are not byte-identical**: first changed record index 1, 439 changed records. Those 439 records were not decoded as scientific-vs-metadata fields; no whole-file-byte-equivalence claim is made. This stronger result supersedes the earlier [Actions #38379020835](https://github.com/RRain001/CTEAS/actions/runs/38379020835) failure that conflated the full binary image with the 143 concentration grids.

**Remaining explicitly open:** the *P6E per-hour producer* still reads an original/reference `CALMET.DAT` envelope for some setup/statics; this downstream P6F **writer independence does not prove upstream P6E input-reference elimination**. No generic multi-surface-station, precipitation-station, non-UTM, variable dimensions, or end-to-end original-source-free meteorological production is claimed. The C++ CALMET time authority remains process-backed, not an in-process `step_diagno/step_comp` kernel. Do not yet mark the overall P6 milestone PASS.


## Original CALPUFF 7.2.1 consumes independent native OUTHD (2026-10-13)

**PASS**, frozen Hefei selected 143h run, [GitHub Actions #38379522205](https://github.com/RRain001/CTEAS/actions/runs/38379522205).

The new [`verify_original_calpuff_native_independent_header.py`](../native_cpp/modules/p6_calmet/p6f/tests/verify_original_calpuff_native_independent_header.py) builds unmodified original CALPUFF 7.2.1 from pinned `modules.for`/`calpuff.for`, and performs a control-variable test using the **same C++ P6D/P6E 143h weather payload** twice:
1. a native CALMET.DAT merged by the C++ clock whose existing header contains 3 documentation lines;
2. a source-generated independent P6F OUTHD with 1,090 comments derived from `met.inp` and `GEO.DAT`, with all numeric control fields and 12,514 static values explicitly rebuilt by the native source generator.

The test checks that **all 6,446 non-comment Fortran records**—including the entire 143h weather field inventory—are byte identical between (1) and (2), independent of comment count and record offsets. Both original CALPUFF runs completed all 143 hours. The 143h concentration-grid `float32` payload SHA-256 is identical between the two outputs. The full `puff.con` file hashes are **not** identical (439 Fortran record byte sequences differ, first differing record index 1); their header-versus-auxiliary-content breakdown is not established by this test. The extracted hourly concentration **float32** payloads are identical. Do not claim full-file equivalence or classify the changed records without separate decoding.

The earlier [Actions #38378460648](https://github.com/RRain001/CTEAS/actions/runs/38378460648) established independent numerical OUTHD and static provenance + original 45-field scientific comparison + P7 structural decoding. This final control-variable CALPUFF test closes the **unmodified P7 read/143h concentration preservation gate**.

Scope and remaining hold:
- This validates the selected Hefei 2022 one-surface/one-upper-station 50×50×9 case. `--emit-native-header` currently uses an already-assembled native P6D/P6E CALMET.DAT as the *hourly field carrier* (not as the source for header and statics). A fully stand-alone P6F writer should receive the per-hour native P6D/P6E field arrays directly, construct `Calmet21File` without parsing a previously assembled CALMET.DAT, and validate source provenance/hashes at the interface.
- CALPUFF concentration-grid byte equivalence for this one case is not CALPUFF source-physics numerical equivalence for every deposition, output mode, or input branch. Do not claim P6 generic G5 or complete all-case P6F acceptance.
- No CALMET scientific tolerances, P6D/P6E physics, reference data or Fortran sources were modified by the OUTHD acceptance test.


## Native coordinator direct P6F handoff and upstream P6E isolation

This is an additional transition milestone, not a declaration of generic source-independent CALMET:

- The process-authoritative `cteas_p6_native_hourly_driver` now accepts optional `--p6f-writer EXECUTABLE`, only for the full 143h selected-case run. After successfully writing the original-path native hourly `native_causal_calmet.dat`, it invokes the independent `cteas_p6f_geo_static_provenance --emit-native-header` executable with **GEO.DAT + met.inp + only the C++ P6D/P6E assembled hourly file**. The second artifact `native_causal_independent_header_calmet.dat` is separate, not substituted into the frozen Python-vs-C++ byte-regression candidate. Its SHA-256 and `independent_p6f_source_header_written` state are recorded in the native coordinator manifest. The 143h scientific G3/G4 gate is enforced separately under the existing immutable 45-field tolerances.
- P6F CMake's frozen-case root is now a configurable `P6F_REPO_ROOT` CACHE PATH, with its original default unchanged; the GitHub-hosted Ubuntu 143h coordinator workflow supplies the separately pinned `original_locked_case` checkout. This avoids silently skipping source-required P6F tests when the case is isolated from the active branch checkout.
- **Independent reference-hourly-value isolation:** [Actions #38380482544](https://github.com/RRain001/CTEAS/actions/runs/38380482544) PASS. The P6E native-hour COMP implementation was run twice for the same actual initial hour, with the same real C++ P6D wind, P4/P5 observation bridge and P6D station ELUSTR2 flux. The frozen reference CALMET.DAT's hourly U/V/T-LEV/USTAR/EL/WSTAR/ZI **values only** were mutated under unchanged static controls and time labels. The two candidate CALMET output files and all three exported `ZI/ZICONV/DPTT` state files were byte-identical. This proves those original *hourly values* are not inputs to the selected first-hour native P6E physical path; it does **not** prove independent header/static inputs or a full 143h zero-reference run.
- **Direct native coordinator→P6F integration PASS:** [GitHub Actions #38380707789](https://github.com/RRain001/CTEAS/actions/runs/38380707789) completed the actual C++ 143h weather simulation and produced the source-independent header artifact `native_causal_independent_header_calmet.dat` directly from the coordinator's optional `--p6f-writer` handoff. The unchanged source-locked 45-field numeric comparator on that artifact returned `total_exceedances=0`. The separate G3/G4 CI job and AVETMP exploratory job remain distinct source-verification gates; their status is not inferred from this production Job.

**Still open:** native P6D/P6E's setup uses a pinned original CALMET.DAT envelope for metadata/time/grid/statics, and the P6D source-input adapter also consumes case metadata. A complete original-free P6 must replace those interfaces with a typed `CaseGeometry + MetControl + HourClock + Stations` supplied by GEO.DAT/met.inp/P4/P5; it is not achieved by writing a new OUTHD after the computation. The 143h frozen-case G3/G4 numerical PASS remains frozen, and the complete P6 milestone and generalized input modes stay gated.


## 2026-10-13: automatic P6F handoff from unified C++ hourly coordinator

The previous accepted `--emit-native-header` tool was externally invoked after the native hourly loop. The production-like `cteas_p6_native_hourly_driver` now accepts `--p6f-writer PATH` (only for a full 143-hour interval) and calls the source-only `GEO.DAT + met.inp` P6F writer as a downstream process after 143 native P6D/P6E COMP commits. It emits `native_causal_independent_header_calmet.dat`, a separate SHA-256 and an explicit provenance bit in `native_cpp_hourly_manifest.json`; the original source-accepted `native_causal_calmet.dat` remains immutable for comparator and C++↔Python byte gates.

**Observed PASS:** [Actions #38380716284](https://github.com/RRain001/CTEAS/actions/runs/38380716284) ran the direct 143h P6D→P6E→P6F chain, emitted the independent header from the native C++ coordinator, and returned **0 exceedances in the original 45-field scientific comparison**. The prior Python-vs-C++ baseline remains byte-identical in [Actions #38380716220](https://github.com/RRain001/CTEAS/actions/runs/38380716220).

**Upstream distinction:** direct P6F header emission does NOT itself make the original `met.dat` dispensable. `native_hourly_driver_main.cpp` still pins and passes the original file to the legacy-style P6E `emit-realcase --reference` and to P6D selected-case readers. The C++ hourly controller has an opt-in `--p6e-source-builder` flag for a *separate, scientifically gated* experiment which supplies metadata built from `GEO.DAT + met.inp` instead of original CALMET.DAT. The `cteas_p6f_p6e_source_metadata` tool produces 143h x 45 fully missing sentinel arrays plus real source grid/station/time controls; its independent source file construction and missing-value self-check passed in [Actions #38381622077](https://github.com/RRain001/CTEAS/actions/runs/38381622077). Until the native P6D→P6E 6h and 143h hour-payload byte comparison passes with that option, its science status must stay EXPERIMENTAL, and this does NOT claim P6D no longer reads the original reference.

**Status:** P6F independent writer handoff: PASS selected case. P6E metadata reference replacement: isolated acceptance pending. Full P6, other grid geometries, rain / precipitation paths, and process-internal CALMET scheduler: NOT YET ACCEPTED.


## 2026-10-13: full selected-case reference-free P6D/P6E→P6F product

**Independent selected-case end-to-end closure, PASS.** Source is the physically unchanged case's `GEO.DAT`, `met.inp`, `SURF.DAT`, `UP.DAT` and station metadata; the model case root explicitly omits **run/met/met.dat**, whose original output fields are used only by independent validation afterward. The native C++ hourly coordinator now accepts `--p6e-source-builder` to generate a valid 143-hour metadata-only 45-field file. Its full hourly meteorology is all XMISS; it cannot supply any original weather values. Native P6D/E then overwrites the computed fields, and `--p6f-writer` composes source-independent OUTHD, numeric run controls, projection, static grid and station records into the final CALMET 2.1 product.

[Actions #38383617259](https://github.com/RRain001/CTEAS/actions/runs/38383617259): in a model input root **without** original `met.dat`, six-hour and 143-hour native C++ process runs passed, all 270 / 6,435 hourly Fortran records were byte-identical to the previously accepted source-reference run, and the fully independent **final P6F header/output file itself** was byte-identical to the previous native independent OUTHD product from [#38380716284](https://github.com/RRain001/CTEAS/actions/runs/38380716284). That prior independent product had been read by unmodified original CALPUFF for 143h in [#38380707826](https://github.com/RRain001/CTEAS/actions/runs/38380707826), where full-file `puff.con` metadata differed but floating concentration payload was bit-for-bit identical. The post-reference-free file has identical complete bytes, so it is the same downstream input. The unchanged CALMET source comparator independently measured **45/45 fields PASS, 0 exceedances**, with no floating tolerance relaxation.

The official 143h C++ science workflow was promoted to `--p6e-source-builder` in commit `70b3fa60e98b852d6788218f04f5266ddda15477`, retaining the existing six-hour/old-path and C++↔Python controls. The promoted official 143h G3/G4 science run [Actions #38384160324](https://github.com/RRain001/CTEAS/actions/runs/38384160324) has now **PASSED**: native P6D/P6E 143-hour computation, GEO/deck-only P6E metadata, integrated source-only P6F OUTHD output, and the independent original 45-field numerical comparator with **0 exceedances**. The source-absent separate case proof remains [#38383617259](https://github.com/RRain001/CTEAS/actions/runs/38383617259).

**Boundaries of acceptance:** frozen Hefei 2022 50×50×9 143-hour selected-case CALMET source reconstruction with original CALMET.DAT physically unnecessary in the P6 computation path. This does not validate arbitrary CALMET grids, multiple surface/upper/precip stations, new stability-control branches, rain or wet deposition (deferred), cross-platform bit identity, or a fully in-process P6D/P6E physical scheduler. The strict source original CALPUFF runtime compatibility is an output-contract acceptance, **not** a claim of P7 numerical reconstruction equivalence. PR #53 remains Draft; do not merge as generic P6 complete.


## 2026-10-13: selected-case direct per-hour native P6F writer (no intermediate assembled CALMET.DAT)

**Official selected-case production handoff upgraded and accepted:** `cteas_p6_native_hourly_driver --p6e-source-builder ... --p6f-writer ... --p6f-direct-hourly`. The optional native P6F result `native_causal_independent_header_calmet.dat` is now assembled from the source-only `GEO.DAT + met.inp` metadata envelope (143×45 hourly XMISS fields) **plus 143 individual original-free P6D/P6E one-hour files** from `native_hourly_files.txt`. The P6F direct writer does not parse or load the previously merged `native_causal_calmet.dat` as the hourly carrier. The latter remains written solely as a historical G3/G4 and Python-vs-C++ numerical baseline.

Implementation: `p6f_geo_static_provenance_main.cpp` supports `--geo GEO.DAT --deck met.inp --source-metadata SOURCE_ONLY.DAT --hour-manifest 143_HOUR_PATHS.txt --emit-native-header OUTPUT.DAT`. The new loader requires exact 143 hourly inputs, the correct 45 labels and clocks at every hour, matching 50×50×9 geometry, no non-finite/missing native weather and no live meteorological values in the source-only metadata. The only special handling is `read_calmet_dat21_native_one_hour`: P6E's *transport* file carries a one-hour field group while its header can retain a longer deck clock. This P6F reader normalizes the transport header start/end from its actual one-hour field clocks **in memory only**, then applies the unchanged strict CALMET 2.1 validator. The existing generic `read_calmet_dat21` public API and strict validations remain unchanged; no original source file or scientific tolerance was altered.

Verification: [GitHub Actions #38387228250](https://github.com/RRain001/CTEAS/actions/runs/38387228250) ran the direct path under the official native 143h coordinator. Its P6D/P6E 143h production job and the direct-P6F fault-injection job both passed: the final source-only P6F output was **byte-identical** to the previously accepted assembled-envelope P6F output, and two negative tests correctly rejected (1) duplicate hour 0 substituted as hour 1 and (2) a metadata envelope containing live weather rather than all XMISS. A separately invoked direct writer also matched the official coordinator output byte-for-byte. This is binary parity, not just relaxed numeric tolerance.

The original wind and original CALMET.DAT remain absent from the native calculation inputs when the `--p6e-source-builder` mode is selected. A reference CALMET.DAT remains separately accessible only to the CI verification comparator, as an independent scientific oracle.

**Scope remains case-specific:** 143h Hefei 2022 50×50×9, one surface and one upper-air station, no precipitation stations. The model remains process-per-hour, not in-process callback-integrated P6D/P6E. Wet deposition, generic multi-station configurations, arbitrary domains and independent all-case G5 remain outside this acceptance; PR #53 stays Draft.


## Official native 143h physical-missing original CALMET and direct-product CALPUFF closure

The **official** `P6 native causal DIAGNO COMP hourly integration` workflow is now stronger than a provenance-flag check. At [Actions #38388872510](https://github.com/RRain001/CTEAS/actions/runs/38388872510), after C++ P6D/P6E and P6F were compiled, CI **moved** the frozen original `run/met/met.dat` outside its input path and asserted the source path was absent throughout the full 143-hour `cteas_p6_native_hourly_driver --p6e-source-builder --p6f-direct-hourly` execution. The original file was restored only after native production finished, for independent source validation; its frozen SHA-256 was rechecked after restoration.

**Results (GitHub-hosted Ubuntu 22.04):** native 143h P6D→P6E→P6F production PASS without original CALMET.DAT present; direct native hourly-manifest P6F build and old-envelope byte-parity PASS; metadata-with-live-weather and duplicate-hour negative injections PASS; independent CALMET original G3/G4 45-field numeric science comparison PASS, `total_exceedances=0`. The other source control stages remain in the same workflow.

For actual downstream acceptance, [Actions #38389061130](https://github.com/RRain001/CTEAS/actions/runs/38389061130) downloaded the exact already-accepted **direct per-hour P6F output** artifact from [#38388062863](https://github.com/RRain001/CTEAS/actions/runs/38388062863), checked that it was byte-identical to an independently regenerated source GEO/deck header plus native weather, and fed the unchanged direct artifact to **unmodified original CALPUFF 7.2.1**. Original CALPUFF completed its 143h read/run, and the original concentration payload-equivalence check passed with native legacy-envelope weather as control. This is not merely a custom C++ decoder test.

**Scientific scope:** this evidence closes the selected Hefei 2022 50×50×9, 143h, one surface and one upper-air station, no precipitation station, **process-level** C++ P6D/P6E/P6F chain. It does *not* validate arbitrary CALMET configurations, generic WIND1 synthetic or G5, all P6F multistation/comment variants, wet deposition, or in-process `step_diagno/step_comp`. Do not merge PR #53 into main as generic P6 acceptance on the basis of this single case.
