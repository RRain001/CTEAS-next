# Issue #40 S4-R1c9f — real NOAA hour-two P6F stage16 precommit

**Stacked on:** S4-R1c9e PR #284, exact base `387a8a24aca7d907f3f50cee03ba3cd142450e8b`. Selected 2022-06-01 02–03 UTC, 2 observed surface stations, 1 upper-air station, 82×85×9 with 63 WATER cells. **No generic or production CALMET acceptance.**

## Native contract

- Reuse the *same in-flight* G14 hour-two G26B state after real stages 0–15. Compute the P6F 45-field candidate using G64, G18C6 and G18D1, not first-hour or frozen MET.DAT values.
- Evaluate a detached G26A/G26B 17-stage causal replay and one additional direct G64 source candidate, and require 45 × 82 × 85 = **313,650 field words** to match (REAL4 bitwise, INTEGER4 exactly). Also require byte identity of three prepared-but-unpublished candidate images, matching source hour, candidate memory, and correct native stage ordering.
- Permit hour index 1 **only for the existing selected source-scoped research path**. No other later hour, production branch, changed source station cardinality, or new physics option is accepted by this change.
- **Never commit second-hour G14 state**, never publish candidate AA/BB/CGAMMA clocks, never write accepted CALMET.DAT, and never mark the candidate as ready for hour three. The scheduler's committed hour count must remain one, and its first-hour ZI/ZICONV/DPTT and published station clocks must remain bitwise unchanged.
- The two G26B runs and direct G64 candidate use the same native kernels, so this is causal-source consistency, **not an independent original Fortran second-hour 45-field comparison**. This cannot supply the scientific-admission evidence alone.

## Validation status

- Historical exact-base PR #284 GitHub workflow run 39918760666: stage15 source-native comparison **PASS_SCOPED** at 62,730 REAL4 words, no stage16.
- This new stage16 change: Ubuntu C++ compile result and Docker SHA-specific smoke/full must be reported separately; they must not be inferred from #284 or historical C1/C2.
- Authentic NOAA hour-two stage16 execution; pristine CALMET Fortran hour-two original-vs-native 45-field comparison; hour-two atomic commit, hours 3–6, other sites, P7, wet deposition: **NOT_RUN / NOT_ACCEPTED** until evidence is obtained.

## Scientific blockers

The original same-input CALMET second-hour 45-field oracle and independent reviewer must validate first differences, preserved mass/physical budget, and hour-two state before relaxing fail-closed publication. Draft PR is mandatory until the exact SHA's applicable software, GitHub and scientific gates are all satisfied.
