# P6G G18D1–D2 — sole G14 precommit P6F barrier and AA/BB–CGAMMA transaction

Date: 2026-10-14. PR #63 (Draft), still stacked on the independently accepted
PR #53, whose 163 frozen P6 physical sources **must not change**. This is
incremental state/control integration; it does **not** certify original-vendor
multi-station 45-field 1h/6h/143h/year scientific equality.

## Previously established selected physical input/output chain

G18C1–C6 now constructs the explicit 2SS/2US physical **candidate**:
original G17D U/V/W, G17C P6E heat and density, G18A MIXHT,
G18C1 *new original-vendor-bit-parity-checked* AVEMIX, frozen WSTARR,
true G18B AA/BB temperature via frozen FACET/TEMP3D and a 45-field
source-owning CALMET.DAT 2.1 candidate. The frozen P6F writer and an
independent Python Fortran-byte parser both accepted the selected
1-hour file (Debug/Release 21/21). Fixture heat coefficients and
incomplete G14 full 17-stage production callback **still remain**.

## G18D1: G14 precommit native output gate

The **same** `UnifiedMultistationHourlyScheduler` now exposes
`advance_with_precommit(physics, verify_output)`; the original
`advance(physics)` remains the existing synthetic/test entry point.
The output validation runs only AFTER the original 17 stage list from
frozen PR #53, strict `{NativeCpp,true}` for every stage, complete eight
native physical arrays and valid next-hour ZI/ZICONV/DPTT — but
**BEFORE** the sole `memory_ = std::move(frame.next)` and hourly index
increment.

- An exception in the output gate preserves exact original committed
  previous-hour ZICONV/DPTT and the original hour index. The same input
  hour is retried, and no future hour is silently selected.
- New `p6g_g18d1_p6f_precommit.hpp` can verify a selected 45-record
  native P6F candidate against the actual *in-flight G14 frame*.
  It checks GEO/CRS/ZFACE/station order/clock identity and requires
  every native U/V/W top-face/T/USTAR/ZI/EL/WSTAR P6F value to agree
  exactly with the current G14 physical arrays — rejecting valid-
  looking original/reference-derived substitute fields. It calls the
  frozen P6F binary serializer for complete run-clock, statics, kind
  and record validation. The result is **prepared binary bytes**, not
  an externally published final file. A separately validated G18C5/6
  candidate still owns IPGT/IRH, TEMPK/RHO/QSW sources.
- G14 1h/6h/143h/8784h tests retain source-accepted stage order and
  synthetic physics status. New G18D1 tests inject output failure
  after all 17 stages, re-run the same hour and then verify second-hour
  previous ZICONV. The G17C–G18C6 source-selected test injects modified
  U wind, averaged ZI, WFACE, cross-hour and upper-station metadata to
  prove all source ownership checks fail closed.

**The callback must not publish external final output or advance separate
station clocks**: it verifies a prepared candidate before the sole G14
logical memory commit. Actual durable file publication/rollback and
process-crash atomicity remain to be designed and validated separately.

## G18D2: source AA/BB and per-UP CGAMMA commit coordination

The source PREPDI upper cache and per-US CGAMMA state are independent
historical state machines; neither may be committed solely after its
own local success while later COMP/P6F is still incomplete.

- G14 now offers `preview_next_hour()`. The preview is derived from
  **the same** actual station/input/clock authority, references the
  last committed ZICONV as `previous`, and carries a private copy of
  tentative next state; it does not increment or separately choose
  the model hour.
- `G18D2StationClockAuthority::prepare_selected` consumes that preview,
  the source `IUPT/ZUPT/IDIOPT2`, original G18B AA/BB/JUSTA observations,
  and G18B7 per-UP `ZICONV(IIUP,JJUP)`, invoking unchanged PR #53
  CGammaState for all upper sites. It preflights **both** history-clock
  commits on isolated copies, so invalid data at a later station
  cannot partially advance an earlier station.
- Only once the **same** scheduler reports
  `completed_hours == prepared.hour_index + 1` may
  `publish_only_after_completed_g14` install the detached upper/CGAMMA
  clocks. Reused/stale tickets, another scheduler instance, failed
  P6F precommit, and reference-oracle stage injection all fail closed.
  The two state moves are independently proven `noexcept` by
  compile-time assertion so accepted candidate histories are published
  as one logical transition.
- The selected G14 2SS/2US test exercises output-gate failure, same-hour
  retry, second-hour reading from actually committed preceding-hour
  ZICONV and duplicate station-state publication. Its soundings are
  explicitly SYNTHETIC; this verifies transaction contract and not
  complete multi-site original CALMET thermodynamics.

## Remaining acceptance blockers

1. G18D3 and later: produce actual source-derived (not fixture) G17C
   heat coefficients and G18A all-station physical handoffs and bind
   the verified G18C1–6 kernels to **all 17 real G14 callbacks**.
2. Finish **durable** atomic output publication/restart semantics:
   prepared bytes passing the callback are not sufficient to claim
   crash-safe CALMET.DAT hour commit.
3. Independently compare real 2SS/2US G14 native output against original
   CALMET 6.5.0 all 45 fields at 1h/6h/143h and full year/cross-year.
   Only GitHub-hosted Ubuntu runners. Do not relax tolerance or mutate
   frozen #53 physics. Keep PR #63 Draft until complete.

CI scope: check exact source-code commit SHA before reporting a PASS.
