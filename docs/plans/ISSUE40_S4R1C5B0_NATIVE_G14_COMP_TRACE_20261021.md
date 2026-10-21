# Issue #40 — S4-R1c5b0: observe native G14 committed COMP chronology

Date: 2026-10-21. Base: main@f41706210372ecc135df3d78babe5d2db120c800 after independently accepted original **reference-only** S4-R1c5a / PR #244.

## Why this prerequisite belongs on unified G14

Original 2SS+1US real NOAA, 82x85 (63 original WATER cells) S4-R1c5a independently confirmed 83,640 PRE-DIAGNO / POST-COMP ZI/ZICONV records and exact original 34,850-cell-pair hour-boundary propagation. That original-only result is NOT a native hourly field calculation and must NEVER be injected into the candidate solver. Existing accepted C1/C2/Huoshan shared G14 physical actor is G34BSelectedOnlyHour, driven by p6g_s4b2_unified_selected_main.cpp.

Before implementing WATER-aware native six-hour G14 physics, add **no new CALMET physical formula or site-only executor**. Instead the same unified selected CLI can optionally trace its already fully committed native ZI, ZICONV and DPTT for up to six consecutive hours. On each successful G14 transaction, capture the previous immutable committed state, demand bit-exact equality with the last committed POST-COMP state, and capture the current committed state only after all native stages, P6F precommit and station-clock publication pass. The trace never writes to G14 memory or station inputs.

## Changes and negative checks

- Optional --native-comp-trace PATH is experimental-only and coupled to existing --selected-experimental admission. It does not authorize normal G26 or production. Traces are restricted to six executed hours and up to 10,000 cells to avoid unbounded buffered evidence. This is not a physical station/grid or S5 expansion limit.
- A trace includes hour ordinal, UTC end epoch, stage PRE_DIAGNO or POST_COMP, 1-based (i,j), and hex-encoded native float ZI/ZICONV/DPTT. POST must come from scheduler.committed_memory() after a full successful native transaction.
- scripts/s4/s4r1c5b0_native_comp_trace.py checks entire grid, ordered source UTC hours and exact bitwise POST of hour h = PRE of h+1. It rejects nonfinite/negative mixing-height fields, incomplete/duplicate rows and tampered previous-hour memory (built-in self-test).
- Existing C2 six-hour software regression workflow compiles/runs the SAME shared G14 binary with tracing enabled and verifies that old C2 executable and traced unified candidate produce byte-identical original-format MET.DAT. It validates 12x12x6x2 = 1,728 traced rows and five x 144 = 720 carried cell-pairs. Require exact-PR-head Actions success.

## Acceptance boundary

After CI success this is at most PASS_SOFTWARE_CAUSAL_STATE_TRACE_ONLY. Reference-only actual NOAA original R1c5a remains separate. No row from its original ZI/ZICONV trace enters the new C++ executable or computation. C2 controlled synthetic source is NOT genuine observed 2SS+1US WATER. Writing a trace is NOT WATER MIXHT/AVEMIX physics.

Required follow-on R1c5b:
1. Reuse SAME G14 source/physical kernel path. Admit authentic 82x85 real 2SS+1US with G43 CALMET-internal nonwind MISSFC, leaving user-approved P5 missing/calm policy unchanged.
2. Reconstruct genuine WATER ELUSTR/WATER friction and mechanical mixing-height prerequisites before G26B MIXHT/AVEMIX. Preserve original stage sequence and ZI, ZICONV, DPTT state ownership; never reset previous each hour.
3. Execute original-source real NOAA six-hour native G14 with trace. Independently compare PRE/POST per hour/grid against R1c5a original reference with frozen numerical tolerances and source SHA, separately land/water. Require nonzero, evolving fields. Neither original MET nor original state enters native inputs.
4. Complete G21/G39, G22/G23/G24 and G26 original 6h x 45-field comparisons, then #36 P7.

No Docker, wet deposition, P7, S5, altered P5 wind valid/calm masks or guessed vendor inputs.
