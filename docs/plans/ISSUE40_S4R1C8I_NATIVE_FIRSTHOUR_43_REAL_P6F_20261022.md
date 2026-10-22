# Issue #40 S4-R1c8i — real NOAA first-hour P6F 43 REAL4 field integration

Date: 2026-10-22. Baseline merged #260 main `c6fdc4471d7332a849bce4830bbebb0f20052070`.

## Scientific goal

The authentic NOAA site now has independent physical parity of native full first-hour G24 (9-layer U/V/10-face W), G54 post-AVEMIX mixed LAND/WATER ZI, G55 WSTAR and G56 full 9-layer TEMP3D. However, the prior numeric tests were **separate stages**. This PR ties them into the *actual original CALMET OUTHR field inventory*, independently checks 43 REAL4 physical records over 6,970 cells and identifies precisely which **two INTEGER4** P6F records remain.

The selected original mode `IRTYPE=1, LCALGRD=T, IWFCOD=1, NPSTA=0, NZ=9` has `9×(U-LEV,V-LEV,WFACE)+9×T-LEV+IPGT+USTAR+ZI+EL+WSTAR+TEMPK+RHO+QSW+IRH =45` fields. Of these, 43 are REAL4 and 2 (`IPGT`, `IRH`) are INTEGER4.

## Native G57 test-only physical ownership

- Actual NOAA P1–P5 source files and source G41 mixed 6,907 LAND / 63 WATER, **2 original SS with one truly missing wind, 1 true US**.
- Physical G48/G24 final U/V/W, exact original WFACE upper face `k+1`; G56 actual COMP TEMP3D 9 layers.
- G54 genuine **post-AVEMIX** ZI, COMP-third SURFVAR/TEMPK, HEATFX QSW/AIRDEN RHO and ELUSTR land USTAR/EL.
- G53 original-selected neutral WATER overwrites WATER USTAR/EL values without classifying WATER as LAND.
- G55 true after-AVEMIX WSTAR, not stale previous intermediate.
- 43 ordered, individually labeled REAL4 `NX×NY` fields are emitted as a **forensic diagnostic**, *not* legal CALMET.DAT, no original header, no static envelope and no physical intermediate data from Fortran.

All quantities are computed in existing shared kernels; G54 change only exposes existing calculated values. Existing G18C5 all-LAND guard and G26B production fail-closed gate remain untouched.

## Independent oracle and numerical acceptance

Use the **unchanged source original** authentic NOAA 6h `MET.DAT` generated independently in the existing source workflow, together with the separate independently certified #260 original 6h×45 write-only byte-identical TEMP3D reference. The external Python parser validates original CALMET 2.1 Fortran sequential record markers, source controls `NX=82,NY=85,NZ=9,IRLG=6,NSSTA=2,NUSTA=1,NPSTA=0`, all six **45-record** hourly inventories, field label ordering and time continuity. *Only after the native binary has already executed* does the comparator read original physical output for first-hour numeric comparisons.

43 real output labels × 6,970 grid points = **299,710** individual REAL4 comparisons. Source-scoped frozen field-specific absolute tolerances: U/V/W/USTAR/WSTAR 2e-4 m/s, T/TEMPK 2e-4 K, ZI 5e-3 m + rel 5e-5, QSW 2e-4 W/m², RHO 2e-4 kg/m³, EL abs 2e-3 m + relative 1e-4 (neutral marker magnitude greater than 1e8 uses frozen 2048 m tolerance reflecting single-precision/format representation). Any original hour, label, station count, raw field extent, nonfinite numeric or frozen threshold mismatch **blocks merge**, reporting per-label worst i,j.

## Strict exclusions

Neither `IPGT` nor `IRH` numeric output is certified here, so **45-field P6F is NOT_ACCEPTED**. Not a legal full output file, not a native production P6F writer, not G14 causal six-hour commit, not P7, no wet deposition. Next: strict original `IPGT/IRH` two-integer source parity, then native 45-field full output through P6F writer, followed by 6-hour *causal* state transitions (not resetting each hour or backfilling reference state). Existing C1/C2 143h evidence remains unchanged and no Copilot review is requested.
