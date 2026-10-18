# Issue #54 D2/D3 — genuine original TERREL vs C++ numeric failure localization

## Status: two genuine numerical FAILs, not a source-data failure

For both routes, manually dispatched [90m](https://github.com/RRain001/CTEAS-next/actions/runs/39128482366)
and [30m](https://github.com/RRain001/CTEAS-next/actions/runs/39128484104)
scientific Actions built original TERREL 7.0.0 from **pinned**
RRain001/CTEAS@`dfad99a7`, rebuilt the genuine original source TIFFs
and native P1 in the same runner, repackaged only the TIFF compression
to Compression=1, and independently confirmed identical original
Int16 elevations/NoData/geotransform. Original and native then read
**exactly the same** uncompressed TIFF. The original DAT/SAV and
native CSV were independently compared by #67/#71 without altered
tolerances. Both routes **NUMERIC_FAIL**.

| Route | original/native total hits | cells with hit difference | raw mean bad cells | max raw mean absolute error |
| --- | --- | --- | --- | --- |
| A user 90m 2 TIFF | 3429 / 3429 | 18 / 2500 | 15 | 2.166667 m |
| B official SRTMGL1 30m | 30893 / 30892 | 493 / 2500 | 487 | 0.588885 m |

The identical **90m total** with a nonzero number of per-grid-cell
hit differences is evidence that some original/raw samples may be
assigned to different cells even without changing the total valid
input point count. The **30m total differs by one** and many
individual grid counts disagree. A plausible mechanism is near-cell
boundary differences in float32 coordinate conversion and/or original
COORDLIB vs GDAL/PROJ, particularly at higher native source
resolution; this is a **hypothesis**, not proven root cause.
Do not change the original physical sampling method, source data,
alter scientific tolerances, or mark the routes PASS on this basis.

## D2/D3 independent numerical investigation

This PR adds no physical or source modifications. The manual
same-source original-vs-native driver now uploads only **summary**
diagnostics: per-model-row and per-model-column mismatch counts,
positive/negative hit residual totals, next-cell opposite-sign
candidate counts and first 20/30 mismatched cells. The first 20
scalar differences are small bounded excerpts from the existing
#67 independent comparator; the complete DEM, original source
coordinate stream, control deck and vendor code remain private to
the ephemeral runner. Aggregate hit diagnostics do **not** change
the acceptance result.

After reviewing the two separately obtained real reports, determine
whether mismatches concentrate near western/eastern vs northern/
southern boundaries, identify representative source pixel locations,
and compare the original TERREL GLOBE/COORDLIB REAL*4 projected km
against the C++ GDAL/PROJ transform and CELLIND REAL*4 rules.
Only then propose a scientifically justified fix, with strict
frozen Hefei and genuine 90m/30m replays.

Acceptance thresholds remain: original cell hit counts **exact**,
unrounded original Fortran REAL*4 mean `1e-5` m, formatted DAT
F8.1 `0.0500001` m. Both routes must pass separately before D4
can establish scientific equivalence.

Project separation: #54 governs P1 numerical equivalence;
#46 remains downstream dynamic P3 and does not implement an
alternative P1 kernel.
