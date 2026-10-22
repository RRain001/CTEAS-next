# Issue #40 — S4-R1c8n source-native first-hour hidden state carrier (G62)

2026-10-22. Independent original DPTT COMMON tracing and first-hour numeric comparison were started under Draft PR #265. This G62 package is an **implementation prerequisite** for eventually executing a genuine next hour, and it neither replaces nor bypasses that original source-science gate.

## Design

A valid one-hour, 45-field CALMET.DAT file cannot carry `ZICONV` or `DPTT`; these are **internal state**, not P6F output. Neither original nor native `CALMET.DAT` is an acceptable source of next-hour `ZICONV/DPTT`. Reusing the original CALMET ground truth as native forcing is forbidden.

The new `g62_real_noaa_firsthour_memory_seed(paths, explicitly_forensic_only)` constructs the C++ `p6::NativeGridMemory` from **actual native G54 physical results**, namely:

- `post_comp.zi_m` = post-LAND-MIXHT **and** post-AVEMIX ZI;
- `post_comp.ziconv_m` = post-AVEMIX ZICONV;
- `post_comp.dptt_k` = post-LAND-MIXHT source-computed DPTT, **not** an inferred output-field quantity, not a zero-filled guess, and not spatially averaged by AVEMIX.

It independently runs source-only G59, verifies the 45-field output's legal `ZI` value is **bitwise equal** to G54 post-AVEMIX ZI, and verifies the *original-source* first-hour UTC clock and cold-start previous COMMON. The actual input case remains NOAA 2022-06-01 01:00–07:00 UTC, 2SS (one true wind missing), 1US, 82×85×9, 6907 LAND/63 WATER.

G62 exports an **uncommitted, explicitly test-only** evidence file: ASCII `CTEAS_G62_SEED_1` magic (16 bytes), little-endian 4×int32 `NX, NY, NZ, NH`, int64 UTC end epoch, and 3×6970 REAL4 planes in i-fastest, each one in `ZI, ZICONV, DPTT` order. No shader/restart/production acceptance or claimed durable G14 commit. This binary artifact is *not* an original CALMET result or an external input to G26/P7.

## Independent verification

The new Python G62 comparator runs after the existing independently certified G54 (real MIXHT/AVEMIX), G59 (real 45-field P6F), and G60 (mixed real hidden ZI/ZICONV). Require provenance SHA256 and original MET unchanged. Check all **20,910** native REAL4 words across G62 vs G54 **bitwise**, plus all 6970 `ZI` words against G59's physical `ZI` record. Reject forged source hour, dimensions, wrong endian/extent, altered hidden DPTT (even if the output 45 fields stay the same), and any attempt to synthesize hidden memory from the output. Negative tests are source-independent.

G61 (PR #265) independently establishes original/native DPTT parity. **G62 verification is not a substitute for G61 and does not promote full G14 17-stage native physics.**

## Next physical milestones

Only after G61 original/native DPTT PASS: bind the three G62 arrays as the **candidate physical history** for subsequent PREPDI, while retaining the one authoritative G14 stage transaction and the **station AA/BB + CGAMMA** clock authority. Bring each branch of current-hour physical kernels under one runtime and prove actual second-hour fields against independent original. Reject hour skipping and abort without state publication; then extend to six hours and all original 45 fields with scientific evidence. C1/C2 general production and P7 are still blocked. No full 143-hour automatic validation; Issue #40 OPEN.
