# Issue #40 — S4-G real NOAA 2SS + 1US same-site source pairing (pre-P6)

Date: 2026-10-21. Follows merged #224 genuine C1 143h independently rerun original CALMET science. No physical G14, G26, G26B or P6F changes.

## Critical geometrical distinction

**The earlier true Huoshan P6 6h case is NOT a genuine two-surface-station case.** It uses a 100×100 @100m WGS84/UTM50N domain with three-decimal origin `462.305,3501.570` km, one virtual 583210 Luogang surface station and one virtual Anqing 58424 upper station; original source wind/upper meteorology was accepted for this scope only.

The genuine two **observed**, **physically inside-grid** NOAA surface stations `58314099999` (Huoshan, IFSTN `583140`, sparse secondary) and `58321099999` (Luogang/Xinqiao, IFSTN `583210`, primary) are in the much larger `426.590,3464.125` km 1-km-resolution grid used by existing Issue #56. **Never reuse the 100×100 Huoshan GEO to run that two-SS SURF.** The known original P5 2022 June 24h case contains 32 populated / 16 missing station-hours of 48 total (P5 original/native raw SMERGE exactly byte-matched); *two stations selected* does not mean *two simultaneous observed wind records every hour*.

## Actual new source-only test

GitHub Actions executes the already existing authentic-source producer pipelines without source-data invention:

1. P4 Anqing `CHM00058424`: replay original archived NOAA IGRA upper observations, run native READ62 and independent original-format UP input parser over actual June 1 2022 01:00–07:00 UTC with real surrounding 00/12 slots; record original raw POR, output binary SHA and exact independently generated large-grid `grid.cmn` SHA.
2. P5 Huoshan + Luogang: replay **the separate existing 2022 annual genuine NOAA ISD+ISD-Lite raw input**, run the existing original SMERGE 5.7.0 and C++ SMERGE using byte-identical GENERIC source, prove original-vs-native raw SURF byte equivalence, then validate the independently published (cloud-policy-adjusted) SURF source at the P6 source reader with **24 consecutive hourly records and both real station IDs**.
3. Independently compare SHA256 of the **actual independently generated original B0 grid files**, frozen 3-decimal origin, observed/virtual flags, aliases, 2022 calendar/source coverage, P4 6h within P5 24h observed window, published SURF hashes, and each source's prior original reader and negative QC verdicts. Reject grid swap, P4 station ID swap, fabricated in-grid station, wrong clock, or fake P6 approval.
4. Upload only bounded source SHA and resulting source join receipt, not private/vendor original code nor NOAA raw weather bytes. This is a new paired, same-geometry **actual-observation** evidence boundary, not separate source-only provenance statements from different domains.

## Hard scientific boundary

`S4G_REAL_NOAA_2SS1US_SOURCE_PAIR=PASS_SCOPED_NO_GEO_G19_P6` may be recorded after the final exact-HEAD workflow passes. It explicitly means **same 1-km-grid P4 and P5 observed-file handoffs have been independently verified**, NOT a complete P1–P5 site nor a true G19 original full input.

Next required prerequisite: generate **new P1/P2-A/P3 GEO.DAT for exactly this larger source grid**, preserving the original selected 38→14 landuse mapping and independent original Fortran MAKEGEO selected-physics comparison; compose the original `met.inp` with source-authoritative 2SS/1US IDs and 2022 01–07 UTC and actual same-case GEO+UP+SURF SHA, including sparse-station handling. Only then run fresh unmodified original Fortran CALMET vs same shared G26 opt-in trial with all 270 field-hour groups and no exceedances; until then `G19_FULL_SOURCE=NOT_RUN`, `P6_FIELD45=NOT_RUN`, `PRODUCTION_ADMISSION=false`.

Do not interpret this PR as 20-site genuine NOAA evidence. S5 memory/chunking, rainfall, Docker and P7 #36 are separately blocked.
