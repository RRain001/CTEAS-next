# P6D9A DIAGNO bridge — scoped scientific contract

Date: 2026-10-11. Unchanged reference is CALMET 6.5.0 L150223, original vendor Git blob `437f43bb7f0e51a1919e56664663e1a046986ed0`.

## Implemented

This is the first **single-call C++ bridge** of the selected 50×50×9 diagnostic wind sequence:

1. `WIND1` selected 1-land + 1-upper, neutral `SIMILT`, original `IEXTRP=-4` source-scoped first-guess field (verified separately at [CI #38125704104](https://github.com/RRain001/CTEAS/actions/runs/38125704104), 270,000 original U/V values PASS).
2. Explicit upstream corrected-field injection or **synthetic identity for original-source testing only**. In real simulations `DiagnoD9UpstreamMode::Missing` fails closed; setting the identity mode does **not** mean terrain/heat/slope physics were solved.
3. Original `WINDBC` boundary extraction **from the post-terrain/slope corrected first guess** (the position where original `DIAGNO` refreshes wind boundaries, L5748). It is not extracted from the final INTER2 blend.
4. Independent `INTER2` for U and V at original DIAGNO lines L6055–6061, with caller-supplied measured winds, original radii, valid masks and WO observation weights, preserving component independence.
5. Original `SMOOTH` → `DIVCEL` → `W` at L6119–6148 via preverified `original_smooth_divcel_w`, without imposing unsourced velocity corrections.
6. Original `IOBR=1` tail: literal O'Brien (1970) vertical-velocity adjustment L6153–L6159 with original `CELLZB(K)=ZFACE(K)` (L5151/L5157), then literal `IF (IOBR .EQ. 1) CALL MINIM(U,V,W,UB,VB,DIV,NITER,DIVLIM)` L6180 against the unchanged original `MINIM` (L9645–L9761). Enabled only through the explicit `obrien_adjustment` flag plus `cellzb_origin_m`/`minim_iterations`/`minim_divergence_limit_per_s`; the L6160–L6179 print-only interval is asserted to contain no computation. `MINIM` holds `W` fixed and relaxes `U`/`V` per level with original `DIVCEL`+`WINDBC` refresh. **The frozen Hefei reference control has `IKINE=0`/`IOBR=0`, so this closes a previously fail-closed original branch and does not alter the selected real-case `IOBR=0` route.**
7. Original `IFRADJ=1` upstream stage: literal `CALL FRADJ(UG,VG,HTOPO,GAMMA,ISURFT,TINF,TEMP2D,CRITFN,CELLZB,HMAX)` L5643–L5644 (unchanged subroutine L7289–L7451) applied to the step-one winds **before** the L5748 `WINDBC` snapshot and the L6055/L6059 `INTER2` calls, exactly as `DIAGNO` does. Enabled only through `froude_adjustment` plus caller-supplied `terrain_m`/`maximum_terrain_m`/`lapse_rate_k_per_m`/`surface_temperature_k` (2500 each), `isurft`, `tinf_k`, `critfn`. This *removes* one stage from the previously "must be supplied externally" set for the `IFRADJ=1` reference control; `SyntheticIdentityForSourceAudit` stays fail-closed and an external corrected field can never be Froude-adjusted twice.
8. Original `ISLOPE=1` upstream stage: literal `if (ISLOPE.EQ.1)CALL SLOPE(USLOPE,VSLOPE,HTOPO,ISURFT,TINF,TEMP2D,HMAX)` L5722–L5723 (unchanged subroutine L30372–L30604) plus the literal `UG(I,J,K)=UG(I,J,K)+USLOPE(I,J,K)`/`VG(...)=VG(...)+VSLOPE(I,J,K)` additive loop L5727–L5732, executed **after** `FRADJ` and before the L5748 boundary snapshot. Enabled only through `slope_flow` plus caller-supplied `minimum_terrain_m`/`distance_to_max_terrain_m`/`distance_to_min_terrain_m`/`sensible_heat_w_m2` (2500 each), the GEO `landuse` plane and the original `IWAT1`/`IWAT2` water class range; water cells are excluded exactly as the original does. With `froude_adjustment` also set, the bridge replays the real case deck's full `IWFCOD=1`/`IFRADJ=1`/`IKINE=0`/`ISLOPE=1`/`IOBR=0` upstream combination.

9. Original `IKINE=1` pre-blend kinematic route (completeness branch; the frozen real deck has `IKINE=0`, so `ALPHA`/`TOPOF2` never execute in the reference case): literal `CALL XMIT(-N,ZERO,W)` L5615–L5616, literal `IF (IKINE .EQ. 1) CALL TOPOF2(UG,VG,W,HTOPO, CELLZB,GAMMA,ISURFT,TINF,TEMP2D,ALPHA)` L5621–L5622 against the unchanged `TOPOF2` L31904–L32078, then the literal `IF (IKINE .EQ. 1) CALL MINIM(UG,VG,W,UB,VB,DIV, NITER,DIVLIM)` L5628–L5629 against the unchanged `MINIM` L9645–L9761 with the literal L5598–L5600 `WINDBC` boundary snapshot. Enabled only through `kinematic_route` plus `alpha`, `kinematic_iterations` and `kinematic_divergence_limit_per_s`; the TOPOF2 face field is exposed for direct comparison and is held fixed by MINIM, as in the original.

10. Original **TERSET terrain envelope in-chain** (real-case path: `i3dctw=iwfcod` at L5082 and the deck sets `IWFCOD=1`, so `if(i3dctw.eq.1)call terset(htopo,hmax,terrad)` at DIAGI L5228 executes): literal call L5228 against the unchanged `TERSET` L31805–L31903, building `HMAX`/`HMIN`/`DISTHMAX`/`DISTHMIN` from the caller's terrain and `TERRAD` inside the bridge. Enabled only through `terset_envelope` plus `terrad_km`; the four planes may be supplied by the caller **or** computed in-chain, never both, and the in-chain result is bit-identical to the caller-supplied envelope (asserted by CTest). This removes four caller-supplied planes from the real-deck `IFRADJ=1`+`ISLOPE=1` route.

## Real-case wind-field producer (partial, delivered)

`native_cpp/modules/p6_calmet/src/realcase_wind_field_main.cpp` (`cteas_p6_realcase_wind_field`) reads a CALMET case tree **read-only** (`run/met/met.inp`, `geo/**/geo.dat`, `met/surface/final/surf.dat`, `met/upperair/final/up_<id>.dat`) and writes, for the 143 case hours, chain-internal fields plus `metadata.json`:

- `wind1_u_<YYYY-MM-DD_HH>.f32`, `wind1_v_<...>.f32` — the original WIND1 step-one UG/VG grid, 50x50x9 float32, k-major/j-major/i-fastest, m/s, missing sentinel `9999.0`: neutral `SIMILT` surface profile at the 10 m anemometer, hourly upper profile from the original PREPDI path (`calmet_vertav` + `calmet_prepdi_hour` over 731 real soundings), `IEXTRP=-4`, deck `BIAS`, `ICALM=0`;
- `blend_u_<...>.f32`, `blend_v_<...>.f32` — the original two-component `INTER2` blend on that step-one grid with the case's own controls: `WO(i,j,k)=1.0` everywhere (RDWT L25035-L25045 fills 1.0 for `IPROG=0/2/4/14` and the deck supplies no `WT.DAT`), `RMIN=0.1`/`RMAX1=100`/`RMAX2=200`/`RMAX3=200`/`R1=50`/`R2=100` km, `LVARY=F`, `NINTR2=99` clamped to the two case stations, `IPROG=0`/`NBAR=0`/`NOOBS=0`, GEO landuse and water class, both stations at the declared grid centre (`case.yaml` grid.center equals `stations.csv` lat/lon, so no branch-local lat/lon projection is used);
- `temp2d_<...>.f32` (K) — the SURFVAR 2-D surface temperature: p6e `surfvar_one_station` with `iall=0` (the DIAGNO L5610 call; per L12878-L12883 it returns the same `temp_k` and drops RH/IPCODE) and `average_temperature=1` for the deck's `IAVET=1`, fed the observed station temperature/humidity and the surface-level diagnostic wind for AVETMP;
- `qh_<...>.f32` (W/m^2) — the HEATFX sensible heat flux: p6e `heatfx` with `mcloud=1` (station cloud, 0 tenths for every case hour), `sinalpc` from `p6e::sinalpc_grid` over `p6e::surface_solar_grid`, and the met.lst coefficients `ha1=990, ha2=-30, hb1=-0.75, hb2=3.4, hc1=5.31e-13, hc2=60, hc3+1=1.12`, with GEO albedo/Bowen/soil-heat/anthropogenic per cell;
- `slope_corrected_u/v_<...>.f32` (m/s) — the SLOPE stage L5722-L5723 plus the additive loop L5727-L5732 applied to the step-one winds with the chain-computed QH, TEMP2D and TERSET envelope; these feed the blend and the W tail;
- `w_face_<...>.f32` — the `DIAGNO` `SMOOTH`+`DIVCEL`+`W` tail (L6119-L6148) on the SLOPE-corrected blended field with the deck `NSMTH` and boundaries taken from that field, ten faces per column, m/s; the L5748 snapshot after the FRADJ/SLOPE corrections is not available yet (TEMP2D/QH), so the emitted W faces are SLOPE-compensated but not FRADJ-compensated and the metadata records `FRADJ: PENDING_GAMMA`;
- `terset_hmax.f32`, `terset_hmin.f32`, `terset_disthmax.f32`, `terset_disthmin.f32` — the in-chain original TERSET envelope (2500 cells each, m). With the deck's `TERRAD=15 km` over a 5 km domain every cell searches the whole grid, so the envelope is the domain-wide extremum pair by construction;
- `metadata.json` — dims, layout, dtype, layer geometry from the deck `ZFACE`, per-file units, sentinel, hour-label convention, surface wind speed range, the list of **stages applied in-chain**, the list of **stages not applied with their exact blocking inputs**, control values read, per-input FNV-1a fingerprints, station ids and sounding count.

Verified on the frozen case (`hefei5km_2022_reference_case_20261011`): 143/143 hour labels, 719 float32 arrays (five fields x 143 hours plus four envelope planes) plus `metadata.json`, 22,500 values per 3-D array and 25,000 per W face array; ranges u in [-0.71, 2.98] m/s (step one) and [-1.29, 5.29] m/s (blended), v in [0.88, 4.25] m/s (step one) and [0.07, 4.50] m/s (blended), W faces in [-1.75e-03, 1.74e-03] m/s with a zero surface face, no sentinel cells, envelope relief 34.5 m, and a fail-closed CTest `p6d_realcase_wind_producer_case_contract` that runs the producer on the case and requires the 143-hour banner (29/29 scoped CTests). `metadata.json` states this is a **partial** product: the DIAGNO stages after the first guess are not applied, so consumers must treat the arrays as the step-one field the original `DIAGNO` starts from.
### Real-case gate steps (requested)

The two real-case verdicts are not yet inside `scripts/local_gate.py`'s `p6d` step list, which currently stops at the synthetic chained parity. To make the product's evidence part of the authoritative gate, add these two steps after it (both need only the module build, the vendor tree and the frozen case):

1. `{build}/cteas_p6_realcase_wind_field --case project/cases/hefei5km_2022_reference_case_20261011 --out {out}/p6d-realcase --fixtures {out}/p6d-realcase-fixtures` (requires the case tree)
2. `python3 native_cpp/modules/p6_calmet/reference/compare_original_d9a_realcase_step_one.py --vendor engine/vendor/src/CALMET_v6.5.0_L150223 --fields {out}/p6d-realcase --fixtures {out}/p6d-realcase-fixtures --out {out}/p6d-realcase-parity` (step-one verdict) and the same with `reference/compare_original_d9a_realcase_blend.py` (blend verdict)

Both comparators compile the unchanged original routines with gfortran and are fail-closed, so they belong in the gate rather than only in local evidence.

### Round 17: the EL table closes the level-2 term; level 1 is an observation-assembly residual

**Bisection.** `U-LEV 2`'s 0.0279876 comes from two consecutive hours (2022-01-02_18/19, my indexes 41/42) and is confined to **level 2** (levels 1 and 3-9 exact at those hours). Reading the station columns out of the INTER2 fixture at that hour shows the reference's level-2 value (`-0.2188`) is neither my surface column (`-0.4856`) nor my upper column (`-0.0076`), so a *station-column input* differs, and the culprit is the Monin-Obukhov length: **the original's `EL` at hours 42/43 is 120.4009 while the P6E E29 `EL` export reads 43.3443** (they agree at every other hour sampled). The same check across all 143 hours finds 8 hours where the two differ by more than 1e-3: 9, 14, 18, 24, 42, 43, 81, 138 (largest at 18: 67.73 vs 43.34; at 42/43: 120.40 vs 43.34).

**Fix.** The producer now takes `--el-cell <file>` (143 float32, built from DGM's `dgm_cell.json`) and prefers it over the E29 `EL`, exactly like `--zii-cell`. Measured at hour 2022-01-02_18: level 2 `dU` 0.027817 -> **0.000007**, `dV` 0.000918 -> **0.000007**. End-to-end: `U-LEV 2` 0.0279876 -> **0.00172555** (exceedances 64,283 -> 57,009) and `V-LEV 2` 0.0128908 -> **0.00177884** (51,814 -> 44,263); levels 3-9 and every `WFACE` are unchanged, since they were already limited by the other terms.

**Level 1 remains, and it cannot be a profile problem**: level 1 is the observed surface wind (the case's anemometer is at 10 m = `ZMID(1)`), so no SIMILT is involved and the EL/ZII tables cannot move it. Its worst hours are 2022-01-03_00/01 and 2022-01-01_18/19 plus 2022-01-02_18/19 (0.000956..0.001567 m/s; 1,450 cells above tolerance), and at the station cell the values agree to ~1.2e-04 while the worst *cell* differs by 1.567e-03 - i.e. the two level-1 fields have *different spatial patterns*, not different station values. **Instrumentation request** (DGM format): for hours 17, 18, 41, 42, 47, 48 (UTC labels 2022-01-01_18/19, 2022-01-02_18/19, 2022-01-03_00/01), dump (a) the surface station's column as it enters the analysis, `US(1,1)/VS(1,1)` after DIAGI's anemometer-to-`ZMID(1)` adjustment, (b) the upper-air `UDAT/VDAT` after `RDUPN` (all nine levels), and (c) the `UG/VG` at the existing kpt 8 - that isolates whether the level-1 pattern difference comes from the surface observation assembly, the UA low-level interpolation, or the analysis weights.

### Round 16: DGM's two answers, and the two fixes they enable

**Fix 1 - the ZI cutoff flip (closes `U-LEV 6`).** DGM's instrumented original run shows that the value SIMILT receives is *not* the grid `ZI`: `ELUSTR2` overwrites its local `zii` through `MIXHTST`/`MIXHT2ST` (L6882-L6887) before the call at L6894, and the processed layer count differs in **50 of the 143 hours** (hour 82: grid `ZI` 659.966 m vs `zii` 153.341 m; the largest divergence at nh 10: 1009.95 m vs `ZII = ZIMIN = 50 m`). The producer now takes `--zii-cell <file>` (143 float32, built from `dgm_p6d_requests_2022/dgm_cell.json`) and uses it for the cutoff, falling back to the grid `ZI` only when absent. Measured at hour 80: level 6 `dU` 1.8280 -> **0.00006**, `dV` 0.3244 -> **0.00001**.

**Fix 2 - the real station coordinates (closes the tilt, and with it every W face).** DGM showed the tilt is already present in `UG` before the SLOPE addition, and that `USLOPE/VSLOPE` are identically zero at levels 2-9 on this domain - so the tilt comes from the initial-guess/analysis line, not from SLOPE. The producer previously forced both stations to the declared grid centre; the station tables actually place them ~3 m apart (surface `583210` at 31.939774444/117.141610855, upper `58424` at 31.9398/117.1416), which makes the inverse-square weights differ slightly across the domain. The producer now projects both stations from their own tables (branch-local equirectangular projection, documented in the source) and feeds those positions to WIND1, INTER2 and both comparator fixtures. Measured: `U-LEV 3`'s spatial spread 0.000166 -> **0.010014** against the reference's 0.010594.

**End-to-end AUX (worst over 143 hours, 357,500 cells/level, tolerance `1e-4+1e-5*|ref|`)**:

| field | round 15 | round 16 |
|---|---|---|
| `U-LEV 2` | 0.0315449 | **0.0279876** |
| `V-LEV 2` | 0.0325136 | **0.0128908** |
| `U-LEV 3` | 0.0330477 | **0.00180769** |
| `V-LEV 3` | 0.0362592 | **0.0019834** |
| `U-LEV 4` | 0.0419641 | **0.00229454** |
| `V-LEV 4` | 0.0397687 | **0.00217557** |
| `U-LEV 5` | 0.0491858 | **0.00269222** |
| `V-LEV 5` | 0.0400119 | **0.00219202** |
| `U-LEV 6` | 1.8483 | **0.00229311** |
| `V-LEV 6` | 0.327975 | **0.00248528** |
| `U-LEV 7` | 1.82837e-05 PASS | **1.43051e-06 PASS** |
| `V-LEV 7` | 1.21593e-05 PASS | **1.90735e-06 PASS** |
| `U-LEV 8` | 2.90871e-05 PASS | **2.86102e-06 PASS** |
| `V-LEV 8` | 2.09808e-05 PASS | **1.90735e-06 PASS** |
| `U-LEV 9` | 4.00543e-05 PASS | **4.76837e-06 PASS** |
| `V-LEV 9` | 2.09808e-05 PASS | **1.90735e-06 PASS** |
| `WFACE 1` | 0.000265361 | 0.000265361 (36 exceedances) |
| `WFACE 2` | 0.00381483 | **0.000265025** |
| `WFACE 3` | 0.0122024 | **0.000717808** |
| `WFACE 4` | 0.0301354 | **0.00180031** |
| `WFACE 5` | 0.0850985 | **0.0039018** |
| `WFACE 6..9` | 0.158155..0.158162 | **0.00851096..0.00851186** |

The W faces improved 18-180x in max-abs and 5-70x in exceedance count (e.g. `WFACE 9`: 178k -> 24.6k cells); the remaining WFACE tail is the level-1 wind residual and the level-2 profile term. Still open: `U-LEV 1`/`V-LEV 1` at 0.00156724/0.00132203 (1,450/905 cells) and `U-LEV 2` at 0.0279876 (64,283 cells).

### Round 15: the `U-LEV 6` value is a ZI cutoff flip at one level, and the tilt correlates with the terrain envelope

**Correction first**: round 14's per-level table for the worst hour was built with a truncated hour label, so its *product* column came from hour 01 while its *reference* column came from the worst hour. The corrected table (hour `2022-01-04_09`, index 80) is:

| level | ref U | product U | dU | ref V | product V | dV |
|---|---|---|---|---|---|---|
| 1 | -2.9353 | -2.9353 | 0.0000 | -1.9062 | -1.9062 | 0.0000 |
| 2 | -3.4454 | -3.4453 | 0.0002 | -2.5208 | -2.5209 | 0.0001 |
| 3 | -3.8299 | -3.8296 | 0.0003 | -2.8545 | -2.8546 | 0.0001 |
| 4 | -4.2716 | -4.2713 | 0.0004 | -3.3408 | -3.3412 | 0.0003 |
| 5 | -4.5966 | -4.5961 | 0.0005 | -3.3379 | -3.3383 | 0.0004 |
| 6 | -4.7156 | -2.8876 | **1.8280** | -2.3417 | -2.6661 | **0.3244** |
| 7 | -0.7605 | -0.7605 | 0.0000 | 2.2326 | 2.2326 | 0.0000 |
| 8 | 7.1751 | 7.1751 | 0.0000 | 8.9067 | 8.9067 | 0.0000 |
| 9 | 14.1135 | 14.1135 | 0.0000 | 8.6280 | 8.6280 | 0.0000 |

So the whole 1.8483 comes from **level 6 at one hour**; the neighbouring hour (index 79) is clean at level 6 (0.0011). The cause is a **cutoff flip**: SIMILT's `zface(k) <= amax1(zi+0.001, zimini)` test decides whether level 6 receives the surface profile or stays missing. At that hour the E29 `ZI` at the station cell is **631.14 m** against `zface(7) = 640 m`, so the port stops one level earlier than the reference, which keeps `-4.7156` (the surface profile) where the port falls back to the sounding (`-2.8876`). The original does not use the raw `ZI` field here: `DIAGI` passes `zii = zi(is,js)` through **`mixhtST`/`mixht2ST`** (L6882-L6887), which update `zii` in place, and only then calls `similt` (L6894). **Instrumentation request**: the value of `zii` as passed to `similt` at L6894 (i.e. after `mixhtST`), per hour, at the station cell `is,js`, together with that routine's inputs (`el, ustar, qqh, rho, ihr2gmt, nearu, iupt, ilandu, iwat1, iwat2, imixh` and the incoming `zii/ziconvi`). With that array the flip is closed without guessing.

**The planar tilt's source: correlations, not yet identified.** For hour 1, `U-LEV 3`'s deviation from its own mean (spread 0.0106; plane fit `dU/di = -1.30e-05`, `dU/dj = +3.78e-05` per cell) correlates with:

| candidate field | correlation |
|---|---|
| `terset_disthmin` (distance to the terrain minimum) | **+0.487** |
| `terset_disthmax` (distance to the terrain maximum) | **-0.394** |
| my `temp2d` | -0.100 |
| my SLOPE correction (level 1) | +0.038 |
| the reference's own `WFACE 3` | -0.001 |

The two terrain-envelope distances are the only fields with a meaningful correlation, which points at a terrain-envelope-driven term of the same family `SLOPE` uses (`hd = 0.05*(HMAX-HTOPO)`, `dcrest` from `disthmax/disthmin`) - but the port's SLOPE cannot be it: on this domain `HMAX` is a uniform 59.5 m, so `hd <= 1.7 m` and the original's own ramp (L30568-L30579) confines that correction to level 1 (measured 0.0413027 there, 0.0 at levels 2-9). **Instrumentation request**: at one hour, `USLOPE/VSLOPE` (the 3-D arrays after the `SLOPE` call at L5722), `UG/VG` immediately before (L5726) and after (L5732) the addition, and the `DIV`/`W` arrays after `DIVCEL` (L6130-L6140) - that isolates which step introduces the tilt and whether the original's slope flow is non-zero above level 1 on this domain.

### Round 14: the `U-LEV 6` episode is an input-side hour, and the W-face structure is *planar* (mechanism still open)

**`U-LEV 6` bisection.** The 1.8483 worst value comes from a single hour on 2022-01-04; at that hour the frozen reference reads `-2.9353 / -3.4454 / -3.8299 / -4.2716 / -4.5966 / -4.7156` (levels 1-6) while the product reads `-1.8955 / -2.1980 / -0.9298 / -0.9764 / -0.8980 / -0.7030`. The decisive detail is **level 1: 1.03982 m/s** - level 1 is the observed surface wind (the case's anemometer is at 10 m, exactly `ZMID(1)`, so no extrapolation is involved) - so the divergence for that episode starts in the *input/assembly* of that hour's station data, not in the profile physics. The next check is bounded: compare the case's surface series around that hour against the interval the product selects.

**The W-face structure is a planar gradient, and three candidate mechanisms are now ruled out by measurement.** The reference's `U-LEV 3` deviation from its own mean is a smooth NW->SE tilt (-1.7e-3 at the NW to +2.8e-3 at the SE, spread 0.0106), *not* a radial, station-centred pattern; the product's own deviation is 1.66e-4 (uniform) and correlates 0.009 with it. Ruled out:

- **station-position offset**: the two station files place their stations 2.6e-5 deg apart in latitude (~3 m). The inverse-square weights differ by ~0.24% across the domain, and the two stations' level-3 values agree to ~1e-3 m/s, so the mechanism can produce ~2e-06 m/s - two orders below the observed 1e-2.
- **SLOPE's vertical structure**: the original fills `USLOPE(I,J,K)` for all `K` (L5726-5732) but ramps it to zero at the depth `hd = 0.05*(HMAX-HTOPO)` (L30568-30579). On this domain the relief gives `hd <= 1.7 m` against `ZFACE(2) = 20 m`, so the correction is confined to level 1 with a ratio of ~0.085 - which is exactly what the port does (measured: 0.0413027 at level 1, 0.0 at levels 2-9). So the level-1-only behaviour is *correct* here, not a gap.
- **`STHEOR`'s 2-D dependence** (the round's premise): `DIAGI` calls `STHEOR`/`SIMILT` inside `DO 70 L=1,NSURF` (L6876-6894) with the *station's* cell `IG,JG`, i.e. **once per station**, so the temperature dependence cannot produce a spatial gradient; and the reference's pattern is planar (domain-scale), not station-centred. The premise is therefore not supported by the source, and no port was attempted on it - a large speculative change contradicted by the measurements would be worse than the open gap.

Open, with the bounded next steps: (a) the level-1 input check for the 2022-01-04 episode; (b) correlate the reference's planar deviation against the terrain/landuse and the divergence fields to find which step introduces it (the W faces are its divergence integral, so both fall together); (c) if needed, dump intermediate fields from a full original run, which is outside this track's scope.

### Round 13: the stability-dependent SIMILT (PSIUD) port closes levels 2-5 and level 7

Ported source-scoped, with the vendor lines and hashes recorded by the comparator: `SIMILT` L30097-L30370 (`sha256` of the extracted block in `p6d-similt-profile-parity.json`) and `PSIUD` L35629-L35674. The kernel now covers the neutral, stable and unstable branches, the Monin-Obukhov clamp at `5*z0`, the Table-2 turning-angle interpolation, the mixing-height cutoff (`zface(k) <= amax1(zi+0.001, zimini)`, "above mixing height, exit") and both hemispheres; `IPSIFCN=1` (PSIUC/COARE) and overwater stations fail closed. The original's write pattern is `US(K-1,NS)` for `K=2..NZP1`, i.e. level 1 receives the profile at `ZMID(1)` - reproducing that exactly was what made the `tall_anemometer` scene agree.

Two inputs drive it, both from the P6E E29 export and both labelled uncertified: `--el` (`<prefix>.el.f32`, the Monin-Obukhov length; hour 1 = -49.5 m) and `--zi` (`<prefix>.zi.f32`, the cutoff; hour 1 = 231 m, floored at the deck's `ZIMIN = 50 m`). `ZI` is the right cutoff input because DIAGI passes `zii=zi(is,js)` (L6876/L6894); `ZICONV` is only the convective height and is zero for 89 of the 143 hours.

Evidence (`compare_original_similt_profile.py`, 15 scenes, 162 components, compiled original + PSIUD, tolerance 2e-4 m/s): **`PASS_SIMILT_PROFILE_ORIGINAL`, max abs error 1.907e-06 m/s, zero mismatches** - covering the neutral WIND1 route, unstable/stable profiles, both clamps, the cutoff at the second face and at the minimum only, and both hemispheres.

End-to-end effect (AUX, product through P6F vs the frozen `met.dat`, worst over 143 hours):

| field | round 12 | round 13 |
|---|---|---|
| `U-LEV 2` | 2.47476 | **0.0315449** |
| `V-LEV 2` | 2.6212 | **0.0325136** |
| `U-LEV 3` | 3.22231 | **0.0330477** |
| `V-LEV 3` | 2.87008 | **0.0362592** |
| `U-LEV 4` | 4.12656 | **0.0419641** |
| `V-LEV 4` | 2.7318 | **0.0397687** |
| `U-LEV 5` | 4.8366 | **0.0491858** |
| `V-LEV 5` | 3.93422 | **0.0400119** |
| `U-LEV 6` | 2.71215 | 1.8483 |
| `V-LEV 6` | 3.03253 | 0.327975 |
| `U-LEV 7` | 2.54216 | **1.82837e-05 PASS** |
| `V-LEV 7` | 3.90401 | **1.21593e-05 PASS** |
| `U-LEV 8/9`, `V-LEV 8/9` | PASS | PASS |
| `WFACE 1..9` | FAIL | FAIL (0.158 plateau unchanged) |

At hour 1 every level now sits within ~2.1e-04 m/s of the reference (level 2: 0.037302 -> 0.000205, level 4: 0.088716 -> 0.000215). Remaining: level 1 (0.00156724, the station-centred structure term), level 6 (1.8483, one deep-mixing episode), and every `WFACE`, which the round-12 analysis showed is the divergence integration of the same missing structure - the stability-dependent profile did not remove it, so the structure must come from the 2-D `temp2d`/flux dependence that `STHEOR` adds on top of `SIMILT`, not from the profile shape alone. The `A-B` deltas (`USTAR` 5.7228e-05, `EL`, `WSTAR`) are unchanged because they follow the level-1 wind and the P6E chain state, both untouched this round.

### Round 12: the AUX per-level table, and one root cause behind the low levels and every W face

Full AUX verdicts (product through P6F written into `CALMET.DAT 2.1` vs the frozen `met.dat`, 357,500 cells per level, tolerance `1e-4 + 1e-5*|ref|`), from `p6g_report.json` of the run recorded in round 11:

| field | max_abs | max_rel | exceedances | verdict |
|---|---|---|---|---|
| `U-LEV 1` | 0.00156724 | 264.542 | 1,451 | FAIL |
| `V-LEV 1` | 0.00132227 | 15,650.6 | 906 | FAIL |
| `WFACE 1` | 0.000265355 | 1,491.51 | 36 | FAIL |
| `U-LEV 2` | 2.47476 | 65.9057 | 357,306 | FAIL |
| `V-LEV 2` | 2.6212 | 27.2546 | 357,115 | FAIL |
| `WFACE 2` | 0.00381483 | 1.22e+08 | 25,235 | FAIL |
| `U-LEV 3` | 3.22231 | 12.5257 | 239,982 | FAIL |
| `V-LEV 3` | 2.87008 | 1.54638 | 239,814 | FAIL |
| `WFACE 3` | 0.0122024 | 3.46e+07 | 75,687 | FAIL |
| `U-LEV 4` | 4.12656 | 0.993557 | 182,498 | FAIL |
| `V-LEV 4` | 2.7318 | 2.29782 | 182,433 | FAIL |
| `WFACE 4` | 0.0301357 | 2.45e+07 | 138,685 | FAIL |
| `U-LEV 5` | 4.8366 | 2.41797 | 130,000 | FAIL |
| `V-LEV 5` | 3.93422 | 11.4096 | 130,000 | FAIL |
| `WFACE 5` | 0.0850979 | 5.63e+07 | 167,611 | FAIL |
| `U-LEV 6` | 2.71215 | 1.36005 | 102,499 | FAIL |
| `V-LEV 6` | 3.03253 | 11.9904 | 102,478 | FAIL |
| `WFACE 6` | 0.158154 | 2.00e+07 | 179,295 | FAIL |
| `U-LEV 7` | 2.54216 | 3.20113 | 37,500 | FAIL |
| `V-LEV 7` | 3.90401 | 1.6656 | 37,500 | FAIL |
| `WFACE 7` | 0.158155 | 2.91e+07 | 180,199 | FAIL |
| `U-LEV 8` | **2.90871e-05** | 4.92287 | 0 | PASS |
| `V-LEV 8` | **2.09808e-05** | 0.000148759 | 0 | PASS |
| `WFACE 8` | 0.158156 | 6,271.09 | 180,266 | FAIL |
| `U-LEV 9` | **4.00543e-05** | 9.36849e-05 | 0 | PASS |
| `V-LEV 9` | **2.09808e-05** | 8.42658e-05 | 0 | PASS |
| `WFACE 9` | 0.15816 | 35,640.2 | 180,318 | FAIL |

The first significant divergence is at level 1 for U/V (0.0016 m/s, 1,451 cells) and at level 2 for W (25,235 cells); the large terms start at level 2 and peak at level 5.

**The W faces are downstream, not a `FRADJ`/order problem.** Measured on the frozen reference itself: its `WFACE` follows its own `U/V` horizontal divergence with the original's `W(K+1) = W(K) - (DZ/2)*HTOP*(dU/dx+dV/dy)` factor - the ratio of `DZ*|div_h|` to `|dW|` is 0.46-0.61 at levels 2, 3, 5, 6, 7 (levels 1/4/8/9 are distorted by the crude one-sided edge differencing used in the check). My product's `U/V` are **exactly uniform per level** (spread 0 against the reference's `1.1e-4` at level 1, `1.0e-2` at level 2, `1.1e-2` at level 3, `1.2e-2` at level 5, `2-5e-3` aloft), so its W is legitimately ~0 (`max 1e-5` at hour 1) where the reference reaches `0.0115`; at the worst hour the reference's `WFACE 9` peaks at **0.15023 exactly at the station's grid cell** and decays radially (0.0253 at +-5 cells, 0.0064 at +-20, 0.002 at the corners). `FRADJ` cannot be the cause: it is inert on this domain (FROUDE 5.14 against `CRITFN = 1.0`, measured 0.0 m/s effect), and the tail's order is verified against the compiled original. The W faces therefore measure the *U/V structure* that this product does not have.

**One mechanism explains both remaining terms**: the original's station profile is built by the *stability-dependent* branch (`STHEOR`, the `IEXTRP = +-4` path in `DIAGI`, which uses the 2-D `temp2d`/fluxes and the analysis radii), while the selected kernel is the *neutral* SIMILT. That is what (a) sets the levels inside the mixing height to a sheared, spatially varying profile (my neutral profile is uniform in space and, at deep-mixing hours, 2-5 m/s away from the reference at levels 2-6), and (b) is the only source of the station-centred structure the W integration needs. Both station files place their station exactly at the declared grid centre (verified: `583210` at 31.939774444/117.141610855 and `58424` at 31.9398/117.1416 against `case.yaml`'s 31.939774444/117.141610855), so the structure cannot come from station distance; it has to come from the 2-D surface fields inside `STHEOR`.

This round is therefore diagnostic: no numerical clearance was achieved, and the next increment is the `STHEOR` port (stable/unstable profile with `zmo` from the surface fluxes, `psiud`/`psiuc`, and the 2-D `temp2d`/`qh` this producer already emits).

### Product verification labels (round 11, final)

`metadata.json` now labels each stage with the verdict that belongs to it: `blend.verification` is the **closed field's** own verdict (`PARTIAL_LEVELS_8_9_PASS_LEVELS_1_7_NEUTRAL_SIMILT_GAP` with the frozen-reference numbers when `--ziconv` is given, `MIXING_HEIGHT_NOT_SUPPLIED_ALL_LEVELS_NEUTRAL_SIMILT` with the measured 13.5074/10.0186 m/s levels 9/8 errors when it is not), and the unchanged-original INTER2 verdict moved to `inter2.verification` because it describes `inter2_u/v_*.f32`. The closed-field verdict never over-claims for the uncapped variant.

Recorded directory for downstream consumption (round-16 variant: `--el` + `--zii-cell` from DGM's instrumented run + the station tables' own coordinates): `/home/lhy/build/p6d/rw23`, 1865 files, tree SHA-256 (sorted `basename || content`) `e318e20022a0eccd86b09ebdcbbf0057749c2594a0393da2a38a1481aeecb055`, `metadata.json` `6355d7b2c810f1d91add66cf9c4ae703aa99305b22a9be04f29394eae030f73f`, `blend_u_2022-01-01_01.f32` `eb4ec5307e36143fd6ff6cda1272d7141615edfcd3cf660b2d5f9d15af4b12b8`, `w_face_2022-01-01_01.f32` `880d435d093850655f0d05433cbf03ce9c9bb16ebc05062f720e552ee0eea74b`. The arrays are bit-identical to `rw20`/`rw22` (the directories the round-16 end-to-end verdicts were measured on; verified by comparing the full tree, `blend_u` and `w_face` hashes), so the AUX numbers above apply to exactly these bytes.

### The height-growing U/V error was the uncapped SIMILT surface profile (round 11)

The P6G end-to-end run showed the reconstructed wind's error growing monotonically with height (level 1 `1.518e-03` m/s -> level 9 `13.507` m/s) and attributed it to the missing `SMOOTH`/`DIVCEL`/`WINDBC`. **Measured first, that attribution is wrong**: enabling the closed field changes the product by at most `5.9e-05` m/s (level 9 of hour 1), four orders below the reported error, so the tail is not the cause.

The real chain of evidence:

1. With a single station and `WO=1.0` both the frozen reference and my product are **horizontally uniform per level**, so the comparison reduces to the per-level station profile.
2. The reference's per level equals the **upper-air sounding** interpolated at the CALMET level heights: at hour 1 my fixture's `upper_observed_profile` is `0.866781` at level 5 and `3.67967` at level 6 against the reference's `0.866` and `3.677` - exact to the reported precision.
3. My product instead carried a **neutral SIMILT profile at all nine levels** and WIND1 combines the surface and upper columns by inverse distance; with both stations at the grid centre the weights are 0.5/0.5, so the upper-air shear was halved: level 9 read `0.716` where the sounding gives `1.017` and the reference `2.464`.
4. The original's `SIMILT` fills the surface-station profile only while `zmid(k) <= zic` and then **exits above the mixing height** (`calmet.for` L30345, `c --> Above mixing height, exit / goto 2`); the levels above keep the upper-air values, and a station value that is missing simply drops out of WIND1's weighted sum.
5. The mixing height is not invented here: P6E's E29 `ZICONV` export gives **150.3 m at hour 1** (344.3 / 531.5 / 791.7 / 958.1 / 985.4 m for hours 2-6), and that boundary is exactly what the reference shows at hour 1 - level 4 (120 m) still carries the surface value `-0.567` while level 5 (240 m) already carries the sounding's `0.866`.

Implementation: `--ziconv <file>` (P6E E29 `<prefix>.ziconv.f32`, hour-major, labelled `ZICONV_SOURCE: P6E_CHAIN_INTERNAL_UNCALIBRATED` with its accuracy caveat in `metadata.json`) caps **the DIAGI-built station column that INTER2 consumes**: `DIAGI` calls `SIMILT` with `zii=amax1(zimech,ziconv)` (L6894) and `SIMILT` exits above `zic` (L30345), so the capped levels carry the INTER2 missing sentinel and the upper-air station alone feeds the blend (the kernel already drops missing station values). The **WIND1 first guess is a different call** - L36171 passes `zmo=zml=10000.` with the comment "similarity theory (assuming neutral conditions and infinite mixing length)" - so it stays uncapped and neutral, which is why `wind1_*` and its step-one verdict are unchanged. The ZICONV used for the recorded run came from the P6E chain driven by the **frozen** wind (case B), which is what keeps the reconstruction non-circular.

Measured effect at hour 1 (U, `|product - frozen reference|`):

| level | before | after |
|---|---|---|
| 2 | 0.03730 | 0.03730 |
| 3 | 0.06616 | 0.06616 |
| 4 | 0.08872 | 0.08872 |
| 5 | 0.99700 | **0.00000** |
| 6 | 2.32200 | **0.00000** |
| 7 | 3.91500 | **0.00001** |
| 8 | 3.65100 | **0.00001** |
| 9 | 1.74900 | **0.00000** |

The same round also exposed a placement trap worth recording: capping the **WIND1** surface column instead of the **DIAGI/INTER2** one is wrong and the step-one verdict catches it (the original's WIND1 SIMILT is deliberately neutral and uncapped, L36171). The cap belongs to the column `DIAGI` builds for the objective analysis.

Levels 2-4 are unchanged because they sit **inside** the mixing height, where the original uses the *stability-dependent* similarity profile (`STHEOR` with the surface fluxes and `temp2d`, the `IEXTRP = ±4` branch) while the selected WIND1 kernel is the **neutral** SIMILT. That residual (0.037-0.089 m/s at hour 1) is the next quantified gap, and it is reachable with data this producer already computes (`qh_*.f32`, `temp2d_*.f32`).

### The DIAGNO product is the closed field: SMOOTH + DIVCEL now reach U/V (round 11)

The tail (`SMOOTH` -> `DIVCEL` -> `W`, `original_smooth_divcel_w`) was already executed and self-verified against the frozen routines, but only its **W faces** were written out; the U/V the tail computes were discarded. The end-to-end run against the frozen `met.dat` therefore compared the *pre-tail* INTER2 blend and its error grew monotonically with height (level 1 `1.518e-03` m/s -> level 9 `13.507` m/s), which is exactly the signature of a missing per-layer smoothing pass (the deck smooths 2 passes on level 1 and 4 on each level above).

The product layout is now honest about the chain:

| array | stage |
|---|---|
| `wind1_u/v_*.f32` | WIND1 first guess (`IEXTRP=-4` neutral SIMILT) |
| `slope_corrected_u/v_*.f32` | after `SLOPE` (+`FRADJ` when `--gamma` is given) |
| `inter2_u/v_*.f32` | after the INTER2 two-component blend (the old `blend_*` content, still the anchor of `compare_original_d9a_realcase_blend.py`) |
| `w_face_*.f32` | after the tail's `SMOOTH`+`DIVCEL`+`W` |
| `windbc_ub/vb_*.f32` | `WINDBC` (L36404): lateral boundary values (`nz*2*ny` / `nz*2*nx`) of the field entering the tail |
| `blend_u/v_*.f32` | **the closed DIAGNO field**: INTER2 blend, then `SMOOTH`, then `DIVCEL` (the canonical slot downstream writers consume) |

`WINDBC` itself is a two-line boundary copy (L36404-L36435) and was already being performed inside the tail before `SMOOTH`; it is now emitted so the stage is auditable, and the tail's refreshed boundaries are what `DIVCEL` uses.

### FRADJ behind an explicit switch, and why it is a no-op for this domain

`FRADJ` (L5643-L5644) is now wired behind `--gamma <dir>`: when given, the producer reads a per-hour gridded `GAMMA` (`gamma_<label>.f32`, 2500 float32) and runs the unchanged Froude kernel before SLOPE, emitting `fradj_corrected_u/v_*.f32`; `metadata.json` then reports `FRADJ: APPLIED_WITH_CALLER_GAMMA` with the `gamma_source` path, and the tail note distinguishes "SLOPE+FRADJ compensated" from "the supplied GAMMA accuracy is not verified here". With the switch off it stays `PENDING_GAMMA`.

Quantified consequence for this case: **the switch is numerically a no-op, because the original FRADJ cannot fire on this domain.** HMAX is the domain-wide 59.5 m (`TERRAD=15 km` over a 5 km domain), so the largest `OBSHGT` at level 1 is `59.5 - 25 - 0 - 10 = 24.5 m` and `FROUDE = 3.0/((9.8*0.016/276.65)^0.5 * 24.5) = 5.14` against `CRITFN = 1.0` (126 m of `OBSHGT` would be required at 3 m/s); higher levels have smaller `OBSHGT`. Measured directly: enabling the switch with `GAMMA = 0.006 K/m` changes the corrected fields by **0.0 m/s**. So the pending GAMMA has no numerical effect on the delivered arrays, and the remaining dependency is one of *completeness*, not of product accuracy.

For the automatic path (no caller GAMMA), the dependency chain is now fully located: `gamma(i,j)` for `IPROG=0` is filled by PREPDI's CGAMMA (L3340-L3395); the `cgamma2` call sites (L5493, L5515) are inside the `iprog=5/15/14` prognostic branches and therefore do not run for this deck. Feeding CGAMMA needs a `CompBufferedHour` (bounded by the soundings, which this producer already has via `calmet_prepdi_2022_hours`) plus the E29 `ZICONV` array; P6E marks that array *interface ready, accuracy pending* (`ZI` 62% mismatch vs the frozen reference).

### IEXTRP = -4 / RMIN2 = -1.0 real-path semantics

The deck sets `IEXTRP = -4` (met.inp L528) and `RMIN2 = -1.0` (L559), and both were previously unmodelled on the C++ side.

- `IEXTRP <= 0` means *"do not use level 1 data from UA winds"* (calmet.for L5778) and is implemented in PREPDI as `IF (IEXTRP .LE. 0) I1=2` (L14099 in the buffered-sounding branch, L14005 in the direct branch), i.e. the upper station's lowest level is left at the original missing value. `reference/probe_original_prepdi_iextrp_level1.py` extracts the literal block L14099-L14107 (sha256 `9dba46c137d7635bc53113a70d2b91c110bc897a5a43f563be43bc787d41d8e5`, exclusion line sha256 `5d69804ebe7f8dee7bd49e09c3c984ce9b6f7d080cd2b0ab3bf882dfa37e09a9`), compiles it unchanged and asserts: with `IEXTRP=-4` level 1 stays `999999.` while level 2 is filled, and with `IEXTRP=+4` level 1 is filled -> `PASS_PREPDI_IEXTRP_LEVEL1_EXCLUSION`. The producer now applies the same rule (level 1 -> original sentinel plus an invalid validity mask), and the measured effect is exactly confined to the lowest level: the first-guess field changes by up to **0.45 m/s** at level 1 while levels 2-9 stay bit-identical, with both real-case verdicts still passing.
- `RMIN2 = -1.0`: the original skips a surface station's vertical extrapolation only when its nearest upper station is closer than `RMIN2` (`IF(FMIN.LT.RMIN2) GO TO 70`, L5831). A negative `RMIN2` can never exceed the non-negative `FMIN`, so no station is skipped; with this case's single surface station the rule is satisfied but inert, and multi-surface-station cases would need it modelled. The metadata records this explicitly instead of leaving a silent gap.

### Real-case windows and levels

Both real-case comparators now report `1h` / `6h` / `143h` windows and per-level maxima on top of the per-hour table, each with its own PASS/FAIL against the frozen 2e-4 m/s tolerance: step one `PASS_REALCASE_STEP_ONE_ORIGINAL_WIND1_PLUS_SIMILT` (6,435,000 components, worst 2.53e-05 m/s, worst relative 1.10e-03) and blend `PASS_REALCASE_BLEND_ORIGINAL_INTER2` (6,435,000 components, worst 4.22e-05 m/s, worst relative 9.37e-04), re-verified after the PREPDI exclusion was applied.

### Machine-readable metadata contract

`grid.layout` = `i_fastest` (with `grid.layout_note` giving `index = i + nx*(j + ny*k)`), `grid.dtype` = `float32`, `grid.byte_order` = `little`, `missing_sentinel` = the scalar `9999.0`, `hour_label` = `END` (interval end in UTC) and `levels.zface_m/thickness_m/center_m` from the deck: exact literals the P6F CALMET.DAT 2.1 writer keys on instead of hardcoding.

### Remaining upstream dependency (precise)

`FRADJ` (L5643-L5644) is the only real-path stage still not applied in the producer: it needs the gridded `GAMMA`, and the original `CGAMMA` derives it with `ZICONV`. After merging the newest `origin/main` I can state exactly what is missing rather than "ZICONV is coming": P6E's MIXHT is **stateful**, not a per-hour function — `cteas::p6e::MixhtObservedMcInput` requires caller-supplied `initial_zi`, `initial_ziconv` and `initial_dptt` fields and is advanced hour by hour through `apply_p6c_hour_to_mixht_one_station` with `cteas::p6e::P6CObservedHour` (the E26 orchestration). So the precise dependency is: **a realized 143-hour `ZICONV` (or `ZI`) array per hour, either exported by P6E's orchestration or supplied by the caller with provenance**; with that in hand the FRADJ wiring is one call in the producer (the FRADJ kernel and its original-source parity already exist here). Until then the stage is marked `PENDING_GAMMA` and the W faces stay the uncompensated-Froude variant.

### Real-case numeric verdict (blend): PASS after the layout fix

`reference/compare_original_d9a_realcase_blend.py` compiles the unchanged original `INTER2` (frozen vendor blob) and replays its driver on all 143 hours of INTER2 fixtures, comparing cell by cell against `blend_u/v_*.f32`: **143 hours, 6,435,000 components compared, worst absolute error 4.22e-05 m/s** at the frozen 2e-4 m/s tolerance, worst relative error 9.37e-04, zero mismatches -> `PASS_REALCASE_BLEND_ORIGINAL_INTER2`.

Root cause of the earlier FAIL (worst 10.36 m/s), nailed down rather than guessed: **the producer filled `station_component_mps` station-major (nine surface levels followed by nine upper levels) while the original `STDAT1(K,L)` layout and the kernel are level-major, station-minor (`data[k*nstations + l]`)**. The fixture writer re-interleaved into level-major rows, so the fixture-driven comparison of the original against the C++ *trace* agreed to 4.8e-07 while the producer's own in-process call used the wrong pairing; isolating that required driving the original driver and the `cteas_p6_inter2` trace from the producer's own emitted fixture and comparing all three outputs. The fix is one line in the producer, and the same class of error is now impossible to hide because the fixture writer and the producer share the same layout expression. Minimal reproduction for the record: an `INTER2` input where the two stations' values differ per level (any case with surface and upper winds that are not equal); with a station-major fill the blend collapses towards the station average instead of the original's mixed result.

### Real-case numeric verdict (step one)

`reference/compare_original_d9a_realcase_step_one.py` compiles the **unchanged** original `WIND1`+`SIMILT` (vendor blob `437f43bb7f0e51a1919e56664663e1a046986ed0`; `wind1_source.for` sha256 `5aba624838f275ca85b018482d6873de7de014a298e65111008b15bb1b67a412`, `similt_source.for` sha256 `b52427a2b52298b5a1a456efc1444c7d0a331dbf471e609b676fe744bb98850b`), replays the driver on all 143 producer fixtures and compares cell by cell against `wind1_u/v_*.f32`: **143 hours, 6,435,000 components compared, worst absolute error 2.53e-05 m/s** (tolerance 2e-4 m/s), worst relative error 1.10e-03, zero mismatches, status `PASS_REALCASE_STEP_ONE_ORIGINAL_WIND1_PLUS_SIMILT`.

## Stage status (roadmap vocabulary)

| stage | status | evidence |
|---|---|---|
| WIND1 → INTER2 → SMOOTH/DIVCEL/W + WINDBC | `IMPLEMENTED_SCOPED`, `PASS_SOFTWARE` | 28/28 scoped CTest; composed literal-source parity `PASS_D9A_SELECTED_CHAINED_ORIGINAL_SOURCES` |
| TERSET envelope (L5228) | `IMPLEMENTED_SCOPED`, `PASS_SOFTWARE`, `PASS_REFERENCE` | in-chain on the real-deck route; literal call sha256 `d7079f77…`, subroutine L31805–L31903 sha256 `495ad293…` |
| FRADJ (L5643–L5644) | `IMPLEMENTED_SCOPED`, `PASS_REFERENCE` | real-case path (`IFRADJ=1`), step-one 5.0e-12 m/s |
| SLOPE (L5722–L5723 + L5727–L5732) | `IMPLEMENTED_SCOPED`, `PASS_REFERENCE` | real-case path (`ISLOPE=1`), W faces 1.2e-05 m/s |
| TOPOF2 + pre-blend MINIM (L5621–L5629) | `IMPLEMENTED_SCOPED`, `PASS_REFERENCE`, **non-case path** | `IKINE=0` in the frozen deck gates both calls, and `ALPHA` is consumed only by this call |
| O'Brien + MINIM tail (L6153–L6180) | `IMPLEMENTED_SCOPED`, `PASS_REFERENCE`, **non-case path** | `IOBR=0` in the frozen deck |
| SURFVAR → `TEMP2D` (L5609–L5610, `ISURFT<0`) | `BLOCKED` (kernel available, scope to confirm) | after merging `origin/main` the p6e kernel exists: `cteas::calmet::p6e::surfvar_one_station(ObservedSurface)` returns `SurfaceState{temp_k,rh_percent,ipcode}`, and every input it asks for is in this case file: `station_temp_k`/`station_rh_percent` come from `read_surface_2022` (SURF.DAT temperature/humidity validity flags), and the deck matches its scope for `NOOBS=0`, `ITPROG=0`, `IRHPROG=0`, `NPSTA=0`, `NSSTA=1`, `NOWSTA=0`. Open: the DIAGNO L5610 call passes `IALL=0` while the kernel documents `IALL=1`, and the deck sets `IAVET=1` while the kernel documents `IAVET=0`; both must be confirmed by P6E (or ported scope-locally) before wiring, not assumed. |
| HEATFX / ELUSTR → `QH` (L5676–L5715, `ISFCMET=0`) | `BLOCKED` on `TEMP2D` and the solar field | merged p6e provides `heatfx(HeatFluxInput)` and `elustr_stable`/`elustr_daytime`, and this case narrows the inputs usefully: the deck sets `ICLOUD=0` (gridded clouds not used → cloud input is the surface station cloud amount, `CCGRID`/`MCLOUD` are not needed), `NSSTA=1` (`NEARS` is the single station cell), `ITWPROG=0`; `albedo`/`bowen`/`soil_heat_fraction`/`anthropogenic_wm2` are per-cell in `read_geo_50`'s `Geo50`, `station_cloud` is `SurfaceObserved::opaque_cloud_tenths`, and `Z0`/`RHO` come from `Geo50::z0_m` and the surface pressure observation. What is still missing: `temp_k` (= `TEMP2D`, i.e. the SURFVAR row above) and the `sun` field (`p6e::solar::calculate`, whose grid solar geometry P6E reports as still in progress), plus the initial `QH` field the original leaves unchanged over water cells. |
| real Hefei 2022 step-one U/V | `IMPLEMENTED_SCOPED`, `PASS_REAL_CASE` | 143 hours, 6,435,000 components vs the unchanged original WIND1+SIMILT, worst 2.53e-05 m/s |
| real Hefei 2022 blended U/V + W faces | `IMPLEMENTED_SCOPED`, `PASS_REAL_CASE` (blend) | 143 hours of INTER2 blend passing its original-source comparison (worst 4.22e-05 m/s) and the SLOPE-compensated W tail; FRADJ stays `PENDING_GAMMA`, so the W faces remain the uncompensated-Froude variant and `P6D_FULL_2022_UVW` stays `NOT_PASS` |
| real-case SURFVAR -> `TEMP2D`, HEATFX -> `QH`, SLOPE | `IMPLEMENTED_SCOPED` | chain-computed per hour from the case tree; SLOPE's kernel keeps its own chained original-source parity (real-deck upstream route). FRADJ stays `PENDING_GAMMA` (see above) |
| real-case INTER2 blend | `IMPLEMENTED_SCOPED`, `PASS_REAL_CASE` | 143 hours, 6,435,000 components vs the unchanged original INTER2, worst 4.22e-05 m/s (after the level-major station-data fix); the `WO(i,j,k)` mapping is resolved (`RDWT` fills 1.0 for `IPROG=0` with no `WT.DAT`) |

## Hard limits and open dependencies

The original full `DIAGNO` also contains `TOPOF2`, the pre-blend `MINIM` at L5628 (kinetic/terrain route, requires `TOPOF2`), `HEATFX`, `ELUSTR`, `STHEOR` and `ADJUST`, as well as lake-breeze branches and the `I3DCTW`/`HTFAC` conditionals. D9A does **not** implement those, and their `QH`/`HMIN`/`DISTH*` inputs are caller-supplied instead of computed in-bridge; the L5628 `MINIM` call remains unimplemented. `INTER2` observation weights `WO`, observed surface-layer extrapolated U/V and the remaining terrain/heat outputs are all required from independently verified upstream providers. The D9A test intentionally uses named synthetic fixtures only; **never promote this mode to a 2022 scientific result**.

`P6D9A_SOFTWARE_GATE` = **PASS** on the P6D9A software path (28/28 scoped CTest targets, including `p6d9a_obrien_minim_iobr1_tail_contract`, `p6d9a_fradj_upstream_route_contract`, `p6d9a_slope_upstream_route_contract`, `p6d9a_topof2_preblend_route_contract` and `p6d9a_inchain_terset_envelope_contract`). `P6D9A_FULL_ORIGINAL_FORTRAN_CHAIN` = **PASS** for the three selected synthetic source-only scenes (`unbiased`, `upper_bias`, `calm_icalm0`) on four routes: identity, `IOBR=1` O'Brien/MINIM, `IFRADJ=1`, and the real-deck `IFRADJ=1`+`ISLOPE=1` upstream sequence — one composed original Fortran reference (frozen `WIND1` → optional literal `FRADJ` → optional literal `SLOPE` + additive loop → original `INTER2` U/V → literal `DIAGNO` L6119–L6148 → optional `IOBR=1` tail) compared against a single C++ bridge call, with 337,500 U/V/DIV/W components and 5,400 boundary values per route plus 7,500 cancelled top W faces under `IOBR=1`. The real-deck `IFRADJ=1`+`ISLOPE=1` route now builds its own TERSET envelope (24,921/7,456/3,772 changed step-one components per scene, final fields inside 8.4e-06 m/s). The `IKINE=1` pre-blend kinematic route adds a fourth replay: 25,000 TOPOF2 W faces per scene compared to 5.96e-08 m/s maximum difference (22,041–22,499 non-zero faces) plus the post-MINIM step-one, INTER2 and final fields. Its MINIM comparison uses `NITER=50` with a deterministic `DIVLIM=0`: at the deck's `DIVLIM=5e-6` the original convergence test `DIVMAX<=DIVLIM` is threshold-sensitive and the two implementations can exit after a different number of Gauss-Seidel iterations (measured calm-scene spread 2.8e-03 m/s versus 2.4e-06 m/s at `DIVLIM=0`, with both active scenes inside 7.2e-06 m/s either way). `IKINE=0` in the frozen deck also means the L5628 pre-blend MINIM route is a non-case path, kept implemented rather than deleted. It is still **NOT_PASS** for real Hefei 2022 inputs: `P6D_FULL_2022_UVW=NOT_PASS`; 1h/6h/143h actual Hefei 2022 U/V/W verification pending. P6E thermodynamic inputs, P6F/G and HTO meteorological forcing not validated by this bridge.

Independent original source segments previously established: [WIND1 CI #38125704104](https://github.com/RRain001/CTEAS/actions/runs/38125704104), [INTER2 CI #38125137491](https://github.com/RRain001/CTEAS/actions/runs/38125137491), [DIAGNO final W CI #38125137481](https://github.com/RRain001/CTEAS/actions/runs/38125137481), isolated original `MINIM` [CI #38126139082](https://github.com/RRain001/CTEAS/actions/runs/38126139082) (base branch `codex/cteas-p6-calmet-hefei-100m`). The composed chain is now numerically accepted for the selected synthetic scenes by `reference/compare_original_diagno_d9a_chained.py` on the frozen vendor blob `437f43bb7f0e51a1919e56664663e1a046986ed0`:

- literal `DIAGNO` L6119–L6148 block sha256 `488ec4ebe627a0746818e4710754f10f36e6ba2ae3b85395e4910e4817baac8d`;
- O'Brien L6153–L6159 sha256 `1144ce12082952854bb7cbf5bf4fd755b5c0452a98a614b0b23b029daec4d69c`;
- `MINIM` call L6180 sha256 `1a9b62a5b6c5bf3c0f03d257af3f9109f1a5022694664a08f8387683229cddc8`;
- original `MINIM` L9645–L9761 sha256 `1d42cb594f9ad1b2724048400bbf027f2422854b10abc0573258a2fd207e00d4`;
- original `FRADJ` L7289–L7456 sha256 `59c7df757cf3eb65e3a1c6409a2acd9d794de23eeb21f26d3257e5f59adfa3aa` (DIAGNO call L5643–L5644);
- original `SLOPE` L30372–L30604 sha256 `d0c7e7f12e6d8f501bf12230fccd43e151aa53c4b55567047948b59ce14ca964`;
- original `TOPOF2` extraction (L31904–L32078 plus the self-contained `UNIDOT`) sha256 recorded in `p6d9a-original-chained-source-parity.json`, with literal `w_init` L5615–L5616, `topof2_call` L5621–L5622, `minim_call` L5628–L5629 and `windbc_loop` L5598–L5600 fragment hashes; literal DIAGNO fragments `fradj_call` L5643–L5644 sha256 `e7d2c6df7eddcacadb176861019744a55ed5e15c6029913de00541135687a93f`, `slope_call` L5722–L5723 sha256 `d4cbeba940e96e95c4861838550e7d4c3437bf33253d4eb371cf5164a31ca5c7`, `slope_add` L5727–L5732 sha256 `7b3170cbfdceec61a41d2cf182b5c4c52e3bdb2b022abd402830efcac0a8aa77`;
- worst observed absolute differences at tolerance 2e-4 m/s / 1e-6 s⁻¹: `IOBR=0` route u 9.54e-07, v 3.52e-06, div 1.22e-08, W 1.14e-05 m/s, boundaries 5.96e-07; `IOBR=1` route u 1.19e-06, v 3.37e-06, div 9.20e-09, W 3.34e-06 m/s, boundaries 1.01e-06, with 7,500 top faces cancelled against 7,500 non-zero top faces in the `IOBR=0` replay; `IFRADJ=1` route step-one u 5.00e-12, v 4.77e-07 m/s for 135,000 components of which 30,789 were actually rotated (`unbiased` 10,351, `upper_bias` 12,956, `calm_icalm0` 7,482), pre-smoothing blend 3.73e-06, final u 1.67e-06, v 3.73e-06, div 1.30e-08, W 1.22e-05 m/s, boundaries 1.07e-06; real-deck `IFRADJ=1`+`ISLOPE=1` route step-one u 2.38e-07, v 4.77e-07 m/s for 135,000 components of which 5,733 were changed by the composed terrain stages (`unbiased` 1,952, `upper_bias` 2,708, `calm_icalm0` 1,073), pre-smoothing blend 3.93e-06, final u 2.38e-06, v 3.93e-06, div 1.58e-08, W 1.20e-05 m/s, boundaries 1.07e-06, with 22,500 3-D W faces compared per scene.

Tolerances, counters and per-scene errors are emitted in `p6d9a-original-chained-source-parity.json` and uploaded as the `p6d9a-original-chained-source-parity` CI artifact.
