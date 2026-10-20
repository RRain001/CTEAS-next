# Issue #40 S4/P6-A — actual CALMET selected-physics portability and fixed-scope audit

2026-10-20. Prerequisite: [S3 Issue #42](https://github.com/RRain001/CTEAS-next/issues/42) **CLOSED / PASS_SCOPED** after true Huoshan `GEO.DAT+UP.DAT+SURF.DAT`, original selected P3 numeric parity, same-B0 joint SHA and actual native G19 file-backed reader on two NOAA-supported six-hour 2022 windows. [Report](https://github.com/RRain001/CTEAS-next/blob/main/docs/science_acceptance/ISSUE42_S3_TRUE_NEW_SITE_P1_P5_FINAL_SCOPED_20261020.md); [actual S3 Actions #39410645549](https://github.com/RRain001/CTEAS-next/actions/runs/39410645549). This PR implements **P6-A source audit and automated drift evidence only**, neither a first-hour native wind field nor independently accepted original CALMET numerical output.

## Root cause: case-independent SOURCE INPUT is not case-independent WIND PHYSICS

The actual source makes **four distinct claims** requiring separate acceptance:

1. **G19 actual input reader and G14 clock admission** supports `NSSTA>=1`, `NUSTA>=1` under the original selected 9-layer and ≤400×400 supported input scope. Actual Huoshan single virtual upper + single virtual surface passes this. No 3D meteorology is computed.
2. **G20 source-backed first-hour WIND1 TEST PROBE** is still explicitly restricted to **2–6 surface + 2–6 upper stations**; the file-backed station profile code then **requires exactly 2 surface/2 upper and upper IDs 58424/58425** for its synthetic G32E PREPDI missing-k1 policy. It reuses actual source physical routines for limited 2SS+2US wind profiles, but its present physics **cannot** be called on the real one-US/one-SS Huoshan input. Removing a min-count CLI guard alone does not fix source profile selection, physical missing layers, or provide an original Fortran proof.
3. **P6D selected realcase wind executor**, `src/realcase_wind_field_main.cpp`, explicitly rejects any grid other than **50×50×9 @100m**; assumes arrays of 2500 and 22500 values, while current S3 Huoshan is **100×100×9 @100m**. At least many array indexes, cumulative true physics state, source UTM station cells, and station composition need modification. Simply padding/cropping to 50×50 would destroy S3 real source identity.
4. **Native hourly driver / launcher** still picks frozen `up_58424.dat`, bridge station `58424`, CGAMMA `--upper-i 25 --upper-j 26`, **143h** and fixed **45×2500 float32 per hour**. The old original `met.dat` SHA is an explicit frozen regression reference option, and `native_cpp/orchestration/run_p6.py` refuses any new site different from `CASE_ID`. The original Hefei comparison script `scripts/run_p6_end_to_end.py` explicitly requires frozen 50×50 and reference original MET.DAT; that comparator should **remain frozen**, and a new case-specific original CALMET comparator must be independent.

**Additional stop:** `p6g_g26_file_backed_g14_diagno_bridge.hpp::run` reports `NativeHourSource::Unknown,false` rather than committing G14 production, and `run_selected` is an explicitly test-only composite. G20 WIND1 profile creation is upstream of it. A successful source parser / test probe MUST NOT be reported as P6D/P6E or native 45-field wind production.

## Reproducible machine-reviewed evidence

Run `python3 -m scripts.s4.p6a_hardcode_source_inventory --repo . --out /tmp/new-p6a-evidence.json` from the repository root with a fresh, nonexistent output path. The script reads eight **actual production/adapter** source files, records SHA256 of their full exact bytes and SHA256 and line number of **20 uniquely matched production-source code anchors**, marks who owns each frozen/supported branch, and specifies its only legitimate next gate. It rejects missing/changed anchors instead of silently labeling a newly refactored physics kernel accepted. This is a **source audit**; no synthetic or NOAA wind is computed by it.

`.github/workflows/issue40-s4-p6a-source-audit.yml` runs this scan on the exact PR SHA without compiling unrelated expensive 143h science; includes a negative drift experiment in disposable source *copies* (alters the G20 2SS/2US guard only in scratch) and requires the audit to reject changed code. Uploads only bounded source SHA metadata. No repository production source or scientific parameters are changed.

## Engineering sequence / separate acceptance PRs

| Phase | Specific next action | Independent exit |
|---|---|---|
| **P6-B0 source handoff** | Reuse exact authentic S3 June 01→07 UTC `100×100@100m`, `GEO/UP/SURF`, native G19 and original station identities. Check 00/12 brackets and SHA. | `PASS_SOURCE_INPUT` only, no wind |
| **P6-B1 first-hour WIND1** | Extend the existing 2SS/2US G20 **selected** source profile physics to real original 1SS/1US case. Handle exact original PREPDI missing 1st upper layer and IEXTRP instead of copying 58424/58425 synthetic policy. | Original CALMET/Fortran actual first-hour WIND1 original-vs-C++ compare, or fail closed |
| **P6-B2 P6D selected DIAGNO** | Parameterize the **real producer** cell arrays, terrain/CGAMMA, station projection and observation geometry; port only supported existing physical option sequence without changing numerical formula. | Genuine nonzero `100×100×9` selected U/V/W and original source stage-by-stage comparator; not yet complete MET |
| **P6-B3 causal P6E and P6F** | Replace frozen station/hour/path/original MET assumptions in native G14/COMP/P6F production. Derive 1h→6h original `met.inp` and exact B0, preserve all 45 fields and state, forbid original MET backfill. | Native `MET.DAT` original-format true newsite (scientific acceptance separately gated) |
| **P6-C science** | Independently run **original Fortran CALMET** using the **same real P1–P5 files and physical controls**. Compare full selected 45 fields/hour for 1h, 6h, then source-supported longer windows; report source SHA, tolerances and actual result. | `P6_NEW_SITE_SCIENCE=PASS_SCOPED` only when actual independent numbers pass |
| **P6-D regressions** | Preserve accepted **Hefei 143h**, deny unsupported wet deposition, options and resource budgets, prove deterministic outputs. | Issue #40 can close only after the original numeric acceptance |

### Explicit caution about observing a long input window

S3 genuinely produced one Huoshan June **24h** five-file stack but **native G19 rejected its upper 00/12 bracket availability** on actual NOAA data. Consequently, the first supported genuine non-Hefei production target should be **2022-06-01 01:00→07:00 UTC** and its independently accepted 02:00→08:00 peer; 24h P6 physics is not an accepted reproduction fixture. Do not fabricate or interpolate a missing original sounding just to grow the numerical window.

## Verdict and exclusions

`P6_A_SOURCE_HARDCODE_INVENTORY=PASS_SCOPED` only **after** actual audit workflow log and source SHA artifact pass. `P6B0_REAL_G19_SOURCE=UPSTREAM_S3_PASS`; `P6B1_TRUE_NEW_SITE_WIND1=NOT_RUN`; `P6_NEW_SITE_45_FIELD_SCIENCE=NOT_ACCEPTED`.

Only existing selected physics options may be ported. No P1–P5 re-implementation, no new P2 mapping, no original all-physics CALMET blanket claim, no P7 numerical science, wet deposition, S5 memory/scale, Docker or silently shortened/fabricated observation data. Full 143h scientific test remains an explicit separate expensive gate; this 10-minute source-audit CI must never trigger it.
