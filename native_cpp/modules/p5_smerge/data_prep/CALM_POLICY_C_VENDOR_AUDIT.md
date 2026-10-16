> **HISTORICAL SOURCE AUDIT ONLY.** As of 2026-10-11 the P5 active source-wind policy is v2 whole-vector hold + user-prescribed calm replacement. This Fortran audit remains valid as a line-level source comparison but its Scheme C numerical input policy is not used. See ISD_LITE_HYBRID_WIND_POLICY.md.

# Scheme C: scoped P5 wind input and original SMERGE/CALMET Fortran audit

Date: 2026-10-10. Source files remain read-only.

SMERGE authority: engine/vendor/src/SMERGE_v5.7.0_L121203/SMERGE.FOR, blob a4315036dae437977d9c90ab5abbb8b8085018d5.
CALMET authority: engine/vendor/src/CALMET_v6.5.0_L150223/calmet.for, blob 437f43bb7f0e51a1919e56664663e1a046986ed0.
Project control: engine/templates/met.inp, ICALM=0.

## Measured source behavior (not assumed)

| Place | Fortran lines | Finding |
|---|---:|---|
| SMERGE GENERIC JDAT=8 | 2667-2704 | Reads XCWD/XCWS from input; when neither is 9999 and direction is 0-360, copies them to XWD/XWS without a 0.5-speed clamp. Invalid direction invalidates both. |
| SMERGE output and validation | 2800-2829 | Writes XWS/XWD to SURF.DAT; counts exact-zero speed in NCALMS. |
| SMERGE native ISH decoder | 5161-5198 | In the DIFFERENT ISH branch, type C or valid WS<0.1 m/s maps to WS=WD=0, type V or invalid QC maps to missing. Does not apply to JDAT=8. |
| CALMET land stability calculation | 6432, 6445-6447 | WS=MAX(WS, 0.001 m/s), local friction/stability numerical guard. |
| CALMET stable calculations | 6507-6512 | Local WS=MAX(WS,0.5 m/s) for stable Ustar/ThetaStar/HQ only. Does not replace source speed. |
| CALMET extrapolation | 6695-6704 | Skip extrapolation when WS<0.001 m/s, in one routine. |
| CALMET overwater-related extrapolation | 33852-33858 | Skip extrapolation for WS<0.0001 m/s in another routine. |
| CALMET surface station upward extrapolation | 36110-36125 | WS10<0.0001 m/s: fill temporary extrapolated U,V=0 instead of normal extrapolation. |
| CALMET weight rebalancing | 36292-36316 | ICALM=0 removes the vertically extrapolated calm-station contribution aloft and rebalances other station weights. |
| CALMET control | engine/templates/met.inp line ~538 | ICALM=0 means do not extrapolate calm winds aloft. |

These numbers are NOT one universal CALMET minimum or threshold. CALPUFF's WSCALM=0.5 m/s (engine/templates/puff.inp) is a separate model control, not P5/SMERGE/CALMET source-wind conversion.

## Implemented P5 Scheme C boundary

- NOAA downloaded CSV is immutable input evidence. Wind speed/direction are decoded by named WND field.
- Independently carry previous valid speed and direction forward across any missing-hour duration, preserving observed values and source timestamps in the per-hour audit. Missing before the first observation is never backfilled.
- Export speed to GENERIC directly: 0.0 -> 0.0; 0.2 -> 0.2; no artificial WS=0.5. A 0.5 m/s threshold remains purely an audit flag named is_calm with calm_limit_usage=LOW_SPEED_DIAGNOSTIC_ONLY. The exact-zero flag is separate.
- At an exact zero-speed hour, directional vector is undefined. To satisfy SMERGE's JDAT=8 pair validation, encode WD=0 degrees ONLY for GENERIC; preserve source and filled original wind direction in audit. This is not a wind from north.
- For nonzero speeds, direction is source or preceding valid direction. Previous scheme's shortest circular-arc interpolation is not applied in main GENERIC or audit statistics; no synthetic wind-direction time trend.
- Audit adds wind_speed_generic_m_s and wind_direction_generic_deg; old wind_speed_calculation_m_s is an unclamped compatibility alias for the P5 output. Raw and source timestamps are retained.
- CALMET originally decides calm extrapolation and local numerical bounds during diagnostics. No change to original Fortran or CTEAS non-scoped Python code.

## Validation limits

Python tests cover 0, 0.2, 1 m/s; stale wind source; 0-speed missing direction; no-leading-observation behavior; static assertions against vendored Fortran exact statements. Hosted real-case 2022 station capture and transformation must test that if the source contains 0 or below-0.5 winds, output preserves them.

This is a changed scientific policy: output is intentionally different from historical P5-inserted 0.5 m/s records, and cannot be deemed byte-identical to the *old P5*; an original CALMET/SMERGE reference must be rerun on the *same new Scheme C* input to verify physical/numerical consistency. Full end-to-end CALMET/CALPUFF compatibility remains pending until this gate.

## Reproducible real-case regression gate

The hosted 2022 Hefei 144-hour capture now executes validate_scheme_c_capture.py after generating the ready GENERIC file. It asserts the full per-hour match against the independently archived wind-audit speed and source-forward-filled values, preservation of exact zero and fractional low-wind speed, station identity, and the distinction between diagnostic threshold and computation minima. The script exports run-evidence/p5-scheme-c-audit.json with counts and fails on any speed clamp or lost station hour. The original CALMET/SMERGE executables are not invoked as part of this regression.
