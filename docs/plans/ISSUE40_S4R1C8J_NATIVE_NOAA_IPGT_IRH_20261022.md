# Issue #40 — S4-R1c8j genuine NOAA native P6F IPGT/IRH integer pair

Date: 2026-10-22. Baseline merged #261 `main@4302e7400b0f6d697ffd9b588671f6d0b7b9dfe2`.

## Purpose

Merged #261 independently validated all **43 REAL4 physical outputs** of original CALMET OUTHR first hour (43×6,970=299,710 values, zero frozen-tolerance exceedance), from genuine 2022 NOAA 2SS (one station truly missing wind) + 1US, 6,907 LAND/63 WATER, 82×85×9. The only remaining hourly output **value types** are two INTEGER4 records: `IPGT` (stability) and `IRH` (relative humidity). This PR computes them using existing P6E kernels without original Fortran computed physical fields.

## Source-physical computing

- Input only source-owned real NOAA P1–P5 model deck, unchanged G41 surface/upper station identity, and the same G43 authentic model-local nonwind MISSFC that retains the original missing wind.
- Existing accepted G57 first-hour actual G24 final `U-LEV 1`/`V-LEV 1` drive P6E original-backed `pgtstb`, with original source-comp G54 `NEARS` and `SINALP`, original grid categories, `MCLOUD=1` as mapped from `ICLOUD=0/1` and real station opaque-cloud and ceiling observations.
- `PGTSTB` explicitly skips all water cells; original genuine selected `NOWSTA=0` neutral `WATER` has assigned **PGT D=4**. G58 overlays precisely this original-defined value for 63 source-verified WATER cells. Water is never reclassified LAND and no missing wind is converted to CALM.
- P6E `surfvar_multistation` reuses original observed station-relative-humidity interpolation with original `IRAD/NUMTS/TRAD`, authentic station positions and model-local nonwind MISSFC for 6,907 LAND cells. On 63 WATER cells original SURFVAR `LDWAT=1` and `NOWSTA=0` selects zero eligible overwater stations and explicitly sets `IRH=100` (vendor L12926–13005); preserve that source-selected branch without reclassifying WATER as LAND.
- Any source branch change, GEO mismatch, missing cloud/ceiling controls, forged station wind or unsupported control tuple rejects. Existing G18C5 all-LAND and G26B production gates remain untouched.

## Independent science gate

Source first-hour C++ emits 2×6,970 INTEGER4 values (IPGT/IRH) in strict order, with no legal CALMET.DAT file or full 45-field claim. Independent Python comparator requires exact source-scoped PR #261 43-REAL acceptance receipt, parses original pristine CALMET 6-hour binary with six 45-field records at exact 2SS/1US 82×85×9 shape and original clock, then performs **13,940 exact integer equalities**, with coordinate/type-specific rejection. Original MET.DAT may only be read **after** native physical calculations, never as native forcing.

The original code and previous C1/C2 regressions are unchanged. Neither an integer mismatch nor a stale science receipt can be hidden by reclassifying water or changing tolerance: INTEGER4 equality is **exact** (zero difference). The next full 45-field gate will require a genuine native one-hour writer/header/static provenance and independent complete physical 45-field file comparison, not merely summing separately scoped tests.

## Still blocked

Even on PASS, this does **not** establish a legal P6F CALMET.DAT file, source-autonomous static/header envelope, causal G14 6-hour ZI/ZICONV/DPTT, full P6 production or P7 #36. Production result flags must remain false. No Copilot review.
