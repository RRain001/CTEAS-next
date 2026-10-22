# Issue #40 — S4-R1c8k full source-native first-hour CALMET.DAT 2.1

Date: 2026-10-22. Baseline merged PR #262 `main@f4b06ee3de8ad57862e7b1662386687eb3f3c97a`.

## Scope

The previous acceptance comprised two independent *field arrays*: real 43 values per cell (PR #261, 299,710 original/native REAL4 comparisons, zero tolerance exceedance) and integer 2 values per cell (PR #262, 13,940 exact integer equalities). It was **not** a complete legal CALMET.DAT file or a causal G14 hour. Stop accumulating detached physics probes: this PR consumes both existing G57 and G58 kernels without copying their equations and binds the result to the already frozen P6F `Calmet21File` serializer.

A new G59 one-hour source-first application takes only real 2022 NOAA P1-P5 `met.inp/GEO/SURF/UP`. It joins exactly 43 floating and 2 integer source-computed fields using canonical `hourly_labels` and `G18C6` source-derived original format statics (ZFACE, terrain, land use, LAI, roughness, station UTM coordinates, original SETCOM NEARS, controls, grid origin, projection, and first-hour UTC clock). The native program accepts **no** original Fortran `MET.DAT` as an input. It serializes through existing `cteas::p6f::write_calmet_dat21`, reads it back and validates the full first-hour dataset. Test-only opt-in is retained and unsupported options fail closed.

## Acceptance

The same authentic six-hour original CALMET run and original source provenance must remain frozen and independently verified. The new comparator independently reads the complete one-hour **native-produced** CALMET.DAT and compares its complete 45-field original OUTHR record order/type, 2SS+1US control block, 82x85x9 geometry, source hour and field values with the *pristine* six-hour original, using unchanged field-specific numeric tolerances. Separately it checks that each raw data field is byte-for-byte identical to independently run G57 and G58 numerical sources, eliminating accidental oracle copy or post-comparison field substitution. It consumes PASS source receipts for both field sets and refuses a new case with a changed original SHA.

The format/layout library was previously tested independently; the additional purpose here is to prove **native source-derived first-hour file assembly**. Passing is `PASS_SOURCE_SCOPED_REAL_NOAA_NATIVE_FIRSTHOUR_FULL45_MET21` with 45 records, 299,710 REAL4 comparisons, 13,940 INTEGER4 checks and zero frozen-threshold exceedances. Keep draft until the exact PR HEAD Actions and source gate pass.

## Boundaries

First hour only. Do **not** claim that G14 has committed the first hour state (ZI/ZICONV/DPTT), nor that six successive native hours, source-autonomous generalized production, C1/C2 same binary, G26 or P7 have passed. Do not mark Issue #40 done. Next priority is to convert this actual 45-field one-hour path into a **causal six-hour G14 actor with original/native 6 x 45 field comparison**, preserving the original-water and missing-wind source route; later prove dynamic new-site/old-case production admission. No new special-case physical formulas, no wet deposition, no Copilot review.
