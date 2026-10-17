# P6G G18C1–G18C3 — original COMP AVEMIX → WSTARR → TEMP3D (2026-10-14)

PR #63 stacked on the accepted PR #53 frozen 163-file physical baseline. The original Hefei deck has `IAVEZI=1`, `MNMDAV=1`, `HAFANG=30.`, `ILEVZI=1`, `IRAD=1`, `ITPROG=0` and `LCALGRD=T`. This is a **selected/test-only** branch, not the whole native G14 multi-station 45-field CALMET science certificate.

## CALMET 6.5.0 source-order correction

Original COMP calls:
`MIXHT → (IAVEZI==1) AVEMIX(nx,ny,mnmdav,hafang,dgrid,U(ILEVZI),V(ILEVZI),ZI,ZICONV) → WSTARR(ZICONV,QH,TEMP2D,RHO) → TEMP3D(TEMP2D,ZICONV,TZGRAA,TZGRBB,...)`.

G18A provided a *partial* WSTARR on pre-average ZICONV. That is not valid final source COMP WSTAR for the pinned `IAVEZI=1` configuration. For G18C, all subsequent convective velocity and 3D temperature computations **must use the post-AVEMIX ZICONV**, and the no-premature-state-commit rule remains enforced.

## G18C1: newly reconstructed original AVEMIX with separate literal-vendor numerical oracle

There was no already accepted stand-alone PR #53 AVEMIX kernel to reuse. New `p6g_g18c1_avemix.hpp` reconstructs the **actual** CALMET 6.5.0 `AVEMIX` original code: source DTDX=3600/DGRID, REAL*4 TAN/ATAN2/AMOD half-angle, INT truncation of the upwind triangle/crosswind extents, source neighbor search order, square neighborhood, wind-dependent truncated upwind cone, original weight `1/(DELA**2 + (1+ABS(DELC))**2)`, and **separate** ZI/ZICONV destination arrays (no in-place contamination). It consumes the *actual* G17D native selected U/V wind at `ILEVZI` and the G18A candidate MIXHT heights, not a fabricated independent wind or a previous-hour grid.

Strict parser `g18c1_parse_original_avemix` pulls `IAVEZI, MNMDAV, HAFANG, ILEVZI` from original `met.inp`, rejects unverified options. Selected `g18c1_selected_after_mixht` is gated by same-hour source geometry and test-only provenance and never commits the candidate.

Independent scientific oracle `reference/compare_original_g18c1_avemix.py` extracts the **literal original Fortran AVEMIX subroutine body** from unchanged `calmet.for` and compiles it using gfortran and a params.met *dimensions-only* stub. A C++ CLI calls the actual new adapter. 13 source-selected 0/negative/positive winds, square and upwind cone, various `MNMDAV`, grid sizes and spacing cases compare **exact REAL*4 bits** for ZI and ZICONV (no loosened numerical tolerance). The new CTest is added to both GitHub-hosted Ubuntu Debug/Release jobs.

## G18C2: reuse accepted PR #53 WSTARR after AVEMIX

New `p6g_g18c2_wstarr_after_avemix.hpp` composes the **unchanged** PR #53 `p6e::wstarr`, using source G18C1 **averaged** ZICONV, G17C2 source ELUSTR-updated QH, G17C1 second SURFVAR `TEMP2D` and AIRDEN. It carries the G18A (MIXHT/STHEOR) **current-hour DPTT mutation** unchanged, carries averaged ZI/ZICONV as a candidate, and does not replace the previous committed G14 state or claim full `CompWstarr` completed. The selected test requires exact equality to a direct frozen WSTARR invocation on post-AVEMIX ZICONV and rejects partial/fake provenance.

## G18C3: reuse accepted PR #53 original TEMP3D with actual multi-UP FACET

New `p6g_g18c3_temp3d_after_comp.hpp` consumes:
- G18B1/B2 actual original multi-UP AA/BB and per-US JUSTA/past/to-go seconds (including asynchronous/cross-year model-hour accounting);
- G18B5 frozen `calmet_facet_temperatures` on the exact source `ZFACE[1..10]` per physical AA/BB upper station;
- G17C1 true second post-FRADJ SURFVAR TEMP2D;
- G18C2 **post-AVEMIX** ZICONV for convective temperature correction;
- ordered real station UTM positions, source `IRAD`/ITPROG/LCALGRD controls and 9 source vertical layers.

It delegates the entire formula to **unchanged PR #53** `p6e::temp3d_observed_land`; current-hour modulo-12 is only used to satisfy the selected one-site source interface, while each US true time difference comes from explicit original G18B bracket intervals. Validates exact FACET source payload and station order, hour stamps, all-land scope and finite source fields; rejects wrong hour, forged AA/BB temps or unsupported branches. Selected tests compare all nine native 3D layers exactly with independent direct #53 TEMP3D invocation, including first layer equal to second SURFVAR TEMP2D.

## Do not overstate the results

These are components in **source-correct COMP physical order**. Upstream full production multi-station DIAGNO/COMP callbacks are not yet all `{NativeCpp,true}`; selected test-only fixture coefficients in G17C1–G18A still require authentic per-hour source controls and complete G14 input authority. Original AVEMIX vendor parity is a newly added independent code/CI gate; selected WSTARR/TEMP3D equality is to frozen #53 kernels. PR #53 physical implementation and its strict 143-hour 45-field science gate must remain green. The target for PR #63 acceptance is real complete multi-site 1h/6h/143h/year original Fortran **45-field** equivalence under one G14 production scheduler with P6F, not mere selected 2SS/2US fixture tests.

CI: `P6G multistation on accepted single-station baseline`, GitHub-hosted Ubuntu only. Verify the **exact** PR #63 commit before marking Debug/Release/AVEMIX vendor test passed; this document is not an automatic scientific acceptance.

## G18C4 — complete eight-field G14 current-hour candidate, still uncommitted

The additional selected adapter `p6g_g18c4_selected_hour_candidate.hpp`
assembles the existing G17D native U/V/W, G17C2 source ELUSTR
QH/USTAR/EL, G18C2 post-AVEMIX WSTAR, G18C3 3D TEMP and
G18C2 averaged ZI/ZICONV/current MIXHT DPTT into precisely the **eight
`NativeHourFields` arrays** and `NativeGridMemory` specified in frozen
PR #53's `hourly_comp_scheduler.hpp`. All field and memory sizes,
original station order, same source hour, finite values and missing sentinels
are checked. The selected test compares all component arrays exactly with
their upstream source-ordered producer and rejects synthetic scientific
promotion, missing 3D temperature, and premature `frame.next` state changes.

**This is not a complete 17-stage `MultiHourPhysics` implementation.**
G14's `CommitOutput` must still be authorized only after full real-source
PREPDI/DIAGNO/COMP and native P6F have completed and been scientifically
checked; this candidate object has no method to publish a completed hour.
The next stage must use the existing G14 execution authority rather than
building a second scheduler. Full real multi-site 45-field vendor verification
remains an explicit prerequisite.
