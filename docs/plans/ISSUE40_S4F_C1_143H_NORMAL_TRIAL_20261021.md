# Issue #40 / S4-F — G26 normal-call trial on actual C1 143h

Date 2026-10-21. Depends on merged PR #222: gated normal G26 DIAGNO and G26B COMP `run()` reuse exactly accepted 17-stage selected G14 kernels, but only with `--selected-experimental --g26-normal-entry-trial`. Default production remains denied.

## Independent missing dimension

C2 currently has 143-hour controlled original-format 2SS/2US **freshly re-executed** original CALMET parity. Real NOAA Huoshan has 6-hour independently fresh original, 100×100 1SS/1US. Prior C1 has real 2022 selected 143-hour 1SS/1US and an immutable original CALMET.DAT SHA, but **the original C1 Fortran was not freshly executed**.

This PR tests the **new normal G26 entry adapter** on that C1 actual observational source over its complete 143 hours, without modifying C1 data, source calendar or original field formulas. Both original selected and explicitly opted-in normal G26 routes execute from the exact same actual C1 met.inp/GEO/SURF/UP; all 143×45=6435 groups across all grid nodes must be compared with the pinned frozen original CALMET.DAT using existing P6E tolerances and zero exceedances. In addition, require normal G26 and selected MET to be **bit-for-bit equal**.

Source and reference SHA256, exact checkout SHA, executable SHA256 and Linux peak process RSS/elapsed time are archived. The output is NOT a production artifact and its verdict must say `FROZEN_ORIGINAL_PASS_SCOPED`, not `FRESH_FORTRAN`.

## Acceptance boundaries

This is a full 143h actual source 1SS/1US *software and frozen scientific reference* regression. It does **not** independently recompute the C1 original Fortran CALMET; that work would need a separate fresh-run oracle with exact C1 original inputs/physics, and is not substituted by any C++ output or rewritten reference. Current selected 9-layer physical option only. No P7, no rainfall, no all-options claim, no 20-station cap, no production G26 enablement.

A green CI is sufficient to merge the narrow C1 regression workflow, but NOT to close issue #40. The remaining scientific blockers include genuine observed multi-SS + multi-US input and original CALMET comparisons, an explicit production admission decision, and broader long-duration RAM/streaming acceptance.
