# Issue #40 — S4-R1c7a genuine NOAA original STHEOR / SIMILT oracle

Date 2026-10-22. Base main@5088a0d36146447216890019ba3c06f4df580b4a (S4-R1c6 accepted).

## Why this scientific prerequisite is needed

Accepted PR #246 independently established actual 2022 2SS/1US mixed 82×85×9 LAND/WATER post-G22 SLOPE original-vs-native first-hour U/V numerical parity for all 125,460 U/V values. However, the existing G17C3 STHEOR/DIAGI source adapter rejects missing or calm surface winds. The actual NOAA six-hour source contains missing surface wind observations, and original CALMET's station interaction cannot be inferred by disabling this guard. P5's user-chosen missing/calm protocol must remain unchanged. G23/INTER2 must not consume forged SS columns or PREPDI upper fields.

S4-R1c7a introduces a SHA-pinned source-only trace from the **unchanged original CALMET 6.5.0** ELUSTR2 after its actual SIMILT invocation, not from a synthetic fixture. The trace captures original (IS,JS), surface-station column ordinal NS, and 9-level US(K,NS)/VS(K,NS) return arrays for every actual original invocation, over the original genuine six-hour 2SS/1US real NOAA source. Original source blob: 437f43bb7f0e51a1919e56664663e1a046986ed0.

## Guards and flow

- No vendor source is edited, stored or republished. The original Fortran is copied to temporary build scratch, and only a **write-only** statement is added directly after the source SIMILT call. No physics branch or return value changes.
- Existing genuine R1c3/R1c6 workflow regenerates identical real site source fields, separately runs a pristine original to produce baseline MET.DAT and the fresh scratch original with write-only station trace.
- Enforce original 6h x 45-field output **byte-identical**; require ordered complete formatted station records, bounded station cell coordinates, exact original surface-station column identity, and finite captured arrays; distinguish station column NS from an independently determined valid-level count. Record actual original call count; do **not** presume every sparse station is a valid DIAGI profile.
- Keep source clock mapping to individual station call events and source missing/calm replacement rules as **NOT_YET_ESTABLISHED**, explicitly report numeric parity and G23 full-field science **NOT_RUN**. This prevents false acceptance of any native station result before original behavior is understood.
- In particular, original U/V station trace is NEVER a native input or independent permission to treat P5 missing winds as valid zero/calm.

## Acceptance

At most PASS_ORIGINAL_STATION_PROFILE_REFERENCE_ONLY conditional on exact-head authentic vendor workflow success and frozen C1/C2 original comparisons. G17C3 real multi-station sparse mapping and scientific parity, G23 native INTER2, G24 final 3D wind, G26 six-hour original 45-field and P7 all remain **NOT_ACCEPTED**.

Next R1c7b: use real source and exact original station call records to resolve each true SS and UTC hour, preserve missing surface mask, independently re-run already accepted C++ station ELUSTR2/MIXHTST/SIMILT and assert field-level parity; only then connect same source G23 INTER2 over 82x85x9 for independent genuine-original U/V parity. Reuse existing G17C3 and G23 numeric kernels with a source-accurate adapter, no new site-specific formulas and no Fortran oracle injection.
