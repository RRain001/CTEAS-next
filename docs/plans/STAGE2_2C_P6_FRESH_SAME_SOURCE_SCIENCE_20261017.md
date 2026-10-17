# S2-2C Hefei 2022 native P3→P6: original CALMET same-source scientific verification

Date: 2026-10-17. Owner authorized running live science on GitHub Actions. **This report is for the selected Hefei 2022 case only.** Original/native scientific thresholds have not been changed.

## Final accepted-scoped result

- Exact native computational source SHA: `8a2d8edb9b764dade39167a73247f9e4ee278b4d` (PR #27, includes mandatory station metadata roles/negative tests).
- Native P1/P2/P3: rebuilt on Actions, using pinned SRTM TIFF SHA256 `c4211914fce527d2ad41ecac1e668d7faa2904bbbfd9135868ee83ef0d32123f` and pinned GENERIC land-use file SHA256 `bd937d99fb13b49ac6185c080359bef050afe76fc63945ac53b7d676547d43dc`. Outputs become freshly constructed original-compatible `TERREL.DAT`, `LU.DAT`, then fresh `GEO.DAT`; historical original GEO is **not** substituted in final science run.
- Native P4/P5: **previously validated frozen Hefei 2022** `up_58424.dat` / `surf.dat` and their respective `stations.csv` metadata copied into the new isolated scratch case, SHA-checked. P4/P5 IGRA/NOAA acquisition and C++ numerical source writer were **not rerun in this particular 2C workflow**.
- Native P6: actual C++ process-per-step P6D/P6E/CGAMMA/BRIDGE/P6F, `--p6e-source-builder` GEO+deck-only original-independent metadata; no historical `run/met/met.dat` exists in staged native case. Real 1h, 6h and 143h completed, produced actual `native_causal_calmet.dat`, and 143h independent header MET with manifest/hashes. This is a selected C++ native implementation, **not** general CALMET options coverage.
- Independent original: pinned `CTEAS@dfad99a78ed84d655e21411c9d25eb0d2583bf13`, unmodified `CALMET 6.5.0` Fortran `calmet.for` Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`; compiled and **freshly executed 143 hours** in its own scratch case using the **identical new native-generated GEO, frozen UP/SURF, and control-deck bytes** as native P6. Original code never used as fallback by native P6.
- Independent comparison: existing `p6e_calmet_dat21 compare` original 143h vs native 143h, 45 meteorological fields, with unchanged field-specific numeric limits; `intervals=143`, `total_exceedances=0`, **PASS_SCOPED**. The Actions comparator success also asserts exactly 143 intervals and zero exceedances, not only process exit zero.
- **Authoritative completed run**: [Actions #39028984274](https://github.com/RRain001/CTEAS-next/actions/runs/39028984274) — SUCCESS, `S2C_SAME_FRESH_GEO_ORIGINAL_NATIVE_143H=PASS_SCOPED`. Only derived non-binary reports/logs uploaded, [metrics-only artifact](https://github.com/RRain001/CTEAS-next/actions/runs/39028984274/artifacts/12100190467); no TIF/original raw MET/vendor Fortran distributed in the artifact.

## Differential diagnosis and corrected false comparator

The historical 2022 `met.dat` is tied to a **different** historical `GEO.DAT`. Comparing its meteorology to new native P3 GEO results created 493 exceedances, despite the native P6 computation succeeding:
- 473 USTAR, 14 EL, 4 WSTAR, 1 U-LEV1 and 1 V-LEV1.
- [Actions #39027746664](https://github.com/RRain001/CTEAS-next/actions/runs/39027746664) same native P6 computational binary/P4/P5, altering only GEO: fresh GEO vs historical original MET **493/FAIL**, frozen historical GEO vs historical original MET **0/PASS**.
- The decisive test is the newly **freshly rerun original CALMET on exactly the new GEO** from Actions #39028984274, which established **0/PASS** under the same unchanged criteria. Old GEO reference mismatch must not be reported as a P6 physics regression.

Initial staging issue in [Actions #39027241804](https://github.com/RRain001/CTEAS-next/actions/runs/39027241804) was missing surface/upper-air `stations.csv`, now required by SHA-checked native handoff; [contract tests #39027848002](https://github.com/RRain001/CTEAS-next/actions/runs/39027848002) PASS. Original same-source run [#39028499707](https://github.com/RRain001/CTEAS-next/actions/runs/39028499707) compiled and executed the original with exit 0 but had a **Bash output guard** defect (`! -s` outside `test`), fixed in the one-shot workflow only for successful #39028984274; no physics or comparator thresholds changed.

## Accurate status and what is *not* certified

**`S2_2C_NATIVE_P3_GEO_PLUS_FROZEN_P4_P5_TO_P6=PASS_SCOPED_HEFEI_2022_143H_SAME_SOURCE`.**

Not yet accepted: fresh re-execution of full upstream P4/P5 original-data preparation and numerical writers in a single canonical `case.yaml` runner; production-grade signed/independent output provenance (manifest labels are self-declared until cross-bound to producer logs); arbitrary CALMET options and dimensions; rain/`NPSTA>0`; generic G5; S2-2D **native-only** full P7 concentration production CLI. `P1_P7_FULL_NATIVE=NOT_READY`. Do not reuse this scoped 143h pass to mark all CALMET or CALPUFF physics accepted.

PR #27 remains Draft until review and remaining scope/evidence dispositions are completed.
