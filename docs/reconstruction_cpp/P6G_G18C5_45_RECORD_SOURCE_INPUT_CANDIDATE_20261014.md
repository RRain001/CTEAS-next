# P6G G18C5 — source-owned 45 CALMET.DAT candidate records, no P6F reference backfill

Date: 2026-10-14. PR #63 is Draft, stacked on accepted frozen PR #53.

## Motivation

G18C4 assembled the eight G14 `NativeHourFields` arrays and last/current
mixing state, **not** an actual CALMET.DAT 2.1 45-field hour. The original
`OUTHR` when `IRTYPE=1`, `LCALGRD=T`, `NPSTA=0` writes exactly:

- 9 U layers, 9 V layers and 9 WFACE records. Fortran WFACE(k) maps
  the native ten-face W array at **face k+1**, not the zero ground face.
- 9 TEMP3D `T-LEV` records.
- Nine surface fields: two integer `IPGT` and `IRH` plus
  `USTAR, ZI, EL, WSTAR, TEMPK, RHO, QSW` floats.

That is **43 float32 records + 2 int32 records = 45 records/hour**. Internal
`QH`, `ZICONV` and `DPTT` do not exist as CALMET.DAT records. Never
reuse an original CALMET.DAT, 143-hour P6E fixture, or P6F `met_fields_from`
reference payload as a fallback to fill missing native physics.

## G18C5 selected 2SS/2US land implementation

`p6g_g18c5_selected_p6f_fields.hpp` produces a **test-only** source-stamped
`G18C5SelectedHourFields` with canonical original 8-character P6F record
names and original native little-endian float/int-compatible values:

- U/V/W/T planes, USTAR/ZI/EL/WSTAR: exact G18C4 producer arrays.
- `TEMPK`: G17C1 second post-FRADJ SURFVAR temperature;
  `RHO`: original SETCOM NEARS/AIRDEN;
  `QSW`: original SOLAR/HEATFX source radiation.
- `IPGT`: PR #53 immutable `cteas::p6e::pgtstb`, with native
  G17D level-one wind, G17C1 source solar and nearest SS,
  actual per-SS ceiling/cloud and all-land source mask. No Turner
  formula is rewritten.
- `IRH`: PR #53 immutable `cteas::p6e::surfvar_multistation`
  with **actual** site-ordered SURF.DAT humidity/temperature and original
  `IRAD/NUMTS/TRADKM` deck controls. Missing humidity follows the source
  interpolation fallback semantics; no copied oracle field is supplied.
- CALMET deck `ICLOUD=0` maps to *internal* `MCLOUD=1`, per
  unmodified vendor READCF, rather than falsely requiring an absent
  `MCLOUD` key in original met.inp. For the selected 2SS case,
  `ICLOUD=0/1` is allowed, gridded cloud options are rejected.
- Fail-closed scope: mismatched model hour/SS identity, missing
  weather arrays, XMISS sentinel, nonfinite field, water-only
  nonvalidated PGT branch, malformed cloud/RH/ceiling or unverified
  source configuration. The `explicitly_test_only` marker is
  mandatory. G14's `frame.next` never changes.

The G17B4/G18 source-selected CTest explicitly compares all 45 record
slots against their actual producers and tests original WFACE top-face
selection, frozen independent PGTSTB/SURFVAR RH kernel invocations,
unsupported gridded cloud and missing QSW refusal. No test here uses a
reference CALMET.DAT weather field for positive outputs.

## CI and scope limitations

GitHub-hosted Ubuntu [G18C5 code gate #38558438849](https://github.com/RRain001/CTEAS/actions/runs/38558438849),
commit `1e87ba964f62735bc854bb19ed198bccde720271`:
**Debug 20/20 PASS, Release 20/20 PASS, frozen 163-core-file guard PASS.**
Initial G18C5 compilation rejected an ambiguous boolean operator under
`-Werror=parentheses`; corrected without altering any physical formula.

**Do not label G18C5 as completed P6F or full scientific acceptance.**
This bridge assembles source-selected 45 candidate values and record names;
it does not construct the P6F `Calmet21File` run header and static records,
write sequential Fortran unformatted binary, or compare a fully generated
1h/6h/143h/year **multi-SS/US** CALMET.DAT to original Fortran.
G17C and G18A also retain source test-only control fixtures. G14 has not
become an end-to-end 17-stage **production** multi-station physical authority.

## Next required gate

- G18C6: feed the exact 45 selected record candidates into the **existing
  PR #53/P6F immutable** `p6f_calmet_dat21` writer contract using
  independently sourced original dynamic GEO, SS/US, ZFACE and
  actual model-clock header, no reference-derived static fields.
  Verify byte structure and independently read back with native P6F/P7.
- G18D: finish actual G14 PREPDI/DIAGNO/COMP callbacks with source physical
  coefficients rather than fixtures. Transactions for AA/BB, CGAMMA and
  previous ZICONV must only commit after native P6F success.
- Source scientific gate: original multi-station Fortran strict per-field
  comparisons of 1h, 6h, 143h and full-year/cross-year simulations on
  GitHub-hosted Ubuntu, before changing PR #63 from Draft.
