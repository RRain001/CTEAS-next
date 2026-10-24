# S4-R1c9l — original CALMET DIAGNO stage 3 independent intermediate evidence

## Scope and exact provenance

- Parent Draft PR #299: fac4cb3274cef93a98e5e800bd861bff19daaa95.
- Authentic NOAA 2022-06-01, 82×85×9, 2 surface stations, 1 upper station, six consecutive hours, 63 GEO water cells.
- Original CALMET 6.5.0 source (read-only /home/lhy/CTEAS): SHA256 835c351d780c0200be721c2d9cbb8dc45b3a8fcd4cb8815fc47bbd26a56a7b23.
- Independent original source **instrumented only in scratch**: scripts/s4/s4r1c9l_original_g22_trace.py prepare. This inserts write-only Fortran stream probes into DIAGNO; no equations, guards or model input were changed. No original/vendor source is committed.
- Instrumented original executable: local SHA256 5998beb84d7f302dc2e33156824af1f1b43a075c3b3cd010cf88dcd9886fba82; built on Ubuntu 22.04 using GFortran 11 with legacy fixed-form and -O0.
- Original full six-hour MET.DAT (pristine and instrumented) **byte-for-byte identical**, SHA256 a7004fbf780212d58536be3957306c2aecc53abe2e58bfec870571b12d8b8e14.
- Original G22 stage trace SHA256 b6d96dab81af8e9cba89ef55d386aba8082d9136aa7ef569ad0f9e39f1e31869; stored privately at /home/lhy/dev/CTEAS-next/local-science/s4-r1c9l-hour3-original-g22-20261024/run/met/S4_DIAGNO_G22.BIN.
- Exact input SHA256: GEO.DAT 5feaa58e5835576b3ae2c03a51e955114d620a7aeb710ded58a9f999695f602a; met.inp c5e6b02ac623a3f7d11b464deca657cd26285605753ef185bcc215257dee9744; SURF.DAT 6a3f45eebdba8c7b783b5b89d5e1b3a7eecf2ce71f7fdaa814e7a54f04a9f655; UP.DAT a4e99dabe6ed246643bb298c3d883c8cde8a5dd07aaa346952f7e096d325ad00.

## Original stage probes

Six hours × five DIAGNO stages = **30 original Fortran events**, all 82×85, stage-50 slope additionally nine layers.

| Stage | Original source boundary | Captured fields |
|---:|---|---|
| 10 | second SURFVAR before HEATFX | TEMP2D |
| 20 | HEATFX after FRADJ | TEMP2D, QH, QSW |
| 30 | AIRDEN after HEATFX | RHO |
| 40 | ELUSTR after AIRDEN | QH, USTAR, EL |
| 50 | SLOPE before wind addition | USLOPE, VSLOPE at nine levels |

Water cells were identified from the original GEO.DAT land-use mask (codes 50–55), not assumed from QH. For all six hours, the QH==0 mask independently matches exactly those 63 GEO water cells.

| Model hour end (UTC) | WATER QH=0 / 63 | WATER USTAR nonzero | WATER EL nonzero | WATER slope nonzero components |
|---:|---:|---:|---:|---:|
| 02:00 | 63 | 0 | 0 | 0 |
| 03:00 | 63 | 63 | 63 | 0 |
| 04:00 | 63 | 63 | 63 | 0 |
| 05:00 | 63 | 63 | 63 | 0 |
| 06:00 | 63 | 63 | 63 | 0 |
| 07:00 | 63 | 63 | 63 | 0 |

The third model hour ends **04:00 UTC**. Original DIAGNO has nonzero water USTAR at all 63 water cells (range 0.02599449–0.12020228 m/s) and nonzero water EL at all 63, even though water QH remains zero and the original water SLOPE additions are all zero. First hour (02:00 UTC) water USTAR and EL are zero. This is a **history-dependent source behavior** that requires a field-by-field causal audit before G22 can be unlocked. It is not evidence that C++ has already reproduced the same water-state lifetime.

## Commands and private output

1. Generate scratch-only Fortran copy using scripts/s4/s4r1c9l_original_g22_trace.py prepare with the pinned vendor source and a NEW private output path.
2. Compile only the instrumented copy with GFortran 11 using the read-only original vendor directory as an include path; run in an isolated directory with the exact original P1–P5 GEO/SURF/UP/met.inp paths.
3. Run the script's verify command with the original source, full six-hour trace, uninstrumented and instrumented MET.DAT, original GEO, control deck, SURF and UP.
4. Unit tests: python3 scripts/s4/test_s4r1c9l_original_g22_trace.py -v (four software tests PASS).

The verifier fails closed on SHA drift, MET output mismatch, malformed stage/clock/shape, missing six hours, GEO water-mask changes, unexpected water-history/slope behavior and nonfinite data. All generated original source, executable, raw 4.2 MB stage trace, original inputs, raw MET.DAT and private JSON remain **outside Git**, under the local-science scratch directory.

## Admission

- **PASS_ORIGINAL_G22_TRACE_BYTE_IDENTICAL_ONLY**: independent original DIAGNO stages are captured and final MET bytes unchanged.
- **NOT_RUN**: native C++ G22 hour-three intermediate array-by-array comparison with this original trace.
- **NOT_ACCEPTED**: G22 hour_index>1 production, G26B, G63, G64, G14 hours 3–6 and P7.
- Do not remove or weaken existing scientific guards. Next stage is a strictly test-only native third-hour stage-3 trace with the same committed hour-two state, then per-cell original/native comparison of TEMP2D/QH/QSW/RHO/USTAR/EL and 9-layer SLOPE before considering an hour-three admission change. Original WATER friction/EL history must not be silently replaced with zeros or stale first-hour values.
