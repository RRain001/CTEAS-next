# Issue #40 — S4-C controlled three-station original-CALMET numerical gate

Date: 2026-10-21. Based on scientific accepted merged [PR #209](https://github.com/RRain001/CTEAS-next/pull/209), `main@8957fc54`. Main purpose: independently test 3 surface and/or 3 upper real-format stations on the SAME selected G14 17-stage C++ P6 executor against independently rebuilt untouched original CALMET 6.5.0, without pretending that these are NOAA observations or unrestricted production.

## Experimental station matrix

Five controlled original-format source combinations: `3SS/3US`, `3SS/2US`, `2SS/3US`, `3SS/1US`, and `1SS/3US`, original 12×12×9 2024 cross-year source with 6 chronological model hours. G19 exporter writes an independent original-format SS3 station ID 583230, separate SURF record per hour, US3 station ID 58426 and unique UP3 soundings; original controls and station-specific positions are explicit, not aliases to other station arrays. Existing 1SS1US/C2 2SS2US inputs untouched. Extend previously independent original staging script to order SS1...SS3 and US1...US3 and each genuine UPn declaration; validate FORTRAN binary 176-byte control record and all 45 field labels per hour. The independently existing immutable P6E tolerance comparator remains sole numeric acceptance authority.

## Narrow physical modifications

- G20 selected source WIND1/INTER2 accepts 1–3 independent input stations per category only; G16 SIMD, genuine source PREPDI VERTAV and G23 station DIAGI/INTER2 physical kernels are reused without changing their formulas. Original IEXTRP=-4 upper-level k1 INTER2-missingness branch remains; original frozen 1/1 and 2/2 special branches retained.
- G18A MIXHT and G18C3 TEMP3D selected admission accepts 3/1 (or 1/3) with explicit experimental gates. G18C5/C6 P6F input/output expands selected 1/3 admission. No new physical result backfilling, no changing C1/C2 143h references, no expanded P6 production `run()` and no change to P7.
- G19 already has tested cardinality-generic source parsing; this PR only extends bounded exported source and selected physical admission. **This is NOT full arbitrary n/m support**; it is the first >2 scientific evidence on the tested nine-layer all-land source.

## Outcome categories (must be based on actual job logs)

1. If source parsing, native G14 or original Fortran fails: `BLOCKED` with actual compiler/original listing and source SHA; do not count it as numerical equivalence.
2. If candidate produces 45×hours output but independent Fortran / P6E comparison has not succeeded: `PRODUCED_UNVERIFIED`.
3. Only if both 1h and full 6h original vs C++ 45-field full-grid comparison have `total_exceedances=0` under existing P6E thresholds, all labels and data validated, and C1/C2/real-Huoshan regressions remain passing: `PASS_SCOPED_CONTROLLED_THREE_STATION`. These 3-station inputs are controlled synthetic original-format, not observed real-world data.

**Remain open:** station counts greater than three, general ID and coordinate changes, arbitrary native G26 production admission, 3+ genuinely measured stations from a real new site, P7, wet deposition, S5 scale, Docker.
