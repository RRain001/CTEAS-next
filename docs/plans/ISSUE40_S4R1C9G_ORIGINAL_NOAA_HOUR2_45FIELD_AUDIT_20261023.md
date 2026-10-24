# Issue #40 — S4-R1c9g independent original-vs-native NOAA hour-two P6F audit

Stacked on draft PR #294 (`ce295493b8f96295d124ce80bc50855785e95d60`). The source case is the strictly scoped 2022-06-01 02–03 UTC second hour, 82×85×9, two observed surface stations, one upper-air station and 63 WATER cells. No generic P6/P7 acceptance is implied.

## Independent physical reference

- Original: the **untouched six-hour CALMET 6.5.0 Fortran** MET.DAT, generated in the same authoritative S4 workflow from the exact NOAA P1–P5 forcing. The unchanged original is only read by the separate Python comparator, never by the native G14 actor. Original vendor source stays at the pinned private checkout and must not be published.
- Native: after second-hour G26A/G26B stages 0–16 and three source-native candidate/replay checks, an explicit forensic flag allows the G65 CLI to write the **unpublished** G18D1-validated P6F candidate to a scratch path. Without this flag it writes no file; the code cannot commit second-hour G14 memory or station clocks.
- Scientific comparator: `scripts/s4/s4r1c9g_compare_noaa_hour2_met21.py` independently reads Fortran record markers, original six hourly groups and only hour index 1, and the native one-hour 45-record candidate at the same UTC second hour. It requires fixed grid/station/header/layout, both integer fields exactly, and all 43 REAL4 fields under the **existing** G57 source-scoped per-field frozen tolerances. No change to tolerances is permitted.
- The comparator reports all 45 field-wise maxima, exceedance counts, first differences and SHA-256 of both data files. Nonfinite data, wrong timestamps, missing hours or fields and mismatched source shape fail closed. The synthetic selftest exercises exact equality, mutated float, mutated integer and shifted-clock rejection; this is a parser test, **not** atmospheric verification.
- A GitHub workflow step enforces zero exceedances; it uploads numerical receipts only. The original six-hour MET.DAT and the uncommitted native candidate bytes remain temporary and are **not uploaded** as artifacts.

## Acceptance boundary and evidence

The predecessor PR #294 passed 54/54 GitHub checks including native second-hour stage16 precommit as of the 2026-10-23 audit. That verifies a 313,650-word native-source reconstruction, **not** independent original second-hour physical equivalence. The exact-head Ubuntu local Docker image could not build due to 502 errors from the locally configured proxy during Debian dependency downloads, including binutils, libhdf4 and libnuma. It is `FAIL_BUILD` (infrastructure), not a C++ software failure or a full regression PASS.

This stage's original-versus-native numerical result remains **NOT_RUN / NOT_ACCEPTED** until its own exact SHA's workflow finishes and the report is inspected. Any mismatch is a scientific failure requiring first-difference investigation; do not convert the full comparison into log-only evidence, relax thresholds, or claim PASS from the synthetic selftest.

Second-hour atomic commit, publication of AA/BB/CGAMMA clocks and ZI/ZICONV/DPTT, causal 3–6 hour operation, new-site generic P6, P7 and wet deposition all remain **NOT_ACCEPTED** even if this limited field comparison passes.
