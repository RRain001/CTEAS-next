# G18C6 — selected native 45-field P6F CALMET.DAT 2.1 binary handoff (2026-10-14)

## Source authority and implementation

PR #63 is a Draft stacked on the frozen accepted 163-source-file PR #53.
G18C5 constructed all 45 selected P6F hourly native field arrays. G18C6
continues the exact **selected/test-only** G17D/G17C/G18C fixture pipeline
into the existing **unchanged** P6F `p6f/src/calmet_dat21_writer.cpp`
software contract. It **does not** reimplement Fortran binary serialization
and does not infer source meteorological field values from an existing
reference MET.DAT file.

New `p6g_g18c6_selected_p6f_dataset.hpp` assembles:
- `Calmet21Header`: `IRTYPE=1`, `LCALGRD=T`, `IWFCOD=1`,
  `IFORMO=1`, `NPSTA=0` strictly checked against source met.inp;
  dynamic 12×12 test GEO is **10 km** WGS-84 UTM zone 50 north, with
  independently calculated REAL*4 grid origins and spacing. The declared
  hour is from **actual** source `SurfaceHour.start/end` UTC, not from
  calendar constants copied out of reference MET.DAT. Fortran field clocks
  use the original packed begin-hour and end-seconds=3600 convention.
- `Calmet21Statics`: source `OriginalWindControls.zface_m` checked
  against the same met.inp's `ZFACE`; dynamic `GeoGrid` original
  `Z0/ILANDU/ELEV/XLAI`, one-based `SETCOM NEARS` **recomputed exactly from current source geometry (also rejecting fabricated but in-range ordinals)**, the original
  *ordered* local-metre SS/US positions, and the source CRS. No original
  CALMET.DAT static array is copied as a shortcut.
- All **45** `Calmet21Field` rows in exactly frozen P6F's own
  `hourly_labels(9,1,true,0)` ordering: 9×U/V/W top face/T plus
  9 surface fields (43 float32 + 2 int32). Missing labels, incorrect
  field widths, unsupported water/precip/cloud branches, mutated ZFACE,
  site reorder or wrong original UTM zone fail closed.
- Immutable P6F's `validate_calmet_dat21`, `serialize_calmet_dat21`,
  `write_calmet_dat21` and `read_calmet_dat21` are called directly
  from the G18C6 selected test. **All byte-level emitted fields** must
  read back unchanged; no synthetic replacement field values are
  inserted into the original 45 record payload.

An independent Python `reference/verify_g18c6_independent_binary.py`
reads the on-disk product with its **own little-endian Fortran sequential
record walker** (not using P6F's decoder or an external reference DAT).
It checks 96-byte declaration, 176-byte controls, 132-byte provenance
comments, original dynamic GEO/source SS/US statics, UTC 2024-Jan-01
02:00–03:00 window, 45 exact 8-character OUTHR labels and hour clocks,
original 2×INT32 and 43×REAL*4 kind/dimension assumptions, and positive
bounds for Turner IPGT and interpolation IRH. Original vendor CALPUFF
read validation and full multi-hour source-fortran parity are separate
scientific gates.

CMake selected source CTest now explicitly compiles the accepted P6F writer
translation unit **without modifying it**, and tests the actual
`g18c6_selected_2ss_2us_1h_calmet.dat` output. The independent
file-walker CTest **depends** on the writer test so that a missing/failed
producer cannot be misclassified as an independent PASS. Both are in the
GitHub-hosted Ubuntu Debug/Release `^p6g_` suite.

## G18C6 selected code gate

[GitHub-hosted Ubuntu #38560073138](https://github.com/RRain001/CTEAS/actions/runs/38560073138) at SHA `f0353ff742dabe3ccca83ade286615cfc7319024`: **Debug 21/21 PASS, Release 21/21 PASS**, including the independent binary record walker and frozen PR #53 163-file guard. The later exact source SETCOM NEARS hardening has a separate SHA and must be validated independently.

## Scientific acceptance boundaries

The 2SS/2US fixture deliberately borrows *control values* from the pinned
one-site met.inp while its station geometry and hourly observations are
deliberately constructed as synthetic test inputs. All records are generated
natively by the existing selected G17/G18 physics and reference-independent
GEO inputs but **they are not source-fortran verified full-hour fields**.
Therefore this is an output format and field-provenance integration test,
**not** completion of native CALMET G14 production physics, the real
P6F all-hour output pipeline, or multi-station 45-field scientific parity.

The remaining gates, without changing frozen #53:
1. independently source-correct G17C/G18A controls (replace fixture
   coefficients and station thermal handoffs);
2. integrate G18C5/6 into a **single** existing G14 scheduler with
   all 17 stages correctly completed and atomic output/cross-hour commit;
3. compare *genuine* original Fortran 2SS/2US original-run 45 fields
   against the C++ 1h, 6h, 143h and year/cross-year outputs;
4. validate actual on-disk CALMET.DAT via existing P6F/P7 and original
   CALPUFF reader, not merely a self-parser. Keep PR #63 Draft until these
   gates are met.

CI results are valid only for their exact code SHA; use hosted Ubuntu
runs to distinguish selected output contract PASS from full physical
multi-site PASS.
