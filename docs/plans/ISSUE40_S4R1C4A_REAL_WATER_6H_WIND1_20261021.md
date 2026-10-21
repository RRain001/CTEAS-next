# Issue #40 S4-R1c4a: real NOAA 63 water × six UTC hours native WIND1

Baseline `main@484dc1124219bc5727bfc8bbba10a703c8dead60`, after merged S4-R1c1/#239 (genuine first-hour G42/G21) and S4-R1c2/#240 (original model-only MISSFC) and S4-R1c3/#241 (first-hour original vs C++ full 6970-cell G39 land thermal).

## Rationale and source-physics limit

Original multi-hour CALMET upper `CGAMMA` uses previous committed `ZICONV`, as do MIXHTST/COMP in later stages. The present G44 real WATER selected source only runs the *first hour*, so simply reusing G44 with freshly zeroed memory for hours 2..6 would produce a scientifically false multi-hour acceptance. **This PR MUST NOT do that.**

Original WIND1 (calmet.for L35829-36402), in contrast, is separately determined by hourly SURF winds and PREPDI upper sounding interpolation, source BIAS/ICALM, real station coordinates, missing valid masks and inverse-square spatial weighting. It does *not* read earlier ZICONV. This separate memoryless physical stage can be independently verified across all six actual hour labels without pretending an unavailable G14 full-hour commit.

The existing G42 first-hour entry remains unchanged and still rejects h != 0. A new private G42 source-only six-hour scoped overload is only callable from `G45`. G45 binds a single genuine P1–P5, real NOAA 2022-06-01 01→07 UTC file set, observes six distinct ordered original source intervals and source-validated UP brackets, computes original selected WIND1 with unchanged frozen G9, emits precisely 63 original WATER cells × six source UTC ending hours, and explicitly rejects producing any G21/G39/G24/G26/P7 state. Its deliberately empty previous-memory field is *not read by WIND1*, not a surrogate for continuous modeling.

The original reference comes from separate SHA-pinned unchanged original CALMET 6.5.0 (`calmet.for` Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`) scratch-only R1c1 DIAGNO first/second SURFVAR trace. The reference Fortran 6h×45-field MET.DAT must remain byte-identical to independently run pristine original; no vendor wind, oracle QSW, G21 TEMP2D or original MET is read into native G45. Original NOAA source `SURF.DAT` is never rewritten; no sparse auxiliary imputation is allowed at P5.

## Scientific gates

- Exact real 2SS (583140 Huoshan, 583210 Luogang) and 1US (58424 Anqing), grid 82×85×9, original-category 63 WATER, and six consecutive source UTC intervals.
- Exactly 378 paired source WATER cell-hour native vs independently instrumented original WIND1 U/V, spatial and hourly identity, original source real wind evolution between hour 1 and hour 6, first-hour one missing SS and zero calm as independent historical witness.
- For every hour: record original timestamp, two component maximum abs/relative deviations, original missing/calm SS counts, non-finite and above-tolerance cell counts; source hashes, binary hash, unchanged reference MET SHA in report.
- Freeze original R1c1 max absolute U/V threshold `0.05 m/s`; never relax if observed residual exceeds it. A failure must remain failed with grid/hour residual coordinates.
- Original G19/G20/G21/G26 default water refusal and G41 1h interfaces remain frozen; C1 1SS/1US, C2 2SS/2US, 143h and G44 first-hour real physical regressions run on exact PR HEAD before merge.
- Scientific label on completion only: `PASS_KERNEL_SCOPED_6H_WIND1`. This is **NOT** `PASS_KERNEL_SCOPED_6H_THERMAL`. Six-hour native G21/G39 temporal previous ZICONV and CGAMMA, G22/G23/G24 full wind tail, WATER USTAR/EL/ZI, true G26 6×45-field MET.DAT and P7 remain blocked until their independently accepted source histories and actual native fields exist.

## Next R1c4b

Establish a source-authentic and *native-computed* previous-hour `ZICONV/ZI` handoff within the frozen G14 state machine without any original-field injection or accidental commit. Only after that can the selected G21/G39 6h genuine 6970-cell land/water heat science be accepted. Avoid expanding this scoped WIND1 PR into an unproven production stage.
